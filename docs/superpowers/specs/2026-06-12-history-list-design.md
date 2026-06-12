# History List on Homepage — Design Spec

## Motivation

After each analysis, the user currently has no way to revisit past results or re-run a previous idea without retyping it. Add a history list on the homepage to solve this.

## Layout

**B — Top/bottom**: the analysis form stays on top (unchanged), the history list sits below it.

## Card Design

Each history card shows:

| Field | Source | Note |
|---|---|---|
| Startup idea text | `Run.startup_idea` | Truncate to ~40 chars with ellipsis |
| Decision badge | `Run.final_report.decision` | Go(green) / No-Go(red) / Conditional-Go(orange). Hidden for non-complete runs. |
| Running indicator | `Run.status` | Blue pulsing badge for queued/running runs |
| One-sentence summary | `Run.final_report.executive_summary` | For complete runs only. For running: "分析进行中...". For failed: "分析失败". |
| Relative time | `Run.created_at` | "刚刚" / "X 分钟前" / "X 小时前" / "昨天" / "X月X日" |

## Card Actions

| Action | Trigger | Behavior |
|---|---|---|
| Re-run | "重跑" button on each card | POST /runs with the same `startup_idea`, navigate to running view |
| View report | Click card body (complete runs) | Navigate to report view for that `run_id` |
| View progress | "查看" button (running runs) | Navigate to running/team view for that `run_id` |
| Delete | "删除" button (hard delete) | DELETE /runs/{run_id}, remove card from list |

## Pagination

- Default: show 10 most recent runs
- "Load more" button at bottom loads next 10
- Backend: `GET /runs?limit=10&offset=0`

## Backend Changes

### New: `GET /runs` — list runs

Query params: `limit` (default 10), `offset` (default 0).  
Returns runs ordered by `created_at DESC`.  
Each item extracts `decision` and `executive_summary` from `final_report` JSON when run is complete.

```json
{
  "runs": [
    {
      "run_id": "...",
      "startup_idea": "面向中小企业的 AI Agent 客服平台",
      "status": "complete",
      "decision": "Go",
      "executive_summary": "市场空间充足，建议以垂直行业为切入点",
      "created_at": "2026-06-12T10:30:00Z"
    }
  ],
  "total": 23
}
```

### New: `DELETE /runs/{run_id}` — hard delete

Deletes the Run row and cascades to associated Evidence and Challenge rows.  
Returns 204 No Content on success, 404 if not found.

### Repository additions

- `list_runs(session, limit, offset)` — query with ORDER BY created_at DESC + LIMIT/OFFSET
- `count_runs(session)` — total count
- `delete_run(session, run_id)` — delete run + cascade evidence + challenges

## Frontend Changes

### New component: `HistoryList`

Props: `onRerun(idea: string)`, `onViewReport(runId: string)`, `onViewProgress(runId: string)`.  
Internal state: runs list, loading, offset, hasMore.  
Fetches `GET /runs?limit=10&offset=0` on mount. "Load more" increments offset.

### New component: `HistoryCard`

Props: `run`, `onRerun`, `onDelete`, `onClick`.  
Renders the card layout. Uses a relative-time helper. Decision badge color-coded.  
Delete: confirm dialog → DELETE request → remove from parent list.

### Modified: `App.tsx`

- On the `form` view, renders `<HistoryList>` below `<StartupForm>`.
- `onRerun` → calls `startAnalysis(idea)`.
- `onViewReport` → sets `run_id` in URL and triggers report view restore.
- `onViewProgress` → sets `run_id` in URL and triggers running view restore.

### Modified: `StartupForm`

Add optional `initialValue` prop so that when clicking "重跑", the form can be pre-filled with the previous idea. (The user can edit before submitting.)

## Error & Edge Cases

- **Empty history**: Show "暂无历史记录" placeholder.
- **Delete last item**: List updates correctly, still shows "Load more" if total > current count.
- **Concurrent delete**: If delete fails (404), remove card optimistically but log.
- **Long text overflow**: Idea text and summary use `text-overflow: ellipsis`.
- **Running run clicked**: If SSE stream has ended (run completed while on homepage), restore from backend status.

## Non-Goals

- No soft delete or undo
- No search/filter on history list
- No batch delete
