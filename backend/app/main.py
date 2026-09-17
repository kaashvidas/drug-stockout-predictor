from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import auth_router, alerts_router, facilities_router, cascade_router, redistribution_router, reports_router

app = FastAPI(
    title="Shortage Cascade API",
    description="Prediction and redistribution-recommendation layer for medicine stockouts. "
                 "See docs/build_guide.md and docs/DATA_SOURCES.md in the repo root.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router.router)
app.include_router(alerts_router.router)
app.include_router(facilities_router.router)
app.include_router(cascade_router.router)
app.include_router(redistribution_router.router)
app.include_router(reports_router.router)
