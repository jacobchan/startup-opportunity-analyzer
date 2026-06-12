import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.storage import create_run, get_run, get_session, list_runs, delete_run
from src.storage.db import init_db
from src.web.events import EventBus
from src.web.run_registry import registry
from src.web.runner import run_deliberation

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    startup_idea: str


@router.post("")
async def create_run_endpoint(req: CreateRunRequest, background_tasks: BackgroundTasks):
    init_db()
    run = create_run(get_session(), startup_idea=req.startup_idea)
    bus = registry.create(run.run_id)
    background_tasks.add_task(_run_in_background, run.run_id, req.startup_idea, bus)
    return {"run_id": run.run_id, "status": run.status}


async def _run_in_background(run_id: str, startup_idea: str, bus: EventBus) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        run_deliberation,
        run_id,
        startup_idea,
        bus.publish,
    )


@router.get("")
async def list_runs_endpoint(limit: int = 10, offset: int = 0):
    init_db()
    session = get_session()
    runs, total = list_runs(session, limit=limit, offset=offset)
    items = []
    for run in runs:
        item = {
            "run_id": run.run_id,
            "startup_idea": run.startup_idea,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "decision": None,
            "executive_summary": None,
        }
        if run.final_report:
            item["decision"] = run.final_report.get("decision")
            item["executive_summary"] = run.final_report.get("executive_summary")
        items.append(item)
    return {"runs": items, "total": total}


@router.delete("/{run_id}")
async def delete_run_endpoint(run_id: str):
    init_db()
    if delete_run(get_session(), run_id):
        return Response(status_code=204)
    raise HTTPException(status_code=404, detail="run not found")


@router.get("/{run_id}")
async def get_run_endpoint(run_id: str):
    run = get_run(get_session(), run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run.run_id,
        "startup_idea": run.startup_idea,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "round1_outputs": run.round1_outputs,
    }


@router.get("/{run_id}/report")
async def get_report_endpoint(run_id: str):
    run = get_run(get_session(), run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status != "complete":
        raise HTTPException(status_code=409, detail=f"run is {run.status}, not complete")
    if run.final_report is None:
        raise HTTPException(status_code=500, detail="run complete but no report")
    return run.final_report
