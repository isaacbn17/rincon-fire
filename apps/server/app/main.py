from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.db.bootstrap import init_db


settings = get_settings()


def _configure_logging() -> None:
    level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger().setLevel(level)


_configure_logging()

app = FastAPI(title="Rincon Fire API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db(reset_db=settings.reset_db_on_start)


app.include_router(api_router)
