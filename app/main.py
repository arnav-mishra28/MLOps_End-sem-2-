from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.viva import router as viva_router
from app.services.llm_service import llm_service

app = FastAPI(
    title=settings.APP_NAME,
    description="Interactive Generative AI-powered Technical Viva Examination System using FastAPI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount API routes
app.include_router(viva_router)


@app.get("/", include_in_schema=False)
def serve_index():
    """Serves the interactive web UI for conducting viva examinations."""
    return FileResponse(static_dir / "index.html")


@app.get("/health", tags=["Health"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "llm_mode": "live_gemini" if llm_service.is_live_llm_available else "intelligent_offline",
        "gemini_model": settings.GEMINI_MODEL,
        "total_questions_per_viva": settings.TOTAL_QUESTIONS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
