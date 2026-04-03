# Phase 0 & 1 手动测试计划

> 测试日期：2026-04-03
> 前提条件：macOS, Appium 服务运行中, Mac2 驱动已安装, 终端有辅助功能权限

---

## 前置准备

```bash
# 安装依赖
uv sync

# 确认 CLI 可用
uv run mac --version
# 预期: fsq-mac 0.1.0

# 确认 Appium 服务运行
curl -s http://127.0.0.1:4723/status | python3 -m json.tool
```

---

## A. Phase 0 功能测试

### A1. `--version` 标志

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A1.1 | `uv run mac --version` | 输出 `fsq-mac 0.1.0`，退出码 0 | [ ] |
| A1.2 | `uv run mac --version --pretty` | 同上（version 优先于其他参数） | [ ] |

### A2. 区域截图 (`--rect`)

```bash
uv run mac session start
```

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A2.1 | `uv run mac capture screenshot /tmp/full.png` | ok=true, 文件存在, size_bytes > 0 | [ ] |
| A2.2 | `uv run mac capture screenshot --rect 0,0,200,200 /tmp/rect.png` | ok=true, 截取左上角 200x200 区域 | [ ] |
| A2.3 | `uv run mac capture screenshot --rect bad /tmp/bad.png` | ok=false, INVALID_ARGUMENT | [ ] |
| A2.4 | `uv run mac capture screenshot --rect 0,0,abc,100 /tmp/bad2.png` | ok=false, INVALID_ARGUMENT | [ ] |

### A3. 元素截图 (`--element`)

```bash
# 先获取元素列表
uv run mac element inspect --pretty
```

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A3.1 | `uv run mac capture screenshot --element e0 /tmp/elem.png` | ok=true, 只截取该元素 | [ ] |
| A3.2 | `uv run mac capture screenshot --element e99999 /tmp/gone.png` | ok=false, 元素不存在的错误 | [ ] |
| A3.3 | `uv run mac capture screenshot --element e0 --rect 0,0,10,10 /tmp/x.png` | CLI 报错：互斥参数 | [ ] |

---

## B. Phase 1 功能测试

### B1. Daemon 自动生命周期

```bash
# 先确保 daemon 未运行
uv run mac session end 2>/dev/null
kill $(cat ~/.fsq-mac/daemon.pid 2>/dev/null) 2>/dev/null
rm -f ~/.fsq-mac/daemon.pid ~/.fsq-mac/daemon.port
```

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B1.1 | `uv run mac session start` | daemon 自动启动, ok=true, session_id=s1 | [ ] |
| B1.2 | `cat ~/.fsq-mac/daemon.pid` | 输出一个 PID 数字 | [ ] |
| B1.3 | `cat ~/.fsq-mac/daemon.port` | 输出 19444 | [ ] |
| B1.4 | `curl -s http://127.0.0.1:19444/health` | `{"status":"ok","pid":...}` | [ ] |

### B2. 会话管理

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B2.1 | `uv run mac session start` | ok=true, 返回 session_id | [ ] |
| B2.2 | `uv run mac session get` | ok=true, 返回当前会话信息 | [ ] |
| B2.3 | `uv run mac session list` | ok=true, sessions 数组非空 | [ ] |
| B2.4 | `uv run mac session end` | ok=true, 返回 ended session_id | [ ] |
| B2.5 | `uv run mac session get` | ok=false, SESSION_NOT_FOUND | [ ] |

### B3. `--verbose` / `--debug` 日志

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B3.1 | `uv run mac session start` | 无额外日志输出（默认静默） | [ ] |
| B3.2 | `uv run mac -v session start` | 有 INFO 级别日志（`mac-cli ...`） | [ ] |
| B3.3 | `uv run mac --debug session start` | 有 DEBUG 级别日志（更详细） | [ ] |

### B4. `--pretty` 输出格式

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B4.1 | `uv run mac session start` | 单行 JSON 输出 | [ ] |
| B4.2 | `uv run mac session start --pretty` | 人类可读格式，有 `OK session.start` 标题 | [ ] |
| B4.3 | `uv run mac session get --pretty`（无会话时） | 显示 `ERROR [SESSION_NOT_FOUND]: ...` | [ ] |

### B5. 统一错误信封

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B5.1 | 无会话时 `uv run mac app launch com.apple.calculator` | ok=false, error.code=SESSION_NOT_FOUND, error.suggested_next_action 包含 `mac session start` | [ ] |
| B5.2 | `uv run mac app terminate com.test` (无 `--allow-dangerous`) | ok=false, error.code=ACTION_BLOCKED, suggested_next_action 包含 `--allow-dangerous` | [ ] |
| B5.3 | 检查 B5.1 响应中包含以下字段: `ok`, `command`, `session_id`, `data`, `error.code`, `error.message`, `error.retryable`, `error.details`, `error.suggested_next_action`, `error.doctor_hint`, `meta` | 所有字段都存在（可为 null） | [ ] |

### B6. 默认延迟为 0

```bash
uv run mac session start
```

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B6.1 | `time uv run mac element inspect` | 执行时间不应有额外 1 秒延迟 | [ ] |
| B6.2 | 如有按钮可点，执行 `time uv run mac element click e0` | 执行速度应接近网络往返，无人为 sleep | [ ] |

### B7. Adapter Registry（后端工厂）

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B7.1 | `uv run mac session start`，然后 `uv run mac session get` | backend_type 字段值为 `appium_mac2` | [ ] |
| B7.2 | 编辑 `~/.fsq-mac/config.json`，添加 `"backend": "nonexistent"`，然后重启 daemon 并 `uv run mac session start` | ok=false, error.code=INVALID_ARGUMENT, error.message 包含 `Unknown backend` | [ ] |
| B7.3 | 恢复 config（删除 `backend` 键或改回 `appium_mac2`） | 确认恢复正常 | [ ] |

### B8. 连接池 Health Check

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B8.1 | `kill $(cat ~/.fsq-mac/daemon.pid)`, 然后立即 `uv run mac session start` | daemon 自动重启, ok=true | [ ] |

---

## C. 应用操作端到端

```bash
uv run mac session start
```

### C1. 应用启动与查看

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C1.1 | `uv run mac app launch com.apple.calculator` | ok=true, data 包含 bundle_id | [ ] |
| C1.2 | `uv run mac app current` | ok=true, 返回 Calculator 信息 | [ ] |
| C1.3 | `uv run mac app list` | ok=true, apps 数组包含 Calculator | [ ] |

### C2. 元素检查与交互

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C2.1 | `uv run mac element inspect --pretty` | ok=true, 列出 Calculator 的 UI 元素（按钮 0-9 等） | [ ] |
| C2.2 | `uv run mac element find "5"` | ok=true, 找到数字 5 按钮 | [ ] |
| C2.3 | `uv run mac element click e0` (某个按钮) | ok=true, 按钮被点击 | [ ] |
| C2.4 | (点击后) `uv run mac element click e0` | ok=false, ELEMENT_REFERENCE_STALE（refs 已失效） | [ ] |
| C2.5 | `uv run mac element find "nonexistent_button_xyz"` | ok=false, ELEMENT_NOT_FOUND | [ ] |

### C3. 键盘输入

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C3.1 | `uv run mac input key "5"` | 计算器显示 5 | [ ] |
| C3.2 | `uv run mac input hotkey "command+a"` | 全选（在适用界面） | [ ] |
| C3.3 | `uv run mac input text "123"` | 输入 123 | [ ] |

### C4. 窗口操作

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C4.1 | `uv run mac window current` | ok=true, 返回窗口标题和尺寸 | [ ] |
| C4.2 | `uv run mac window list` | ok=true, 返回窗口列表 | [ ] |
| C4.3 | `uv run mac window focus 0` | ok=true, 第一个窗口获得焦点 | [ ] |
| C4.4 | `uv run mac window focus 999` | ok=false, WINDOW_NOT_FOUND | [ ] |

### C5. 等待操作

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C5.1 | `uv run mac wait app com.apple.calculator` | ok=true, found=true | [ ] |
| C5.2 | `uv run mac wait app com.nonexistent.app --timeout 2000` | ok=false, TIMEOUT | [ ] |
| C5.3 | `uv run mac wait window "Calculator"` | ok=true, found=true | [ ] |

### C6. 安全分级

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C6.1 | `uv run mac app terminate com.apple.calculator` | ok=false, ACTION_BLOCKED | [ ] |
| C6.2 | `uv run mac app terminate com.apple.calculator --allow-dangerous` | ok=true, 计算器关闭 | [ ] |

---

## D. Doctor 诊断

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| D1 | `uv run mac doctor --pretty` | 显示所有检查项，标记 pass/fail/warn | [ ] |
| D2 | `uv run mac doctor permissions --pretty` | 仅检查辅助功能权限 | [ ] |
| D3 | `uv run mac doctor backend --pretty` | 检查 Xcode、Appium、Mac2 驱动 | [ ] |

---

## E. 错误传播一致性验证

> 验证所有层级的错误都遵循标准信封格式

| # | 场景 | 操作 | 检查点 | 通过 |
|---|------|------|--------|------|
| E1 | Adapter → Core | 启动不存在的 app: `uv run mac app launch com.nonexistent.fake.app` | error.code=BACKEND_UNAVAILABLE, error.doctor_hint 存在 | [ ] |
| E2 | Core → Client | 无会话时执行命令 | error 包含所有标准字段 | [ ] |
| E3 | 不安全 bundle ID | `uv run mac app activate 'com.test";exit'` | error.code=INVALID_ARGUMENT (如果 activate_app 走 AppleScript 回退) | [ ] |
| E4 | Client 500 处理 | 手动停止 Appium, 然后执行命令 | error.code=BACKEND_UNAVAILABLE, retryable=true | [ ] |

---

## F. 自动化测试确认

```bash
# 运行全部单元测试
uv run pytest tests/ -v

# 检查覆盖率
uv run pytest tests/ --cov=fsq_mac --cov-report=term-missing
```

| # | 检查 | 预期结果 | 通过 |
|---|------|---------|------|
| F1 | 所有测试通过 | 397 passed, 0 failed | [ ] |
| F2 | 总覆盖率 | ≥ 80%（当前 86%） | [ ] |
| F3 | `adapters/__init__.py` 覆盖率 | 100% | [ ] |
| F4 | `models.py` 覆盖率 | 100% | [ ] |

---

## G. 收尾验证

```bash
# 验证关键重构目标
grep -n "AppiumMac2Adapter" src/fsq_mac/session.py
# 预期: 无输出（session.py 不再直接引用 adapter 实现）

grep -n "httpx.get" src/fsq_mac/client.py
# 预期: 无输出（所有请求走连接池）

grep -rn "raise " src/fsq_mac/adapters/appium_mac2.py
# 预期: 仅 _safe_applescript_str 一处 raise
```

| # | 检查 | 预期结果 | 通过 |
|---|------|---------|------|
| G1 | session.py 无 AppiumMac2Adapter 引用 | 0 匹配 | [ ] |
| G2 | client.py 无独立 httpx.get | 0 匹配 | [ ] |
| G3 | adapter 中仅 _safe_applescript_str raise | 仅 1 处 | [ ] |

---

## 测试结果汇总

| 分类 | 总数 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| A. Phase 0 功能 | 9 | | | |
| B. Phase 1 功能 | 17 | | | |
| C. 端到端操作 | 17 | | | |
| D. Doctor 诊断 | 3 | | | |
| E. 错误传播 | 4 | | | |
| F. 自动化测试 | 4 | | | |
| G. 收尾验证 | 3 | | | |
| **合计** | **57** | | | |
