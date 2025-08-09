# File: /app/main.py | Version: 1.5 | Path: /app/main.py
from fastapi import FastAPI, Depends

from app.routers import auth, core_entities, task, tags  # <- add tags
from app.security import get_current_user
from app.models import User

app = FastAPI(title="Task Manager API")

@app.get("/")
def read_root():
    return {"status": "ok"}

# Root-level protected endpoint (tests expect /protected)
@app.get("/protected")
def protected(current_user: User = Depends(get_current_user)):
    return {"ok": True, "user": {"id": current_user.id, "email": current_user.email}}

# Routers
app.include_router(auth.router)
app.include_router(core_entities.router)
app.include_router(task.router)
app.include_router(tags.router)  # <- mount tags
