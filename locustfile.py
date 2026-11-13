"""locustfile.py: skenario beban. Berhenti otomatis setelah TOTAL_REQUESTS request SELESAI.

  Read : SCENARIO=read  TOTAL_REQUESTS=100 locust -f locustfile.py --headless -u 20 -r 20
  Write: SCENARIO=write TOTAL_REQUESTS=50  locust -f locustfile.py --headless -u 10 -r 10
Ringkasan (jumlah request, total waktu, throughput) dicetak di baris terakhir.
"""
import os
import random
import time

import gevent
from locust import HttpUser, constant, events, task

SCENARIO = os.getenv("SCENARIO", "read")
TOTAL = int(os.getenv("TOTAL_REQUESTS", "100"))

_terkirim = 0   # request yang sudah dikirim
_selesai = 0    # request yang sudah menerima respon
_mulai = None   # waktu request pertama dikirim
_akhir = None   # waktu respon terakhir diterima


class PembeliBuku(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = constant(0)

    @task
    def jalankan(self):
        global _terkirim, _selesai, _mulai, _akhir
        if _terkirim >= TOTAL:      # kuota terkirim: jangan kirim lagi, tunggu yang lain selesai
            gevent.sleep(0.01)
            return
        _terkirim += 1
        if _mulai is None:
            _mulai = time.perf_counter()
        if SCENARIO == "read":
            self.client.get("/books?skip=0&limit=10", name="GET /books")
        else:
            self.client.post("/transactions", name="POST /transactions",
                             json={"item_id": random.randint(1, 12), "qty": 1})
        _selesai += 1
        _akhir = time.perf_counter()


@events.test_start.add_listener
def _pantau(environment, **kwargs):
    """Hentikan tes hanya setelah SEMUA request benar-benar selesai (tidak ada yang terpotong)."""
    def loop():
        while _selesai < TOTAL:
            gevent.sleep(0.01)
        environment.runner.quit()
    gevent.spawn(loop)


@events.quitting.add_listener
def _ringkasan(environment, **kwargs):
    if _mulai and _akhir and _akhir > _mulai:
        total = _akhir - _mulai
        print(f"\n=== RINGKASAN {SCENARIO}: {_selesai} request | total waktu {total:.2f} s | "
              f"throughput {_selesai / total:.2f} req/s ===")
