import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import get_settings
from app.database import engine, Base, get_db
from app.cache import get_redis, cache_get, cache_set, cache_delete
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating database tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Startup complete")
    yield
    logger.info("Shutting down")
    await engine.dispose()


app = FastAPI(
    title="Task Manager API",
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(STATIC_DIR / "index.html")


# ── Health Check ────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    cache_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        db_status = "unreachable"

    try:
        r = await get_redis()
        await r.ping()
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        cache_status = "unreachable"

    overall = "healthy" if db_status == "ok" and cache_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        database=db_status,
        cache=cache_status,
        version=APP_VERSION,
    )


# ── Tasks ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/tasks", response_model=list[TaskResponse], tags=["tasks"])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("tasks:all")
    if cached:
        logger.info("Cache hit: tasks:all")
        return cached

    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = result.scalars().all()
    data = [TaskResponse.model_validate(t).model_dump(mode="json") for t in tasks]
    await cache_set("tasks:all", data)
    return data


@app.post(
    "/api/v1/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await cache_delete("tasks:all")
    logger.info("Created task id=%s", task.id)
    return task


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    cached = await cache_get(f"task:{task_id}")
    if cached:
        return cached

    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    data = TaskResponse.model_validate(task).model_dump(mode="json")
    await cache_set(f"task:{task_id}", data)
    return data


@app.put("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def update_task(
    task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    await cache_delete(f"task:{task_id}")
    await cache_delete("tasks:all")
    logger.info("Updated task id=%s", task_id)
    return task


@app.delete(
    "/api/v1/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    await cache_delete(f"task:{task_id}")
    await cache_delete("tasks:all")
    logger.info("Deleted task id=%s", task_id)
