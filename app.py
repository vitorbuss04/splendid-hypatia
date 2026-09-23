import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.routes import auth_routes, printer_routes, filament_routes, project_routes
from backend.config import APP_ENV

# Initialize tables
init_db()

app = FastAPI(
    title="3D Print Cost Calculator & Quoting Engine",
    description="Calculadora Profissional e Sistema de Orçamentos para Impressão 3D",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(printer_routes.router)
app.include_router(filament_routes.router)
app.include_router(project_routes.router)

# Healthcheck
@app.get("/api/health", tags=["Sistema"])
def health_check():
    return {
        "status": "healthy",
        "environment": APP_ENV,
        "version": "1.0.0",
    }

# Serve frontend static assets
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/preview")
    def serve_preview():
        return FileResponse(str(FRONTEND_DIR / "preview.html"))

    @app.get("/{catchall:path}")
    def serve_spa(catchall: str):
        # Do not catch API routes
        if catchall == "api" or catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="Endpoint não encontrado.")
        # If file exists in frontend, serve it safely
        target_path = (FRONTEND_DIR / catchall).resolve()
        if target_path.is_file() and target_path.is_relative_to(FRONTEND_DIR.resolve()):
            return FileResponse(str(target_path))
        # Otherwise fallback to index.html for SPA routing
        return FileResponse(str(FRONTEND_DIR / "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
