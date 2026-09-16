from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.routers import dashboard, exercises, plans, reference, users, workouts


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(reference.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(exercises.router, prefix="/api")
    app.include_router(plans.router, prefix="/api")
    app.include_router(workouts.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")

    frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if frontend_dist.is_dir():
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str) -> FileResponse:
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found")
            requested_file = (frontend_dist / full_path).resolve()
            if (
                full_path
                and requested_file.is_relative_to(frontend_dist.resolve())
                and requested_file.is_file()
            ):
                return FileResponse(requested_file)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
