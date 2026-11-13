"""main.py: inisialisasi FastAPI dan registrasi router."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import database
from routes import resource, transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()  # aman dipanggil tiap worker (CREATE TABLE IF NOT EXISTS)
    yield


app = FastAPI(title="API Toko Buku - UTS Komputasi Paralel", lifespan=lifespan)
app.include_router(resource.router)
app.include_router(transaction.router)
