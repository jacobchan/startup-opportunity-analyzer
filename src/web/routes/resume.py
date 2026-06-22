"""POST /runs/{id}/resume - continue a paused or failed deliberation."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.storage import get_run, get_session
from src.web.run_registry import registry
from src.web.events import EventBus
from src.web.runner import resume_deliberation


router = APIRouter(prefix="/runs", tags=["resume"])
TERMINAL_BUS_GRACE_SECONDS = 30


@router.post("/{run_id}/resume")
async def resume_run_endpoint(run_id: str, background_tasks: BackgroundTasks):
    run = get_run(get_session(), run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status == "complete":
        raise HTTPException(status_code=409, detail="run is already complete")
    if run.status == "running":
        raise HTTPException(status_code=409, detail="run is already running")

    # Reuse the same EventBus pattern as the create-run flow: create a
    # fresh bus for this resume attempt, then start a background task.
    # If the resume fails, the bus's last event will be run.failed.
    bus = registry.create(run_id)
    background_tasks.add_task(_resume_in_background, run_id, bus)
    return {"run_id": run_id, "status": "resuming"}


async def _resume_in_background(run_id: str, bus: EventBus) -> None:
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            resume_deliberation,
            run_id,
            bus.publish,
        )
    finally:
        loop.call_later(TERMINAL_BUS_GRACE_SECONDS, registry.release, run_id)
