from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.runs import router as runs_router
from app.routes.projects import router as projects_router
from app.routes.datasets import router as datasets_router
from app.routes.metrics import router as metrics_router
from app.routes.compare import router as compare_router
from app.routes.schema import router as schema_router
from app.routes.experiments import router as experiments_router

app = FastAPI(title="BenchVault")
app.include_router(runs_router)
app.include_router(projects_router)
app.include_router(datasets_router)
app.include_router(metrics_router)
app.include_router(compare_router)
app.include_router(schema_router)
app.include_router(experiments_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
