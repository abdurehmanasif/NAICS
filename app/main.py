from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .api.scoring import router as scoring_router
from .api.generation import router as generation_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
TITLE = "RFP Processing API"
DESCRIPTION = (
    "A FastAPI application for scoring proposals and generating RFP responses using AI"
)
VERSION = "1.0.0"

# Create FastAPI application
app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(scoring_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint providing basic API information."""
    return {
        "message": TITLE,
        "version": VERSION,
        "docs": "/docs",
        "endpoints": {
            "scoring": "/api/v1/scoring/score-proposal",
            "generation": "/api/v1/generation/generate-proposal",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": TITLE}
