# 多 Agent 协作控制台重构设计

> Status: Approved design (2026-06-22)
> Scope: frontend only
> Target: replace the "5 张等宽 AgentCard" workspace with a 3-column collaboration console

## 1. 背景与目标

当前 `frontend/src/App.tsx:212-224` 在 `view === 'running' | 'report' | 'failed'` 时渲染 5 张等宽 `AgentCard`（市场/竞品/财务/风险/战略）+ `ChallengeLog` + `EvidenceReport`。卡片内容空洞，无法表达多 Agent 之间的任务拆解、依赖、交接与协作过程。

重构目标：参考 WorkBuddy 工作台理念，改造成"多 Agent 协作控制台"，强调**任务正在如何被多个 Agent 协同完成**，而非"系统里有哪些 Agent"。具体诉求：

- 三栏布局（左 240px 团队栏 / 中主工作区 / 右 320px 详情检查器）+ 顶部紧凑任务栏
- 不使用 Agent 卡片墙、不使用看板、不设计为聊天群、不使用拟人头像
- 视觉理性克制：暖白背景、细边框、极少阴影、8–12px 圆角
- 状态色：执行中蓝/靛青、完成绿、等待灰、需要确认琥珀、失败红

## 2. 范围

### In scope

- 前端 `frontend/src/` 全部改造
- `App.tsx` 在分析进行 / 完成 / 失败态挂载新 `<Workspace>` 容器
- 新增派生 hook `useRunWorkspace` 把扁平事件流编译成 Round → AgentTask → TaskEvent 树
- 顶栏 / 左栏 / 中区 / 右栏四套新展示组件
- 完整单元测试 + 集成测试
- 复用现有 `EvidenceReport` 组件嵌入到 R3 artifact

### Out of scope（明确不做）

- 后端 API 改动（暂停、终止、按 Agent 重试、给单 Agent 发指令的真实通道均**不实现**，前端按钮 disabled 占位）
- 新依赖引入（无 zustand / redux / styled-components / framer-motion / dayjs）
- 暗色模式、i18n、键盘快捷键、主题切换
- SSE 层重构（`lib/sse.ts` 原样保留）
- 响应式小屏适配（仅桌面 ≥ 1280px）
- 旧 `AgentCard.tsx` / `ChallengeLog.tsx` 文件保留但停用，不删除

## 3. 架构

### 3.1 路线选择

采用**派生 hook + 纯展示子组件**模式（候选方案 B）：
- `useRunWorkspace(events, runInfo)` hook 把扁平事件流编译成结构化 `Round[] → AgentTask[] → TaskEvent[]` 树
- 子组件纯展示，按 props 接收派生结果
- 沿用 `HistoryCard` 的 BEM CSS 模式（每组件一份 `.css`）

否决方案：
- A 单文件大组件：读写集中但 1000+ 行不可维护
- C `useReducer` 状态机：对展示为主的流式日志过度设计

### 3.2 文件结构

```
frontend/src/
├── App.tsx                                  # 改：仅挂载 <Workspace>
├── lib/
│   ├── types.ts                             # 不动
│   ├── sse.ts                               # 不动
│   ├── workspace-types.ts                   # 新：派生结构 TS 类型
│   ├── buildWorkspace.ts                    # 新：纯函数 events → Workspace 树
│   └── useRunWorkspace.ts                   # 新：React hook，封装派生 + selection
└── components/
    ├── AgentCard.tsx                        # 保留停用
    ├── ChallengeLog.tsx                     # 保留停用
    ├── EvidenceReport.tsx                   # 不动（被 R3 artifact 复用）
    ├── HistoryCard.tsx / HistoryList.tsx    # 不动
    ├── StartupForm.tsx                      # 不动
    └── workspace/                           # 新目录
        ├── Workspace.tsx                    # 三栏 + 顶栏容器
        ├── WorkspaceTopbar.tsx              # 顶栏
        ├── AgentTeamSidebar.tsx             # 左 240px
        ├── CollaborationTimeline.tsx        # 中主区
        ├── TimelineTaskItem.tsx             # 单个任务节点（含展开产物）
        ├── DetailInspector.tsx              # 右 320px
        ├── AgentAvatar.tsx                  # 左栏 + 右栏共用的状态色点 + 名称
        └── workspace.css                    # 全局 CSS 变量 + 三栏栅格
```

### 3.3 数据流

```
App.tsx
  ├─ events (from SSE)
  ├─ report, errorMsg, runInfo (from fetch + SSE)
  └─ <Workspace events report errorMsg runInfo onBack />
       ├─ useRunWorkspace(events, runInfo, report) → { rounds, agents, progress, status, selectedTarget, setSelectedTarget }
       ├─ <WorkspaceTopbar       progress status runInfo onBack />
       ├─ <AgentTeamSidebar      agents selectedTarget onSelect />
       ├─ <CollaborationTimeline rounds   selectedTarget onSelect />
       └─ <DetailInspector       rounds   selectedTarget onSelect />
```

`App.tsx` 不再直接持有 `events` 的语义，只做透传。`useRunWorkspace` 在 `<Workspace>` mount 时初始化，随 events 变化重跑派生。

## 4. 派生数据模型

### 4.1 类型定义（`lib/workspace-types.ts`）

```ts
type RoundId = 'r1' | 'r2' | 'r3'

type AgentStatus =
  | 'pending'        // 未开始
  | 'running'        // 正在执行
  | 'waiting'        // 等待依赖（R1 risk_reviewer / R2-B targets）
  | 'needs_input'    // 需要确认（本期不主动触发，预留）
  | 'done'           // 已完成
  | 'failed'         // 失败

interface AgentTaskEvent {
  id: string                          // event type + timestamp + idx
  kind: 'start' | 'tool' | 'message' | 'challenge_issued'
      | 'challenge_responded' | 'end'
  timestamp: number                   // 派生，按事件流顺序递增
  agent: AgentName
  round: RoundId
  payload: Record<string, unknown>    // 原始事件字段
}

interface AgentTask {
  agent: AgentName
  round: RoundId
  subRound?: 'A' | 'B'                // R2 才有：A=issue, B=respond
  status: AgentStatus
  startedAt: number | null
  endedAt: number | null
  events: AgentTaskEvent[]
  output_summary?: unknown
  error?: string
}

interface Round {
  id: RoundId
  title: string
  subtitle: string
  status: 'pending' | 'running' | 'done' | 'failed'
  tasks: AgentTask[]
  transitionedAt: number | null
}

interface AgentSummary {
  name: AgentName
  label: string
  role: 'orchestrator' | 'analyst'
  status: AgentStatus                 // 跨轮聚合
  currentAction: string
  progress: { done: number; total: number }
}

interface WorkspaceState {
  rounds: Round[]
  agents: AgentSummary[]
  progress: { done: number; total: 11; percent: number }
  status: 'pending' | 'running' | 'done' | 'failed'
}

type SelectedTarget =
  | { kind: 'agent'; agent: AgentName }
  | { kind: 'event'; taskId: string; eventId: string }
  | { kind: 'artifact'; taskId: string }
  | null
```

### 4.2 静态配置

```ts
// buildWorkspace.ts

const ROUND_META: Record<RoundId, { title: string; subtitle: string }> = {
  r1: { title: '第一轮 · 独立分析', subtitle: '4 个 Agent 并行展开市场、竞品、财务、风险' },
  r2: { title: '第二轮 · 交叉挑战', subtitle: '市场/竞品/财务 Agent 互相质询并回应' },
  r3: { title: '第三轮 · 战略综合', subtitle: '战略顾问综合所有输入，给出 Go/No-Go 结论' },
}

const EXPECTED_TASKS_PER_AGENT: Record<AgentName, number> = {
  market_analyst: 3,        // R1 + R2-A + R2-B
  competitor_researcher: 3, // R1 + R2-A + R2-B
  finance_analyst: 3,       // R1 + R2-A + R2-B
  risk_reviewer: 1,         // R1
  strategy_advisor: 1,      // R3
}
// 总 = 11，用作 progress.total
// 注：R2-B 在引擎中按需启动（target 无未决挑战时跳过），
// 因此实际 task 数可能 < 11。progress 用 11 作为固定分母，
// run.complete 时强制 100% 兜底。
```

### 4.3 派生算法

`buildWorkspace(events: RunEvent[], runInfo, report): WorkspaceState` 是纯函数，单遍扫描事件流。

**事件 → task 归属表**：

| RunEvent.type | 归属 task | 副作用 |
|---|---|---|
| `run.start` | — | 触发 `transitionedAt` 初始化 |
| `round.transition` | — | 创建/激活对应 Round |
| `agent.start` | 新建或复用 task（R2 同 agent 第 2 个 start 拆为 R2-B） | status → running |
| `agent.message` | 当前 running task | push event |
| `tool.start` | 当前 running task | push event |
| `tool.end` | 当前 running task | push event（含 evidence_id） |
| `challenge.issued` | issuer 当前 running task（必为 R2-A） | push event |
| `challenge.responded` | target 的 R2-B task（若已 start）否则回退 R2-A | push event |
| `agent.end` | 关闭当前 running task | status → done/failed |
| `run.complete` | — | Round.r3 → done，progress 强制 100% |
| `run.failed` | 不动 agent（除非 error 精确含 name） | 全局 status failed |

**状态推断不变量**：

1. 同一 `(round, agent)` 至多一个 running task。R2 的 issue / respond 是两条独立 task。
2. `agent.end` 必须关闭 running task；找不到则忽略（不新建空 task）。
3. `risk_reviewer` 在 R1 的 waiting→running：仅当其他 3 个 R1 task 都 done 时推断；若事件流已含 `agent.start`，以事件为准。
4. R2-B target 的 waiting 状态：R2-A 完成后、R2-B `agent.start` 出现前。
5. 失败归因保守：`run.failed.error` 必须**精确 token 匹配**（`error.split(/\W+/).includes(name)`）才标红 agent。否则只把 Round 标 failed，不动 agent 状态色。
6. 事件按到达顺序处理，**不重排**。

**进度兜底**：
- `progress.done = count(task.status === 'done')`
- `progress.total = 11`
- `progress.percent = runInfo.status === 'complete' ? 100 : round(done/11 * 100)`
- 失败 task 不计 done
- R2-B 在引擎中按需启动（target 无未决挑战时跳过），实际 task 数可能 < 11。
  - 正常情况：3 个分析师都有挑战 → 11 个 task，progress 0% → 100% 平滑增长
  - 边缘情况：某 agent 无挑战 → 实际 task < 11，progress 可能卡在 < 100%。
    由 `run.complete` 触发强制 100% 兜底。

### 4.4 Restore 兼容

`App.tsx:24-36` 现有的 `buildEventsFromR1Outputs` 函数迁移到 `useRunWorkspace` 内部，输出标准 `AgentTaskEvent[]` 注入 events 列表头部。

- restore 路径下没有 `agent.start` 只有合成 `agent.end`：派生算法容错（task 直接标 done，`startedAt = null`，时间线不显示"开始分析"行）
- SSE 重连后真实事件到来时去重：key = `(round, agent, type, hash(output_summary))`，真实事件覆盖合成事件

## 5. 视觉系统

### 5.1 色板（`workspace.css` 顶部 CSS 变量）

```css
:root {
  --ws-bg:           #f7f7f5;   /* 暖灰白主背景 */
  --ws-surface:      #ffffff;    /* 三栏面板背景 */
  --ws-border:       #e8e8e8;
  --ws-border-strong:#d2d2d2;
  --ws-text:         #1d1d1f;
  --ws-text-muted:   #737377;
  --ws-text-faint:   #a1a1a6;
  --ws-radius:       10px;
  --ws-radius-sm:    6px;
  --ws-shadow-soft:  0 1px 2px rgba(0,0,0,0.03);

  --ws-status-running:     #2563eb;   /* 靛青 */
  --ws-status-running-bg:  #eff6ff;
  --ws-status-done:        #08783e;   /* 绿 */
  --ws-status-done-bg:     #edf8f2;
  --ws-status-waiting:     #86868b;   /* 灰 */
  --ws-status-waiting-bg:  #f2f4f7;
  --ws-status-needs_input: #b45309;   /* 琥珀 */
  --ws-status-needs_input-bg:#fff5e8;
  --ws-status-failed:      #c22f2f;   /* 红 */
  --ws-status-failed-bg:   #fff0f0;

  --ws-font-sans: -apple-system, "PingFang SC", "Microsoft YaHei",
                  "Helvetica Neue", Arial, sans-serif;
}
```

### 5.2 动效约束

仅两处允许 pulse 动画（复用 `history-pulse` 1.8s ease-in-out）：
- 左栏 Agent 状态色点 running 态
- 中间时间线当前 running task 左侧 2px 竖条

其他状态无动画。`transition` 仅允许 160ms 的 `border-color / background-color / opacity`，不用 `transform`。

### 5.3 字号层级

| 用途 | 字号 / 字重 |
|---|---|
| 主任务名 / 节点标题 | 15px / 600 |
| 正文 | 13px / 1.5 行高 |
| 元信息（时间、工具名） | 12px / `--ws-text-muted` |
| Agent 名称 | 13px / 600 |
| 小标签（Orchestrator / R2-A 等） | 10–11px / faint / 字母间距 0.05em |

### 5.4 间距

4px 基线网格：4 / 8 / 12 / 16 / 24。

## 6. 组件详细设计

### 6.1 `Workspace` 容器

- 顶栏 56px + 三栏剩余高度
- 三栏栅格：`grid-template-columns: 240px 1fr 320px`
- 最小宽 1280px，更窄时允许横向滚动（桌面 only）

### 6.2 `WorkspaceTopbar`

```
[← 返回]  市场进入策略分析  [progress bar 32%]  ● 进行中  [⏸ 暂停] [⏹ 终止] [⤓ 导出]
```

- **返回按钮**：transparent + 1px border，调用 `onBack`（清 URL、清 state）
- **主任务名**：`runInfo.startup_idea`，>32 字符截断 + tooltip
- **进度条**：12px 高 / 180px 宽，填充随 `progress.percent` 变色（running→蓝 / done→绿 / failed→红）
- **总体状态徽章**：复用 HistoryCard 胶囊样式，文案 `进行中 / 已完成 / 分析失败`
- **暂停 / 终止按钮**：disabled + `title="暂停功能即将支持"`
- **导出按钮**：`report != null` 时启用，导出 `JSON.stringify({run_id, startup_idea, report}, null, 2)` 为 `.json` 文件

失败态：徽章红 / 进度条红 / 下方加 12px 红字显示 `errorMsg`。

### 6.3 `AgentTeamSidebar`

- 固定 240px，右边框 1px `--ws-border`
- 顶部 24px padding 区域：`团队` 标题
- **Orchestrator 卡片**（`strategy_advisor`）：
  - `background: var(--ws-bg)`，1px border，10px radius，12px padding
  - 12px 状态色点 + 名称 + `Orchestrator` 小标签 + `currentAction`
  - 可点（选中后左侧 2px 竖条变蓝）
- **普通 Agent 列表**（市场 / 竞品 / 财务 / 风险，固定顺序）：
  - `padding: 10px 16px`，hover `--ws-bg` 背景
  - 8px 状态色点 + 名称 / `currentAction` 单行截断 / `<done>/<total> 任务`
  - 选中态：左 2px 竖条 + `--ws-bg` 背景
- **状态色点样式**：
  - running：实心 + pulse
  - waiting：空心环（2px border，透明背景）
  - 其他：实心

失败 agent：左 2px 竖条变红 + 第二行失败原因（单行截断 + tooltip）

空态：所有 agent 显示 `pending`，`currentAction = "等待启动"`

### 6.4 `CollaborationTimeline`

- flex 1，`--ws-bg` 背景，`overflow-y: auto`
- padding `24px 32px 48px`，max-width 920px 居中
- 三个 `<section class="ws-round">` 纵向排列

**Round header**：`第一轮 · 独立分析` + 状态徽章 + 折叠按钮 `▾/▸`

**折叠规则**：
- running / done → 默认展开
- pending → 默认折叠
- failed → 强制展开不可折叠

**任务节点（`TimelineTaskItem`）**：
```
│ ● 市场分析师 · R1                              ● 执行中
│   正在搜索：AI Agent startup 2025
│   └ 3 条工具调用 · 0 条挑战
│   ▸ 展开产物
```

- 左 2px 竖条按 status 变色
- 状态点 + Agent 名称 + round 标签 + 状态徽章
- `currentAction`：取最新事件简述
- 元信息行：`N 条工具调用 · N 条挑战`
- `▸ 展开产物`：仅在有 `output_summary` 或 ≥1 个 tool.end 时显示

**展开产物区块**（内嵌，不弹卡片）：
```
─────────────────────────
时间线（紧凑）
  09:42  开始分析
  09:43  搜索：AI Agent 市场规模 2025 → ev-3a2f1
  09:51  提交产物
─────────────────────────
产物预览（按 agent 类型差异化渲染）
  TAM:  $XX B
  SAM:  $XX B
  ...
  [查看完整 JSON]   ← 复制到剪贴板
```

**事件文案映射**：
- `agent.start` → "开始分析"
- `tool.start` → `搜索：<input_preview 前 40 字>`
- `tool.end` → `搜索完成 → <evidence_id 或 "无证据">`
- `agent.message` → `<content_summary 前 60 字>`
- `challenge.issued` → `向 <target> 发起挑战：<claim 前 40 字>`
- `challenge.responded` → `回应 <issuer>：<response 前 40 字> [<verdict>]`
- `agent.end` → `提交产物` 或 `失败：<error>`

**R2 特殊**：同一 agent 拆成 R2-A（发起挑战）和 R2-B（回应挑战）两条 task 节点。

**R3 完成后**：展开产物区块替换为 `<EvidenceReport report={...} />`，不再在时间线底部单独留 `<EvidenceReport>`。

**空态**：events 为空时三 Round 全部待启动，居中显示 `"战略顾问正在拆解任务，即将分配给其他 Agent…"`。

### 6.5 `DetailInspector`

固定 320px，左 1px border，`overflow-y: auto`，padding `20px 24px`。

默认 selection：`{ kind: 'agent', agent: 'strategy_advisor' }`。

**A. Agent 面板**（点击左栏 Agent）：
- 顶部：状态点 + 名称 + 角色标签（Orchestrator / Analyst）
- `状态` 行：状态点 + 中文文案
- `当前动作`：agent.currentAction
- `执行步骤`：当前 round + task 状态
- `跨轮任务`：列出该 agent 在各轮的 task 一行
- `补充指令`：textarea + disabled 发送按钮 + tooltip "运行中追加指令将在下一版支持"
  - 纯占位，不写 state
  - 点击发送显示提示行 "已记录，下个版本会真正送达"

**B. Event 面板**（点击时间线的工具/挑战事件）：
- `← 返回 Agent 详情` 链接
- 事件类型徽章 + agent + 时间
- 工具名 / 输入预览 / 输出预览
- 引用证据：`[查看 ev-xxx]` 调用 `/evidence/<id>` 弹 modal（复用 EvidenceReport 的 modal 样式）
- 所属任务：点击切回该 task 的 artifact 面板

**C. Artifact 面板**（点击"展开产物"）：
- 按 agent 类型差异化渲染：

| Agent | 渲染形式 |
|---|---|
| market_analyst | TAM / SAM / SOM + 趋势 + 用户画像 |
| competitor_researcher | 竞品表（名称 / 差异化 / 威胁等级） |
| finance_analyst | LTV / CAC / 毛利率 / 定价 / 资金需求 |
| risk_reviewer | 风险表（维度 / 严重程度 / 缓解） |
| strategy_advisor | 嵌入 `<EvidenceReport>` 组件 |

- 未知字段兜底：JSON viewer 折叠块（默认折叠）
- 底部：`复制 JSON`（活跃）+ `重试任务`（disabled + tooltip）

**失败态**：agent 失败时状态行下方加 13px / `--ws-status-failed` 错误原因。

## 7. 事件映射与边界情况

详见 §4.3。摘要：

- 同一 `(round, agent)` 至多一个 running task
- R2 同 agent issue / respond 是两条独立 task
- `agent.end` 必须关闭 running task；找不到则忽略
- R1 risk_reviewer 的 waiting 由前 3 个 task 推断
- R2-B target 的 waiting 由 R2-A 完成推断
- 失败归因保守：error 精确 token 匹配才标红 agent
- 事件按到达顺序处理，不重排
- restore 路径合成事件 + 真实事件去重

## 8. 测试策略

栈：vitest + @testing-library/react + jsdom（无新依赖）。

### 8.1 纯函数测试（`tests/lib/buildWorkspace.test.ts`）

覆盖 §4.3 全部边界事件清单，每 case 一个 `it`：

- 空事件 → 所有 task pending，progress 0%
- 仅 run.start → Round.r1 running
- R1 前三 done → risk_reviewer inferred waiting
- R1 前三 done + risk_reviewer 收到 agent.start → running
- R2-A agent.end 后无 R2-B start + 收到 challenge.responded → 归 R2-A
- agent.end output_summary.error → task.failed
- run.failed error 不含 agent name → 仅 Round.failed
- run.failed error 含 `market_analyst` → 该 agent 当前 task.failed
- run.complete 缺 R3 agent.end（restore） → progress 强制 100% + R3 task 兜底 done
- 合成事件 + 真实事件混合 → 去重正确
- 事件顺序：先 agent.start 后 round.transition → task 正确归属

### 8.2 子组件渲染测试

- `AgentTeamSidebar.test.tsx`：Orchestrator 顶部 / 4 Agent 顺序 / 点击 / pulse class / failed 竖条 / 空态
- `CollaborationTimeline.test.tsx`：3 Round header / 折叠规则 / 点击任务 / 展开产物 / R2 拆 A/B / 失败展开
- `DetailInspector.test.tsx`：默认选 strategy_advisor / 三种 selection 切换 / 按 agent 类型差异化 artifact / 未知 schema 兜底 / EvidenceReport 嵌入 / failed 错误显示
- `WorkspaceTopbar.test.tsx`：progress 联动 / 失败态 / disabled 按钮 / 导出 Blob mock / 返回

### 8.3 集成测试（`tests/integration/workspace-flow.test.tsx`）

mount `<Workspace>`，喂 30 条录制事件，断言：
- 进度从 0% → ~9% (1/11) → ... → 100%
- 左栏 Agent 状态色点依次切换
- 中间时间线 R1 → R2 → R3 依次展开
- R3 展开后 EvidenceReport mount
- 右栏默认显示 Orchestrator

### 8.4 旧测试处理

- `AgentCard.test.tsx` / `ChallengeLog.test.tsx`：保留（死代码测试零成本）
- `App.test.tsx`：更新断言，`view === 'running'` 时 mount `<Workspace>` 而非 5 张 AgentCard

### 8.5 不写测试

- CSS 视觉效果（颜色、间距、动画）—— 人工目测
- SSE 重连（`sse.test.ts` 已覆盖）
- 真实 LLM 端到端

## 9. 实施顺序

6 个独立 commit（可合并）：

1. **类型 + 派生算法 + 测试**（无 UI 改动）
   - `lib/workspace-types.ts` / `lib/buildWorkspace.ts` / `lib/useRunWorkspace.ts`
   - `tests/lib/buildWorkspace.test.ts`
   - 跑测试全绿，不影响生产

2. **`workspace.css` + `WorkspaceTopbar` + 测试**
   - 定下色板 / 字号 / 间距视觉锚点

3. **`AgentTeamSidebar` + `AgentAvatar` + 测试**

4. **`CollaborationTimeline` + `TimelineTaskItem` + 测试**
   - 复用 `EvidenceReport`

5. **`DetailInspector` + 测试**
   - 复用 `EvidenceReport` 的 modal

6. **`Workspace` 容器 + `App.tsx` 切换 + 集成测试**
   - 串联 hook + 三栏 + 顶栏
   - 移除 `App.tsx` 中的 `AgentCard` grid + `ChallengeLog`
   - `buildEventsFromR1Outputs` 迁到 hook
   - 更新 `App.test.tsx`
   - 新增 `tests/integration/workspace-flow.test.tsx`

## 10. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| R2-A/R2-B task 拆分判断错误 | 高 | 中 | §4.3 不变量 #1 强制约束 + 针对测试 |
| 派生算法对乱序事件过敏感 | 中 | 低 | 不重排；集成测试加乱序 fixture |
| LLM output_summary 偏离预设 schema | 高 | 低 | §6.5 兜底分支 + 测试 |
| EvidenceReport 嵌入样式冲突 | 中 | 中 | 保留原组件不改；必要时最小样式 wrap |
| 1280px 三栏挤压 | 低 | 低 | `min-width: 1280px` + 横向滚动 |
| 失败归因误判（error 巧合含 agent name） | 低 | 低 | 精确 token 匹配（`split(/\W+/).includes`） |

## 11. 验收标准

合并后以下场景必须工作：

1. 启动新分析：空态 → R1 三并行 → risk_reviewer waiting → running → R2 双阶段 → R3 → EvidenceReport
2. 中途刷新 `?run=xxx`：checkpoint 恢复 + SSE 重连，状态正确还原
3. 点击左栏 Agent → 右栏切换
4. 点击工具调用 → 右栏 event 详情 + evidence modal
5. 点击"展开产物" → 内嵌区块按 agent 类型差异化渲染
6. 失败态：顶栏红 / 进度条红 / 失败 task 红标识
7. 完成态：导出按钮活跃，下载 JSON
