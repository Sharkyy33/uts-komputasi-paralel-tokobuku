"""seed.py: mengisi 12 data buku awal.  Pakai:  python seed.py [--reset]"""
import asyncio
import sys

import database as db

BUKU = [
    ("Laskar Pelangi", "Andrea Hirata", "Novel", 89000),
    ("Bumi Manusia", "Pramoedya Ananta Toer", "Novel", 110000),
    ("Filosofi Teras", "Henry Manampiring", "Filsafat", 98000),
    ("Atomic Habits", "James Clear", "Pengembangan Diri", 120000),
    ("Clean Code", "Robert C. Martin", "Teknologi", 450000),
    ("Fluent Python", "Luciano Ramalho", "Teknologi", 520000),
    ("Sapiens", "Yuval Noah Harari", "Sejarah", 135000),
    ("Negeri 5 Menara", "Ahmad Fuadi", "Novel", 85000),
    ("Dilan 1990", "Pidi Baiq", "Novel", 79000),
    ("Rich Dad Poor Dad", "Robert Kiyosaki", "Bisnis", 95000),
    ("Pemrograman Python Dasar", "Penulis Lokal", "Teknologi", 150000),
    ("Cantik Itu Luka", "Eka Kurniawan", "Novel", 105000),
]


async def main():
    await db.init_db()
    if "--reset" in sys.argv:
        async with db.koneksi() as c:
            await c.execute("DELETE FROM transactions")
            await c.execute("DELETE FROM books")
            await c.execute("DELETE FROM sqlite_sequence")
            await c.commit()
    if await db.list_books(0, 1):
        print("Data sudah ada. Pakai --reset untuk mengisi ulang.")
        return
    for judul, penulis, kategori, harga in BUKU:
        await db.insert_book(dict(judul=judul, penulis=penulis, kategori=kategori, harga=harga, stok=500))
    print(f"{len(BUKU)} buku berhasil ditambahkan (stok awal 500 tiap buku).")


if __name__ == "__main__":
    asyncio.run(main())
