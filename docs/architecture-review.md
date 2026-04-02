# AutoGenesis Mac CLI — 架构评审报告

> 目标：做到 macOS 原生应用自动化领域的「Playwright 级别」CLI 工具
> 评审日期：2026-04-02

---

## 一、当前水平评估

### 总评：扎实的原型 — 满分 10 分中约 2.5 分（对标 Playwright）

基础架构设计合理，但距离世界一流仍有系统性差距。下面从 10 个维度逐一分析。

---

## 二、做得好的地方（已具备的竞争力）

| 优势 | 说明 | 对比 Playwright |
|------|------|----------------|
| **Agent-First 响应信封** | 每个响应包含 `ok`、`error.code`、`retryable`、`suggested_next_action`。AI Agent 可直接解析和决策 | **领先** — Playwright 没有为 Agent 消费设计 |
| **Daemon 自动生命周期** | 首次调用自动启动守护进程，fcntl 文件锁防竞态，PID/端口文件管理，30 分钟空闲自动退出，优雅关闭 | 与 Playwright Browser Server 同级 |
| **安全分级系统** | SAFE / GUARDED / DANGEROUS 三级，危险操作需 `--allow-dangerous` | **领先** — Playwright 无此机制 |
| **AppleScript 注入防护** | `_safe_applescript_str()` 覆盖所有插值点 | 安全意识良好 |
| **参数化路由覆盖测试** | `test_routes.py` 用参数化测试验证全部 30 条 CLI → dispatch 映射 | 工程纪律优秀 |
| **统一错误码体系** | 14 个错误码，每个错误带 `suggested_next_action` 和 `doctor_hint` | Agent 友好度高 |

---

## 三、与 Playwright 的核心差距（80% 的工作在这里）

### 差距 1：自动等待机制（CRITICAL — Playwright 的第一差异化能力）

**当前状态**：每次 click 后硬编码 `time.sleep(1)`，hotkey 前 `time.sleep(0.5)`。没有任何可操作性检查。

**Playwright 的做法**：每个操作前自动验证 5 项前置条件：

| 检查项 | 含义 |
|--------|------|
| Visible | 元素有非空边界框，非 `visibility:hidden` |
| Stable | 连续两帧动画中，边界框没有变化 |
| Enabled | 非 disabled 状态 |
| Editable | 非 readonly（仅 fill/type 操作） |
| Receives Events | 元素在点击坐标上是命中目标（无遮挡） |

**影响**：硬编码 sleep 既浪费时间（快的操作等 1 秒）又不可靠（慢的操作 1 秒不够）。这是最大的技术债。

---

### 差距 2：Locator 架构（CRITICAL）

**当前状态**：静态元素引用 `e0`, `e1`, ...。每次 `inspect()` 后引用全部失效。多步操作流程：

```
inspect → 找到 e5 是 "Submit" → click e5 → inspect（引用全部失效）→ 找到 e3 是输入框 → type e3 "hello"
```

**Playwright 的做法**：Locator 是 **惰性查询**，每次操作时重新解析，永不过期：

```javascript
// Playwright — 这个 locator 永远有效，每次用时才解析
page.getByRole('button', { name: 'Submit' }).click()
```

**影响**：当前的 inspect-then-act 模式让每个操作流程都需要额外的 inspect 步骤，增加了延迟和复杂度。

**目标状态**：

```bash
# 直接按角色 + 名称操作，无需先 inspect
mac element click --role AXButton --name "Submit"
mac element type --role AXTextField --name "Search" "hello"
```

---

### 差距 3：无 Adapter 抽象层（架构异味）

**当前状态**：`SessionManager` 直接 import 和实例化 `AppiumMac2Adapter`。没有接口、Protocol、或工厂模式。

**影响**：无法添加第二个后端（如直接使用 macOS Accessibility API 而不经过 Appium，或未来支持 Linux/AT-SPI）。

**需要**：定义 `Adapter` Protocol，加入适配器工厂。

---

### 差距 4：无追踪/录制/回放能力

| 能力 | Playwright | 当前 |
|------|-----------|------|
| 操作录制 | `codegen` 录制用户操作，自动生成测试代码 | 无 |
| Trace Viewer | DOM 快照 + 网络日志 + 控制台 + 源码关联 | 无 |
| 回放 | 从录制文件重放完整操作流程 | 无 |
| 操作步骤日志 | 每步操作带 before/after 截图 | 仅最终截图 |

**对于 macOS 原生场景，相当于**：记录每个操作的时间戳、操作前后的 accessibility tree diff、截图、元素状态变化。然后提供一个 HTML 查看器回放。

---

### 差距 5：错误传播模式不统一

**当前状态**：Adapter 层用返回码模式（`return {"error_code": "..."}`），Core 层有时捕获异常、有时检查返回码。两套心智模型。

**需要**：统一为一种模式。建议 Adapter 层抛出类型化异常（更 Pythonic），Core 层统一捕获和转译。

---

### 差距 6：性能问题

| 问题 | 影响 | 严重度 |
|------|------|--------|
| `inspect()` 双重遍历 | `page_source`（45-120 秒）+ `find_elements(XPATH, "//*")`。计算器 45 秒，复杂应用无法使用 | 高 |
| 硬编码 `sleep(1)` / `sleep(0.5)` | 每次操作至少浪费 0.5-1 秒 | 高 |
| 无 httpx 连接池 | 每次调用创建新 HTTP 连接 | 中 |
| AppleScript 子进程无缓存 | `app_current()`、`window_current()` 等每次都 spawn `osascript` | 中 |

---

### 差距 7：缺失的操作

| 缺失能力 | Playwright 等价 | 优先级 |
|----------|-----------------|--------|
| 断言命令（`assert visible/enabled/text`） | `expect(locator).toBeVisible()` | **高** |
| 坐标点击（`click-at x y`） | `page.mouse.click(x, y)` | **高** |
| 菜单栏操作（`menu click "File > Open"`） | 无直接等价（Mac 特有） | **高** |
| 剪贴板读写 | `navigator.clipboard` | 中 |
| 长按 / Force Touch | `page.mouse.down()` + 定时器 | 中 |
| 文件选择对话框 | `page.setInputFiles()` | 中 |
| `--verbose` / `--debug` 日志 | `DEBUG=pw:api` | 高 |
| Shell 补全 (zsh/bash) | Tab 补全 | 中 |
| `--version` | `npx playwright --version` | 低 |

---

### 差距 8：测试覆盖率不足

**当前**：~2,700 行代码，~48 个测试用例（约 1:56 的比例）。

**未覆盖的模块**：CLI 解析（`mac.py`）、客户端自动启动（`client.py`）、格式化器（`formatters.py`）、诊断工具（`doctor.py`）、集成测试（全 HTTP 路径）。

**Playwright** 的测试矩阵覆盖数千个测试用例 × 多浏览器。

---

### 差距 9：无 CI/CD 集成

没有 GitHub Actions 工作流、没有 JUnit XML 输出、没有 exit code 语义文档。

---

## 四、你的独特优势

**Playwright 自动化浏览器。你自动化原生 macOS 应用。这个领域没有世界一流的工具。**

最接近的竞品：

| 工具 | 弱点 |
|------|------|
| Appium + Mac2 Driver | 需要单独运行 Appium 服务器，无内置测试运行器，无自动等待 |
| XCUITest | 绑定 Xcode，仅支持 Swift/ObjC，无独立 CLI |
| Accessibility Inspector | 只读，不能执行操作 |
| macOS `osascript` | 无结构化 API，无元素定位，无会话管理 |

**如果你实现了 自动等待 + 惰性 Locator + Agent-First 响应 + Daemon 自动生命周期**，你拥有的是一个不存在的产品：**面向 AI Agent 的 Playwright 级别 macOS 原生应用自动化 CLI**。

Agent-First 响应设计已经领先 Playwright。应该在这个方向上加倍投入。

---

## 五、路线图：从 2.5 分到 10 分

### 第零阶段：用户可感知的基础（最高优先级）

> 没有这两项，后面所有工作对外都是不可见的。

| # | 任务 | 说明 | 预期效果 |
|---|------|------|---------|
| 0a | **CLI 封装为可安装命令** | `pyproject.toml` 加 `[project.scripts]` 入口点，支持 `pip install` / `pipx install` / `uv tool install`。用户直接执行 `mac` 命令，不再需要 `uv run python mac.py` | 从「脚本」变成「工具」 |
| 0b | **Agent Skill 封装** | 编写 Claude Code / Copilot 可直接使用的 skill 文件。包含：工具列表、使用模式（先 inspect 再操作）、错误处理策略（ELEMENT_NOT_FOUND → 重新 inspect）、常见流程模板 | Agent 开箱即用，不需要人教 |
| 0c | **区域截图** | `capture screenshot` 支持 `--rect x,y,w,h` 和 `--element <ref>` 参数，按指定区域或元素边界截图，不必每次全屏 | 截图更精准，Token 消耗更低 |

**安装体验目标**：

```bash
# 安装（一条命令）
pipx install autogenesis-mac-cli

# 使用（干净的命令）
mac doctor
mac session start
mac element inspect
mac element click e0
```

**Skill 使用示例**（Agent 视角）：

```
Tester: "点击计算器的 5 + 3 然后截图"

Agent 自动执行:
  mac session start
  mac app launch com.apple.calculator
  mac element inspect                    ← 探索界面
  mac element click e5                   ← 点 5（静态引用）
  mac element click e2                   ← 点 +
  mac element click e3                   ← 点 3
  mac element click e8                   ← 点 =
  mac capture screenshot ./result.png    ← 截图验证
```

---

### 第一阶段：内部质量（2.5 → 4 分）

| # | 任务 | 预期效果 |
|---|------|---------|
| 1 | **Adapter Protocol 抽象** — 定义接口，解耦 SessionManager | 可扩展多后端 |
| 2 | **统一错误传播** — 选一种模式（建议：类型化异常），全面应用 | 代码可维护性 |
| 3 | **httpx 连接池** — 复用 `httpx.Client()` | 减少延迟 |
| 4 | **消灭硬编码 sleep** — 替换为可配置的 post-action 延迟（默认 0） | 速度 × 2-3 |
| 5 | **`--version`、`--verbose`、`--debug`** | 基本 CLI 规范 |
| 6 | **测试覆盖率 ≥ 80%** — CLI 解析、client、formatters、doctor | 质量基线 |

### 第二阶段：核心差异化能力（4 → 6 分）

> 惰性 Locator 是录制/回放/Codegen 整条链的第一块砖。

| # | 任务 | 预期效果 |
|---|------|---------|
| 7 | **惰性 Locator** — `--role AXButton --name Submit` 操作时解析，与静态引用 `e0` 共存 | 告别 inspect-then-act（确定性场景） |
| 8 | **自动等待** — 操作前检查 visible / enabled / stable | 消灭 sleep，消灭 flaky |
| 9 | **断言命令** — `mac assert visible/enabled/text/value` | 完整测试能力 |
| 10 | **菜单栏操作** — `mac menu click "File > Open"` | Mac 特有高频需求 |
| 11 | **坐标操作** — `mac input click-at 100 200` | 覆盖无 accessibility 的场景 |

**两种定位模式共存**（本阶段设计关键）：

```bash
# 模式 1：静态引用 — Agent 探索式使用，先看再决策
mac element inspect
mac element click e5

# 模式 2：惰性 Locator — 确定性操作，可录制回放
mac element click --role AXButton --name "Submit"

# CLI 根据参数格式自动识别，无需切换
```

**Locator 优先级**（Agent 从探索转换为确定性操作时的选择策略）：

| 优先级 | 策略 | macOS 属性 | 稳定性 |
|--------|------|-----------|--------|
| 1 | `--id` | `accessibilityIdentifier` | 最稳定（开发者主动设置） |
| 2 | `--role` + `--name` | `AXRole` + `AXTitle/AXDescription` | 中等（多语言会变） |
| 3 | `--label` | `AXLabel` | 中等 |
| 4 | `--xpath` | accessibility hierarchy path | 最脆弱 |

### 第三阶段：开发者体验（6 → 8 分）

> 依赖第二阶段的惰性 Locator：录制记录的是 Locator 查询，不是静态引用。

| # | 任务 | 预期效果 |
|---|------|---------|
| 12 | **操作录制** — 记录所有操作 + accessibility tree diff，每步存储为 Locator 查询 | 可追溯、可调试、可回放 |
| 13 | **回放** — 从录制文件按 Locator 重新查找并执行操作 | 回归测试 |
| 14 | **Trace Viewer** — HTML 查看器（截图 + tree diff + 时序） | 事后调试 |
| 15 | **Shell 补全** — zsh / bash / fish | CLI 体验 |
| 16 | **CI 集成** — GitHub Actions workflow + JUnit XML | 工程化 |
| 17 | **分屏隔离文档/脚本** — 提供 AppleScript 将被测应用移到独立 Space 的方案，集成到 skill 启动流程 | 自动化不受干扰 |

### 第四阶段：打磨（8 → 10 分）

| # | 任务 | 预期效果 |
|---|------|---------|
| 18 | **Codegen** — 从录制生成 CLI 脚本或 Python 代码 | Playwright 标志性能力 |
| 19 | **性能优化** — 绕过 Appium `page_source`，直接用 Accessibility API 单次遍历 | inspect 从 45s → 毫秒级 |
| 20 | **插件系统** — 自定义适配器、自定义 Locator 策略 | 可扩展性 |
| 21 | **文档** — 面向任务的文档（快速开始、常见场景、调试、CI） | 开发者入门 |

---

### 依赖关系总览

```
第 0 阶段: CLI 封装 + Skill + 区域截图
    ↓ （用户可以开始用了）
第 1 阶段: 内部质量（Adapter 抽象、错误统一、消灭 sleep、测试）
    ↓
第 2 阶段: 惰性 Locator + 自动等待 + 断言 + 菜单 + 坐标
    ↓ （Locator 是下面所有能力的前置依赖）
第 3 阶段: 录制 → 回放 → Trace Viewer → Shell 补全 → CI
    ↓
第 4 阶段: Codegen → 性能优化 → 插件 → 文档
```

---

## 六、当前架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                     CLI (mac.py) 212 行                      │
│                     argparse 子命令树                         │
│                     --pretty / --session / --strategy        │
└──────────────────┬───────────────────────────────────────────┘
                   │ HTTP (httpx)
┌──────────────────▼───────────────────────────────────────────┐
│                  Client (client.py) 174 行                    │
│                  自动启动 Daemon、重试、超时管理               │
└──────────────────┬───────────────────────────────────────────┘
                   │ HTTP POST → localhost:19444
┌──────────────────▼───────────────────────────────────────────┐
│                  Daemon (daemon.py) 327 行                    │
│                  Starlette/Uvicorn，路由分发                  │
│                  安全检查 (check_safety)                      │
│                  空闲看门狗 (30 分钟)                          │
├──────────────────────────────────────────────────────────────┤
│                  Core (core.py) 457 行                        │
│                  产品语义层 — 26 个公开方法                    │
│                  安全分级 · 响应封装 · 会话路由                │
├──────────────────────────────────────────────────────────────┤
│                  Session (session.py) 136 行                  │
│                  单调递增 ID (s1, s2, ...)                    │
│                  JSON 文件持久化 → ~/.autogenesis/            │
└──────────────────┬───────────────────────────────────────────┘
                   │ Appium WebDriver + AppleScript subprocess
┌──────────────────▼───────────────────────────────────────────┐
│           Adapter (adapters/appium_mac2.py) 898 行            │
│           Appium Mac2 驱动 + AppleScript 降级回退             │
│           元素引用管理 (e0, e1, ... 按代次作废)               │
│           安全字符串检查 (_safe_applescript_str)               │
└──────────────────────────────────────────────────────────────┘
```

**数据流示例**：`mac element click e0`

1. `mac.py` → 解析 domain=element, action=click, ref=e0
2. `client.py` → POST `{"ref":"e0"}` 到 `http://127.0.0.1:19444/api/element/click`
3. `daemon.py` → 安全检查 → 路由到 `core.element_click()`
4. `core.py` → 获取适配器 → 调用 `adapter.click("e0")`
5. `appium_mac2.py` → 解析 e0 引用 → WebDriver ActionChains click → 等 1 秒 → 失效所有引用
6. 返回路径：adapter `{}` → core `success_response()` → daemon `JSONResponse` → client `.json()` → mac.py 输出

---

## 七、当前代码量统计

| 文件 | 行数 | 职责 |
|------|------|------|
| `mac.py` | 212 | CLI 入口，argparse |
| `daemon.py` | 327 | HTTP 守护进程 |
| `core.py` | 457 | 产品语义 + 安全 |
| `client.py` | 174 | HTTP 客户端 |
| `session.py` | 136 | 会话管理 |
| `models.py` | 207 | 数据模型 |
| `doctor.py` | 182 | 环境诊断 |
| `adapters/appium_mac2.py` | 898 | Appium 适配器 |
| `formatters.py` | 90 | 输出格式化 |
| **合计** | **~2,683** | |
| 测试文件（8 个） | ~300 | 48 个测试用例 |

---

## 八、结论

这个项目有一个正确的起点：**Agent-First 设计哲学 + Daemon 自动生命周期 + 安全分级**。这三个设计决策比 Playwright 更适合 AI Agent 场景。

核心差距在于两个已被验证的技术模式：**自动等待**和**惰性 Locator**。这两项是 Playwright 从 Selenium 时代脱颖而出的根本原因。实现它们将直接把这个工具从「能用的原型」提升到「生产级工具」。

独特的市场定位是：**世界上没有一个面向 AI Agent 的、Playwright 级别的 macOS 原生应用自动化 CLI**。这个空白是真实存在的。
