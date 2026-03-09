from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.runs import router as runs_router

app = FastAPI(title="BenchVault")
app.include_router(runs_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
