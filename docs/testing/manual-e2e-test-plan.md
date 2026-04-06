# 手动 E2E 测试计划

> 测试日期：2026-04-06
> 适用范围：fsq-mac 全量人工验收与版本回归测试
> 前提条件：macOS、Appium 服务运行中、Mac2 驱动已安装、终端已授予辅助功能权限

---

## 目标

这份文档用于验证 fsq-mac 在真实桌面环境中是否真正可用，而不只是单元测试通过。

覆盖范围包括：

- 安装与环境检查
- daemon / session / safety / doctor
- app / window / element / input / assert / wait
- capture
- trace / viewer / replay / codegen
- plugin discovery
- 关键失败路径与回归项

建议优先使用以下系统应用做测试：

- `Calculator`：适合点击、trace、codegen、replay
- `TextEdit`：适合输入、菜单、窗口、等待

---

## 安装 CLI

这份文档默认你已经安装了 `fsq-mac`，并且终端里可以直接运行 `mac`。

推荐安装方式：

```bash
uv pip install fsq-mac
```

安装后先确认 CLI 可用：

```bash
mac --version
```

如果你是在源码仓库内验证当前分支，而不是验证已安装版本，可使用开发者路径：

```bash
uv sync
uv run mac --version
```

说明：

- 面向真实用户的手动验收，优先使用已安装后的 `mac ...`
- 只有在源码 checkout、且未安装 CLI 时，才使用 `uv run mac ...`

---

## 注意事项

请以当前 CLI 实际语法为准，而不是旧文档中的过时示例。

当前有效写法示例：

```bash
mac element type "hello world" --role TextField
mac element scroll down --role ScrollArea
mac menu click "File > Open"
mac assert text "Hello" --role StaticText
mac assert value "42" --role TextField
mac wait window "Calculator"
mac wait app com.apple.calculator
mac input click-at 100 200
```

以下是旧写法，不应再作为测试依据：

```bash
mac element type --text "hello world"
mac element scroll --direction down
mac menu click --path "File > Open"
mac assert text --expected "Hello"
mac assert value --expected "42"
mac input click-at --x 100 --y 200
```

---

## 前置准备

### 1. 启动 Appium

在单独终端中运行：

```bash
appium
```

### 2. 确认 CLI 与环境

默认假设你已经安装了 CLI，因此以下命令直接使用 `mac ...`。

如果你是在源码仓库内、且尚未安装 CLI，可临时把下面所有命令替换为 `uv run mac ...`。

```bash
mac doctor --pretty
mac doctor backend --pretty
mac doctor permissions --pretty
mac doctor plugins --pretty
```

预期：

- `doctor` 不出现阻断后续测试的错误
- `doctor plugins` 至少列出 `appium_mac2`

### 3. 清理旧会话

```bash
mac session end
```

---

## A. 基础链路

### A1. Daemon / Session

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A1.1 | `mac session start --pretty` | ok=true，返回 `session_id` | [ ] |
| A1.2 | `mac session get --pretty` | 返回当前会话信息 | [ ] |
| A1.3 | `mac session list --pretty` | sessions 非空 | [ ] |
| A1.4 | `mac session end --pretty` | 正常结束当前会话 | [ ] |
| A1.5 | `mac session get --pretty` | ok=false，`SESSION_NOT_FOUND` | [ ] |

### A2. Doctor / Plugin Discovery

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A2.1 | `mac doctor --pretty` | 返回检查项列表 | [ ] |
| A2.2 | `mac doctor backend --pretty` | 显示 Xcode / Appium / Mac2 driver 检查项 | [ ] |
| A2.3 | `mac doctor permissions --pretty` | 权限检查正常 | [ ] |
| A2.4 | `mac doctor plugins --pretty` | 列出 adapters / doctor_plugins | [ ] |
| A2.5 | 检查 `doctor plugins` 输出 | adapters 至少包含 `appium_mac2` | [ ] |

### A3. Safety Gate

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| A3.1 | `mac app terminate com.apple.calculator --pretty` | ok=false，`ACTION_BLOCKED` | [ ] |
| A3.2 | 错误输出检查 | 包含 `suggested_next_action` 且提示 `--allow-dangerous` | [ ] |

---

## B. Calculator 场景

### B1. App / Window 基础操作

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B1.1 | `mac session start --pretty` | 会话启动成功 | [ ] |
| B1.2 | `mac app launch com.apple.calculator --pretty` | Calculator 启动成功 | [ ] |
| B1.3 | `mac app current --pretty` | 当前 app 为 Calculator | [ ] |
| B1.4 | `mac app list --pretty` | 列表包含 Calculator | [ ] |
| B1.5 | `mac window current --pretty` | 返回当前窗口信息 | [ ] |
| B1.6 | `mac window list --pretty` | 返回窗口列表 | [ ] |
| B1.7 | `mac window focus 0 --pretty` | 聚焦成功 | [ ] |

### B2. Element Inspect / Find / Click

先运行：

```bash
mac element inspect --pretty
```

根据输出确认 Calculator 中按钮的真实 `role` / `name`。如果 `Button` 不匹配，以 inspect 结果为准。

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B2.1 | `mac element inspect --pretty` | 可列出可见元素 | [ ] |
| B2.2 | `mac element find 5 --pretty` | 能找到数字 5 相关元素 | [ ] |
| B2.3 | `mac element click --role Button --name 5 --pretty` | 数字 5 被点击 | [ ] |
| B2.4 | `mac element click --role Button --name + --pretty` | 加号被点击 | [ ] |
| B2.5 | `mac element click --role Button --name 3 --pretty` | 数字 3 被点击 | [ ] |
| B2.6 | `mac element click --role Button --name = --pretty` | 等号被点击 | [ ] |
| B2.7 | `mac element find nonexistent_button_xyz --pretty` | ok=false，`ELEMENT_NOT_FOUND` | [ ] |

### B3. Input / Capture / Wait

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| B3.1 | `mac input key return --pretty` | ok=true | [ ] |
| B3.2 | `mac input click-at 100 200 --pretty` | ok=true | [ ] |
| B3.3 | `mac capture screenshot /tmp/fsq-calc-full.png --pretty` | 文件生成成功 | [ ] |
| B3.4 | `mac capture ui-tree --pretty` | 返回 UI tree/XML 内容 | [ ] |
| B3.5 | `mac wait app com.apple.calculator --timeout 5000 --pretty` | ok=true | [ ] |
| B3.6 | `mac wait window "Calculator" --timeout 5000 --pretty` | 若标题匹配，ok=true | [ ] |

---

## C. TextEdit 场景

### C1. 菜单、输入、断言准备

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C1.1 | `mac app launch com.apple.TextEdit --pretty` | TextEdit 启动成功 | [ ] |
| C1.2 | `mac menu click "File > New" --pretty` | 新文档窗口打开或激活 | [ ] |
| C1.3 | `mac window current --pretty` | 当前窗口为 TextEdit 文档窗口 | [ ] |
| C1.4 | `mac element inspect --pretty` | 可看到编辑区相关元素 | [ ] |

### C2. 输入与等待

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C2.1 | 手动聚焦文档编辑区 | 光标出现在文档中 | [ ] |
| C2.2 | `mac input text "hello fsq mac" --pretty` | 文本成功输入 | [ ] |
| C2.3 | `mac capture screenshot /tmp/fsq-textedit.png --pretty` | 截图成功，可见输入内容 | [ ] |
| C2.4 | `mac wait app com.apple.TextEdit --timeout 5000 --pretty` | ok=true | [ ] |
| C2.5 | `mac wait window "TextEdit" --timeout 5000 --pretty` | 若标题匹配，ok=true | [ ] |

说明：

- TextEdit 的精确 locator 可能因系统版本不同而不同。
- 如无法稳定定位编辑区，允许先手动聚焦，再测试 `input text`。

### C3. 可选断言测试

如果当前 UI 能稳定定位文字或文本框，可补充：

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| C3.1 | `mac assert visible --role TextArea --pretty` | 若 locator 正确，ok=true | [ ] |
| C3.2 | `mac assert text "hello fsq mac" --role StaticText --pretty` | 若 locator 正确，ok=true | [ ] |
| C3.3 | `mac assert value "hello fsq mac" --role TextField --pretty` | 若 locator 正确，ok=true | [ ] |

说明：

- 断言类用例依赖当前系统版本和 UI accessibility 暴露情况。
- 如果 locator 不稳定，不应把这组用例作为 release blocker。

---

## D. Trace / Viewer / Replay / Codegen

### D1. 录制 trace

先重新打开 Calculator：

```bash
mac app launch com.apple.calculator --pretty
```

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| D1.1 | `mac trace start --pretty` | 开始录制，返回路径/trace_id | [ ] |
| D1.2 | `mac element click --role Button --name 7 --pretty` | 点击成功并被记录 | [ ] |
| D1.3 | `mac element click --role Button --name + --pretty` | 点击成功并被记录 | [ ] |
| D1.4 | `mac element click --role Button --name 8 --pretty` | 点击成功并被记录 | [ ] |
| D1.5 | `mac element click --role Button --name = --pretty` | 点击成功并被记录 | [ ] |
| D1.6 | `mac trace status --pretty` | `active=true`，steps 数量递增 | [ ] |
| D1.7 | `mac trace stop --pretty` | 停止录制，返回 `<TRACE_PATH>` | [ ] |

### D2. Trace 产物

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| D2.1 | 检查 `<TRACE_PATH>/trace.json` | 文件存在 | [ ] |
| D2.2 | 检查 `<TRACE_PATH>/steps/` | 存在截图或 tree 文件 | [ ] |
| D2.3 | `mac trace viewer <TRACE_PATH> --pretty` | 返回 viewer 路径 | [ ] |

### D3. Replay

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| D3.1 | `mac trace replay <TRACE_PATH> --pretty` | replay 成功，ok=true | [ ] |
| D3.2 | 若 replay 失败 | 错误中应包含 `completed_steps`，必要时包含 `failing_step` | [ ] |

### D4. Codegen

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| D4.1 | `mac trace codegen <TRACE_PATH> --pretty` | stdout 输出脚本 | [ ] |
| D4.2 | `mac trace codegen <TRACE_PATH> --output /tmp/fsq-trace.sh` | 生成脚本文件成功 | [ ] |
| D4.3 | 检查 `/tmp/fsq-trace.sh` 内容 | 使用当前 CLI 语法，不含旧 flag 写法 | [ ] |
| D4.4 | `bash /tmp/fsq-trace.sh` | 脚本可真实执行，不因 argparse 语法错误失败 | [ ] |

---

## E. 失败路径与回归项

### E1. 常见失败路径

| # | 操作 | 预期结果 | 通过 |
|---|------|---------|------|
| E1.1 | 无会话时执行 `mac app current --pretty` | `SESSION_NOT_FOUND` | [ ] |
| E1.2 | `mac wait app com.fake.does.not.exist --timeout 2000 --pretty` | `TIMEOUT` | [ ] |
| E1.3 | `mac element find nonexistent_button_xyz --pretty` | `ELEMENT_NOT_FOUND` | [ ] |
| E1.4 | `mac app terminate com.apple.TextEdit --pretty` | `ACTION_BLOCKED` | [ ] |

### E2. Phase 4 专项回归

| # | 检查点 | 预期结果 | 通过 |
|---|--------|---------|------|
| E2.1 | `trace codegen` 输出 element/menu/assert/input/wait 命令 | 使用位置参数语法，不是旧 flag 语法 | [ ] |
| E2.2 | 录制后立刻继续 inspect / ui-tree | 不应持续读取明显过时的 UI 状态 | [ ] |
| E2.3 | `doctor plugins` | 正常列出 plugin discovery 结果 | [ ] |

---

## 记录模板

每完成一条用例，记录以下信息：

| 用例 | 命令 | 实际结果 | 是否通过 | 备注 |
|------|------|---------|---------|------|
| A1.1 | `mac session start --pretty` | 返回 session_id=... | Pass |  |

建议额外保存：

- 失败时的完整命令输出
- 关键截图路径
- 生成的 trace 路径
- 生成脚本路径

---

## 最小验收集合

如果时间有限，优先跑以下 10 条：

1. `mac doctor backend --pretty`
2. `mac session start --pretty`
3. `mac app launch com.apple.calculator --pretty`
4. `mac element inspect --pretty`
5. `mac trace start --pretty`
6. 录制几次 Calculator 点击
7. `mac trace stop --pretty`
8. `mac trace codegen <TRACE_PATH> --output /tmp/fsq-trace.sh`
9. `bash /tmp/fsq-trace.sh`
10. `mac doctor plugins --pretty`

这 10 条能最快验证 fsq-mac 的核心用户价值是否真实可用。
