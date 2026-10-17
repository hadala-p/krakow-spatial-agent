from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.transit import router as transit_router
from app.core.database import check_db_health

app = FastAPI(
    title="Krakow Spatial Agent API",
    version="1.0.0",
    description="Asynchronous Geo-AI and Public Transit API for Krakow",
)

app.include_router(transit_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    if await check_db_health():
        return JSONResponse(status_code=200, content={"status": "healthy"})
    return JSONResponse(status_code=503, content={"status": "unhealthy"})
