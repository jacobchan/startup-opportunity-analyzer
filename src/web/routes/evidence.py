from fastapi import APIRouter, HTTPException

from src.storage import get_evidence, get_session

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{evidence_id}")
async def get_evidence_endpoint(evidence_id: str):
    ev = get_evidence(get_session(), evidence_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return {
        "evidence_id": ev.evidence_id,
        "source_type": ev.source_type,
        "query": ev.query,
        "url": ev.url,
        "title": ev.title,
        "content_excerpt": ev.content_excerpt,
        "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
    }
