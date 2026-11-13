"""database.py: koneksi aiosqlite + seluruh operasi basis data (async / non-blocking)."""
import os
from contextlib import asynccontextmanager

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "tokobuku.db")

# Catatan: kolom stok SENGAJA tanpa CHECK(stok >= 0) agar overselling pada
# Tahap 1 B3 (tanpa lock) bisa terlihat sebagai stok negatif. Validasi stok
# dilakukan di lapisan aplikasi (lihat routes/transaction.py).
CREATE_BOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS books (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    judul    TEXT NOT NULL,
    penulis  TEXT NOT NULL,
    kategori TEXT NOT NULL,
    harga    REAL NOT NULL,
    stok     INTEGER NOT NULL          -- kolom kuantitas wajib
);
"""

CREATE_TRX_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL,
    qty         INTEGER NOT NULL,
    total_harga REAL NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    catatan     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@asynccontextmanager
async def koneksi():
    """Satu koneksi per operasi: aman dipakai banyak coroutine / banyak worker."""
    async with aiosqlite.connect(DB_PATH, timeout=30) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA busy_timeout = 30000")
        yield db


async def init_db():
    async with koneksi() as db:
        await db.execute("PRAGMA journal_mode = WAL")  # baca/tulis lebih lancar antar worker
        await db.execute(CREATE_BOOKS_TABLE)
        await db.execute(CREATE_TRX_TABLE)
        await db.commit()


# ---------------------------- CRUD books ----------------------------
async def list_books(skip: int, limit: int):
    async with koneksi() as db:
        cur = await db.execute("SELECT * FROM books ORDER BY id LIMIT ? OFFSET ?", (limit, skip))
        return [dict(r) for r in await cur.fetchall()]


async def get_book(book_id: int):
    async with koneksi() as db:
        cur = await db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def insert_book(d: dict) -> int:
    async with koneksi() as db:
        cur = await db.execute(
            "INSERT INTO books (judul, penulis, kategori, harga, stok) VALUES (?,?,?,?,?)",
            (d["judul"], d["penulis"], d["kategori"], d["harga"], d["stok"]),
        )
        await db.commit()
        return cur.lastrowid


async def update_book(book_id: int, d: dict) -> bool:
    async with koneksi() as db:
        cur = await db.execute(
            "UPDATE books SET judul=?, penulis=?, kategori=?, harga=?, stok=? WHERE id=?",
            (d["judul"], d["penulis"], d["kategori"], d["harga"], d["stok"], book_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_book(book_id: int) -> bool:
    """Hard delete: baris benar-benar dihapus dari tabel."""
    async with koneksi() as db:
        cur = await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        await db.commit()
        return cur.rowcount > 0


# ---------------------------- Stok ----------------------------
async def get_stok(book_id: int) -> int:
    async with koneksi() as db:
        cur = await db.execute("SELECT stok FROM books WHERE id = ?", (book_id,))
        row = await cur.fetchone()
        return row["stok"] if row else 0


async def decrement_stok(book_id: int, qty: int) -> None:
    """Pengurangan polos (dipakai versi TANPA lock)."""
    async with koneksi() as db:
        await db.execute("UPDATE books SET stok = stok - ? WHERE id = ?", (qty, book_id))
        await db.commit()


async def decrement_stok_aman(book_id: int, qty: int) -> bool:
    """Pengurangan dengan guard atomik di SQL (dipakai versi DENGAN lock).
    Berguna sebagai lapis kedua karena asyncio.Lock hanya berlaku per proses."""
    async with koneksi() as db:
        cur = await db.execute(
            "UPDATE books SET stok = stok - ? WHERE id = ? AND stok >= ?", (qty, book_id, qty)
        )
        await db.commit()
        return cur.rowcount > 0


async def kembalikan_stok(book_id: int, qty: int) -> None:
    async with koneksi() as db:
        await db.execute("UPDATE books SET stok = stok + ? WHERE id = ?", (qty, book_id))
        await db.commit()


# ---------------------------- Transaksi ----------------------------
async def insert_transaction(item_id: int, qty: int, total: float, status: str = "pending") -> int:
    async with koneksi() as db:
        cur = await db.execute(
            "INSERT INTO transactions (item_id, qty, total_harga, status) VALUES (?,?,?,?)",
            (item_id, qty, total, status),
        )
        await db.commit()
        return cur.lastrowid


async def update_trx_status(trx_id: int, status: str, catatan: str | None = None) -> None:
    async with koneksi() as db:
        await db.execute(
            "UPDATE transactions SET status=?, catatan=COALESCE(?, catatan) WHERE id=?",
            (status, catatan, trx_id),
        )
        await db.commit()


async def get_transaction(trx_id: int):
    async with koneksi() as db:
        cur = await db.execute("SELECT * FROM transactions WHERE id = ?", (trx_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_transactions(status: str | None, skip: int, limit: int):
    async with koneksi() as db:
        if status:
            cur = await db.execute(
                "SELECT * FROM transactions WHERE status=? ORDER BY id LIMIT ? OFFSET ?",
                (status, limit, skip),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM transactions ORDER BY id LIMIT ? OFFSET ?", (limit, skip)
            )
        return [dict(r) for r in await cur.fetchall()]
