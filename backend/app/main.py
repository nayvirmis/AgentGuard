import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update

from .api import router
from .config import get_settings
from .db import SessionLocal, create_all
from .domain import RunStatus
from .mcp_client import mcp_client
from .models import Run
from .seed import seed_demo_runs, seed_eval_cases


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    with SessionLocal() as db:
        db.execute(
            update(Run)
            .where(Run.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
            .values(status=RunStatus.INTERRUPTED)
        )
        db.commit()
    await mcp_client.start()
    seed_eval_cases()
    await seed_demo_runs()
    yield
    await mcp_client.stop()


settings = get_settings()
app = FastAPI(
    title="AgentGuard API",
    version="0.1.0",
    description="Security and observability control plane for MCP-style agents.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        {
            settings.frontend_origin,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex[:12]}")
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": type(exc).__name__,
                "message": "The request crossed a controlled failure boundary.",
            }
        },
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "mcp": mcp_client.health}


app.include_router(router)
