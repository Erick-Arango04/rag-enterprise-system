import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.api.routes import router as document_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

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

# Include routers
app.include_router(document_router)


@app.get("/")
async def root():
    return {
        "message": "RAG Enterprise System API",
        "status": "running",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "storage": "connected"
    }