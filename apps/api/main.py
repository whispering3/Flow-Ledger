from fastapi import FastAPI

from apps.api.routes.auth import router as auth_router
from apps.api.routes.destinations import router as destinations_router
from apps.api.routes.events import router as events_router
from apps.api.routes.executions import router as executions_router

app = FastAPI(
    title="FlowLedger API",
    version="0.1.0",
    description="Reliable webhook delivery and execution monitoring.",
)
app.include_router(events_router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(destinations_router, prefix="/v1")
app.include_router(executions_router, prefix="/v1")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}
