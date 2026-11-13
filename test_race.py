"""test_race.py: kirim 2 request transaksi serentak untuk buku berstok 1."""
import asyncio
import os

import httpx

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")


async def main():
    async with httpx.AsyncClient(base_url=BASE) as client:
        # Siapkan buku khusus dengan stok = 1
        r = await client.post("/books", json={
            "judul": "Buku Uji Race", "penulis": "Tester", "kategori": "Uji",
            "harga": 10000, "stok": 1})
        item_id = r.json()["id"]
        payload = {"item_id": item_id, "qty": 1}

        # Dua request dikirim serentak
        res1, res2 = await asyncio.gather(
            client.post("/transactions", json=payload),
            client.post("/transactions", json=payload),
        )
        print("Respon Request 1:", res1.status_code, res1.json())
        print("Respon Request 2:", res2.status_code, res2.json())

        akhir = (await client.get(f"/books/{item_id}")).json()
        print("Stok akhir:", akhir["stok"])


if __name__ == "__main__":
    asyncio.run(main())
