import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from app.api.v1.live import router as live_router
from app.api.v1.transit import router as transit_router
from app.core.database import check_db_health
from app.services.live_feed_service import live_feed_service

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    refresh_task = asyncio.create_task(live_feed_service.run_refresh_loop())
    try:
        yield
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Krakow Spatial Agent API",
    version="1.0.0",
    description="Asynchronous Geo-AI and Public Transit API for Krakow",
    lifespan=lifespan,
)

app.include_router(transit_router, prefix="/api/v1")
app.include_router(live_router, prefix="/api/v1")


@app.middleware("http")
async def measure_request_time(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        logger.exception(
            "HTTP %s %s failed after %.2f ms",
            request.method,
            endpoint,
            elapsed_ms,
        )
        raise

    elapsed_ms = (perf_counter() - started_at) * 1000
    route = request.scope.get("route")
    endpoint = getattr(route, "path", request.url.path)
    response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"
    logger.info(
        "HTTP %s %s -> %s in %.2f ms",
        request.method,
        endpoint,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    if await check_db_health():
        return JSONResponse(status_code=200, content={"status": "healthy"})
    return JSONResponse(status_code=503, content={"status": "unhealthy"})
