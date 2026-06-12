from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.web.routes import runs, stream, evidence


def create_app() -> FastAPI:
    app = FastAPI(title="Startup Opportunity Analyzer", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(evidence.router)

    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
