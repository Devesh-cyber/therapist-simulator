import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import auth, game, patients, sessions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
settings = get_settings()



@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logging.getLogger("app").info("LLM mode: %s", settings.effective_llm_mode)
    yield


app = FastAPI(title="Therapist Simulator API", version="1.0.0", lifespan=lifespan)

origins = [o.strip().rstrip("/") for o in settings.frontend_url.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel preview deployments
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "llm_mode": settings.effective_llm_mode, "model": settings.grok_model}


for r in (auth.router, patients.router, sessions.router, game.router):
    app.include_router(r)
