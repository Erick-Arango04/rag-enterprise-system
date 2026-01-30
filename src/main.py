from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.api.routes import router as document_router
from src.api.exception_handlers import register_exception_handlers
from src.middleware import HTTPLoggingMiddleware
from src.utils.logging import configure_logging, get_logger

# Configure structured JSON logging
configure_logging(log_level="INFO")
logger = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title="RAG Enterprise System",
    description="Sistema RAG con PostgreSQL + pgvector + MinIO + Claude",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Logging (AOP-style)
app.add_middleware(HTTPLoggingMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(document_router)
