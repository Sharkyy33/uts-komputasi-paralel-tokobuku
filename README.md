Video presentasi: https://youtu.be/GANTI_DENGAN_LINK_UNLISTED_KAMU

# API Toko Buku (UTS Komputasi Paralel dan Terdistribusi)

Nama: ... | NIM: ...

REST API toko buku: FastAPI + SQLite (aiosqlite), transaksi asinkron via BackgroundTasks, dan pengaman race condition dengan asyncio.Lock.

## Instalasi
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py            # isi 12 buku awal (python seed.py --reset untuk ulang)
```

## Menjalankan
```bash
uvicorn main:app --port 8000                 # 1 worker
uvicorn main:app --port 8000 --workers 4     # 4 worker
```
Swagger UI: http://127.0.0.1:8000/docs

## Uji race condition (B3)
```bash
# Tahap 1: tanpa lock  -> kedua request 202, stok akhir -1
USE_LOCK=0 uvicorn main:app --port 8000      # Windows PowerShell: $env:USE_LOCK="0"; uvicorn ...
python test_race.py
# Tahap 2: dengan lock -> satu 202, satu 409 Conflict, stok akhir 0
USE_LOCK=1 uvicorn main:app --port 8000
python test_race.py
```
`test_race.py` membuat buku baru dengan stok 1 setiap dijalankan, jadi tidak perlu reset manual.

## Uji beban (C1)
Jalankan server (1 lalu 4 worker), lalu di terminal lain:
```bash
SCENARIO=read  TOTAL_REQUESTS=100 locust -f locustfile.py --headless -u 20 -r 20 --csv hasil_read_1w
SCENARIO=write TOTAL_REQUESTS=50  locust -f locustfile.py --headless -u 10 -r 10 --csv hasil_write_1w
```
Ulangi dengan server 4 worker (ganti nama csv). Ambil Total Waktu, Throughput (Requests/s), dan Average Response Time dari output / file csv.

## Endpoint
| Method | Path | Keterangan |
|---|---|---|
| GET | /books?skip=0&limit=10 | Daftar buku |
| GET | /books/{id} | Detail buku |
| POST | /books | Tambah buku (201) |
| PUT | /books/{id} | Perbarui buku |
| DELETE | /books/{id} | Hapus permanen (hard delete) |
| POST | /transactions | Buat transaksi, respon 202 `pending`; 404 buku tak ada; 409 stok habis |
| GET | /transactions?status=pending | Daftar transaksi + filter status |
| GET | /transactions/{id} | Detail & status terkini |

Catatan: `asyncio.Lock` hanya berlaku di dalam satu proses. Pada multi-worker, pengurangan stok versi lock juga memakai `UPDATE ... WHERE stok >= qty` sebagai lapis kedua.

## Referensi
FastAPI, Python asyncio, aiosqlite, Uvicorn, Locust (dokumentasi resmi) + tambahkan referensi lain yang kamu pakai.
