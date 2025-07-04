# app/main.py
import logging
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rear-differential")

# Create the FastAPI app
app = FastAPI(
    title="Rear Differential API",
    description="API for the rear-differential service",
    version="0.1.0",
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, in production you should restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a root router with the prefix
root_router = APIRouter(prefix="/rear-diff")

# OpenAPI JSON endpoint
@root_router.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

# Health check endpoint
@root_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Root endpoint
@root_router.get("/", tags=["root"])
async def root():
    """API root endpoint."""
    return {
        "message": "Welcome to Rear Differential API",
        "docs": "/docs",
        "health": "/health"
    }

# Mount docs at the prefixed path
@root_router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/rear-diff/openapi.json",
        title=app.title + " - Swagger UI"
    )

@root_router.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url="/rear-diff/openapi.json",
        title=app.title + " - ReDoc"
    )

# Add exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

# Include the root router in the app
app.include_router(root_router)

# Import routers
from app.routers import training, media

# Include routers
app.include_router(training.get_router(), prefix="/rear-diff/training", tags=["training"])
app.include_router(media.get_router(), prefix="/rear-diff/media", tags=["media"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )