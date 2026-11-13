"""models.py: skema Pydantic (validasi request & serialisasi response)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    judul: str = Field(min_length=1, max_length=200)
    penulis: str = Field(min_length=1, max_length=100)
    kategori: str = Field(min_length=1, max_length=50)
    harga: float = Field(gt=0)
    stok: int = Field(ge=0)


class Book(BaseModel):
    # Response tanpa batas ge=0 agar stok negatif (demo overselling B3 Tahap 1) tetap bisa ditampilkan
    id: int
    judul: str
    penulis: str
    kategori: str
    harga: float
    stok: int


class TransactionCreate(BaseModel):
    item_id: int = Field(gt=0)   # id buku
    qty: int = Field(gt=0)


class TransactionOut(BaseModel):
    id: int
    item_id: int
    qty: int
    total_harga: float
    status: Literal["pending", "processing", "completed", "failed"]
    catatan: Optional[str] = None
    created_at: str


class TransactionAccepted(BaseModel):
    id: int
    status: str
    message: str
