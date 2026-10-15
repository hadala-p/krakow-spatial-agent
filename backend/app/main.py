from fastapi import FastAPI

from app.api.v1.transit import router as transit_router

app = FastAPI(
    title="Krakow Spatial Agent API",
    version="1.0.0",
    description="Asynchronous Geo-AI and Public Transit API for Krakow",
)

app.include_router(transit_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
