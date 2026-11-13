"""routes/transaction.py: transaksi + background task + pengaman konkurensi (Lock)."""
import asyncio
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

import database as db
from models import TransactionAccepted, TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Saklar untuk pengujian B3:  USE_LOCK=0 -> Tahap 1 (tanpa lock), USE_LOCK=1 -> Tahap 2 (dengan lock)
USE_LOCK = os.getenv("USE_LOCK", "1") == "1"

# asyncio.Lock di tingkat modul: dipakai bersama oleh semua coroutine dalam SATU proses.
# Catatan: lock ini tidak dibagi antar worker Uvicorn (tiap worker = proses berbeda).
stok_lock = asyncio.Lock()


async def potong_stok_tanpa_lock(item_id: int, qty: int) -> bool:
    """VERSI 1 (rawan race condition): baca -> jeda -> tulis tanpa perlindungan."""
    stok_terkini = await db.get_stok(item_id)
    # Jeda buatan: coroutine lain bisa menyela di sini dan membaca stok yang SAMA
    await asyncio.sleep(0.01)
    if stok_terkini < qty:
        return False
    await db.decrement_stok(item_id, qty)
    return True


async def potong_stok_dengan_lock(item_id: int, qty: int) -> bool:
    """VERSI 2 (aman): critical section dilindungi asyncio.Lock."""
    async with stok_lock:  # hanya satu coroutine yang boleh masuk pada satu waktu
        stok_terkini = await db.get_stok(item_id)
        await asyncio.sleep(0.01)
        if stok_terkini < qty:
            return False
        # Guard atomik di SQL = lapis kedua (melindungi juga saat multi-worker)
        return await db.decrement_stok_aman(item_id, qty)


async def potong_stok(item_id: int, qty: int) -> bool:
    return await (potong_stok_dengan_lock if USE_LOCK else potong_stok_tanpa_lock)(item_id, qty)


async def proses_transaksi_background(trx_id: int, item_id: int, qty: int):
    """Fungsi pekerja internal (BUKAN endpoint HTTP). Dijalankan FastAPI setelah respon terkirim."""
    try:
        await db.update_trx_status(trx_id, "processing")
        await asyncio.sleep(3)  # simulasi pekerjaan I/O (mis. pembayaran / pengemasan)
        await db.update_trx_status(trx_id, "completed")
    except Exception as exc:  # jika gagal: tandai failed & kembalikan stok
        await db.update_trx_status(trx_id, "failed", str(exc))
        await db.kembalikan_stok(item_id, qty)


@router.post("", response_model=TransactionAccepted, status_code=status.HTTP_202_ACCEPTED)
async def buat_transaksi(data: TransactionCreate, bg: BackgroundTasks):
    book = await db.get_book(data.item_id)
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak terdaftar")

    # Pemotongan stok dilakukan sinkron terhadap request agar penolakan 409 langsung terlihat
    if not await potong_stok(data.item_id, data.qty):
        raise HTTPException(status_code=409, detail="Stok habis / tidak mencukupi")

    trx_id = await db.insert_transaction(data.item_id, data.qty, book["harga"] * data.qty, "pending")
    # Pemrosesan lanjutan dijadwalkan di latar belakang; respon langsung dikembalikan
    bg.add_task(proses_transaksi_background, trx_id, data.item_id, data.qty)
    return {"id": trx_id, "status": "pending", "message": "Transaksi diproses"}


@router.get("", response_model=list[TransactionOut])
async def daftar_transaksi(
    status: Optional[str] = Query(None, pattern="^(pending|processing|completed|failed)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return await db.list_transactions(status, skip, limit)


@router.get("/{trx_id}", response_model=TransactionOut)
async def detail_transaksi(trx_id: int):
    trx = await db.get_transaction(trx_id)
    if not trx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return trx
