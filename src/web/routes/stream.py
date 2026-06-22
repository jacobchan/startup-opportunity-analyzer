import json
import uuid

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from src.web.run_registry import registry

router = APIRouter(prefix="/runs", tags=["stream"])


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    bus = registry.get(run_id)
    if bus is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_generator():
        terminal_seen = False
        try:
            async for event in bus.subscribe():
                yield (
                    f"id: {uuid.uuid4().hex}\n"
                    f"event: {event.get('type', 'message')}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
                if event.get("type") in ("run.complete", "run.failed"):
                    terminal_seen = True
                    break
        except GeneratorExit:
            # Client disconnected before the terminal event arrived.
            pass
        finally:
            # Only a terminal event may retire the lookup. A plain disconnect
            # is normally a refresh, and the new page must reconnect.
            if terminal_seen:
                registry.release(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
