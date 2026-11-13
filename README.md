Video presentasi: https://youtu.be/GANTI_DENGAN_LINK_YOUTUBE_UNLISTED

# API Toko Buku (UTS Komputasi Paralel dan Terdistribusi)

- Nama: Abang Malik Syaidar
- NIM: 231220010
- Kelas: 31
- Dosen: Yulrio Brianorman, S.Si., M.T.

REST API toko buku berbasis **FastAPI** dengan penyimpanan **SQLite (aiosqlite)**. Fitur utama: CRUD buku, transaksi yang diproses di latar belakang (`BackgroundTasks`), dan pencegahan race condition pada pengurangan stok dengan `asyncio.Lock`. Laporan lengkap ada di `docs/laporan_uts.pdf`.

## Prasyarat

- Python 3.10 atau lebih baru (diuji pada Python 3.13)
- Windows PowerShell (perintah di bawah ditulis untuk PowerShell)

> Catatan: pada Python yang terlalu baru (misalnya 3.15), beberapa pustaka belum punya paket siap pakai dan gagal dipasang. Gunakan Python 3.12 atau 3.13.

## Instalasi

Jalankan di folder proyek:

```powershell
# 1. Izinkan skrip untuk sesi terminal ini saja (agar venv bisa diaktifkan)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 2. Buat dan aktifkan virtual environment
py -3.13 -m venv venv
venv\Scripts\activate

# 3. Pasang dependensi
pip install -r requirements.txt

# 4. Isi data awal (12 buku, stok awal 500 per buku)
python seed.py
```

Untuk mengisi ulang data dari awal: `python seed.py --reset` (jalankan saat server mati).

## Menjalankan server

```powershell
uvicorn main:app --port 8000
```

Dokumentasi interaktif (Swagger UI): http://127.0.0.1:8000/docs

Berkas database `tokobuku.db` dibuat otomatis saat server pertama kali jalan.

Untuk 1 atau 4 worker (dipakai saat benchmark):

```powershell
uvicorn main:app --port 8000 --workers 1
uvicorn main:app --port 8000 --workers 4
```

> Pada Windows, `--workers 4` kadang mencetak `OSError: [WinError 10022]` saat start dan satu proses anak diganti otomatis oleh Uvicorn. Pastikan log menampilkan 4 baris `Started server process` sebelum menjalankan Locust.

## Pengujian race condition (B3)

Jalankan server dan skrip uji di **dua terminal terpisah** (aktifkan `venv` di keduanya).

**Tahap 1: tanpa lock (harus terjadi overselling)**

Terminal 1:
```powershell
$env:USE_LOCK="0"
uvicorn main:app --port 8000
```
Terminal 2:
```powershell
python test_race.py
```
Hasil yang diharapkan: kedua request `202` dan `Stok akhir: -1`.

**Tahap 2: dengan lock (satu ditolak 409)**

Terminal 1 (hentikan server dengan `Ctrl+C`, lalu):
```powershell
$env:USE_LOCK="1"
uvicorn main:app --port 8000
```
Terminal 2:
```powershell
python test_race.py
```
Hasil yang diharapkan: satu request `202`, satu request `409` (`Stok habis / tidak mencukupi`), dan `Stok akhir: 0`.

`test_race.py` membuat buku baru dengan stok 1 setiap dijalankan, jadi tidak perlu mengatur stok secara manual. Variabel `$env:USE_LOCK` hanya berlaku di terminal tempat variabel itu diketik; bila tidak diatur, nilai bawaannya adalah lock aktif (`1`).

## Uji beban dengan Locust (C1)

Jalankan server lebih dulu (1 worker, lalu 4 worker), kemudian di terminal lain:

**Skenario Read** (`GET /books`, 100 request, konkurensi 20):
```powershell
$env:SCENARIO="read"; $env:TOTAL_REQUESTS="100"
locust -f locustfile.py --headless -u 20 -r 20
```

**Skenario Write** (`POST /transactions`, 50 request, konkurensi 10):
```powershell
$env:SCENARIO="write"; $env:TOTAL_REQUESTS="50"
locust -f locustfile.py --headless -u 10 -r 10
```

Locust berhenti sendiri setelah semua request selesai dan mencetak baris `=== RINGKASAN ... ===` (jumlah request, total waktu, throughput) di bagian paling bawah, di samping tabel statistik Locust (termasuk rata-rata latensi).

Hasil benchmark (median dari 3 kali pengujian per kombinasi):

| Skenario | Worker | Total Waktu | Throughput | Rata-rata Latensi |
|---|---|---|---|---|
| GET /books | 1 | 0,23 s | 442,23 req/s | 38 ms |
| GET /books | 4 | 0,17 s | 573,83 req/s | 27 ms |
| POST /transactions | 1 | 2,26 s | 22,10 req/s | 417 ms |
| POST /transactions | 4 | 1,58 s | 31,64 req/s | 284 ms |

Analisis lengkap ada di `docs/laporan_uts.pdf`.

## Daftar endpoint

| Method | Path | Keterangan |
|---|---|---|
| GET | `/books?skip=0&limit=10` | Daftar buku dengan paginasi |
| GET | `/books/{id}` | Detail buku (404 bila tidak ada) |
| POST | `/books` | Tambah buku (201 Created; 422 bila tidak valid) |
| PUT | `/books/{id}` | Perbarui buku dan kembalikan data terbaru |
| DELETE | `/books/{id}` | Hapus permanen (hard delete) |
| POST | `/transactions` | Buat transaksi; respons `202` berstatus `pending`; 404 bila buku tidak terdaftar; 409 bila stok habis |
| GET | `/transactions?status=pending` | Daftar transaksi, dapat difilter status |
| GET | `/transactions/{id}` | Detail transaksi beserta status terkini |

Alur status transaksi: `pending` → `processing` → `completed` (atau `failed`). Perubahan status dilakukan oleh fungsi pekerja internal `proses_transaksi_background`, dengan simulasi proses `await asyncio.sleep(3)`.

## Struktur proyek

```
.
├── main.py              # Inisialisasi FastAPI dan registrasi router
├── database.py          # Koneksi aiosqlite, skema tabel, operasi basis data
├── models.py            # Skema Pydantic (request dan response)
├── routes/
│   ├── resource.py      # Endpoint CRUD buku
│   └── transaction.py   # Endpoint transaksi, BackgroundTasks, asyncio.Lock
├── seed.py              # Data awal (12 buku)
├── test_race.py         # Pengujian race condition
├── locustfile.py        # Skenario uji beban Locust
├── requirements.txt     # Daftar dependensi
└── docs/
    └── laporan_uts.pdf  # Laporan hasil pengujian dan analisis
```

## Catatan teknis

- `asyncio.Lock` (`stok_lock`) hanya melindungi di dalam **satu proses**. Pada multi-worker, setiap worker memiliki lock sendiri, sehingga pengurangan stok pada versi dengan lock juga memakai guard SQL `UPDATE ... WHERE stok >= qty` sebagai lapis kedua.
- Kolom `stok` sengaja tidak memakai `CHECK (stok >= 0)` agar overselling pada Tahap 1 (tanpa lock) dapat diperlihatkan sebagai stok negatif; validasi stok dilakukan di lapisan aplikasi.
- Pembayaran dan pengiriman hanya disimulasikan; belum ada autentikasi.

## Referensi

- FastAPI: https://fastapi.tiangolo.com
- Python asyncio: https://docs.python.org/3/library/asyncio.html
- aiosqlite: https://aiosqlite.omnilib.dev
- Uvicorn: https://www.uvicorn.org
- Locust: https://locust.io
