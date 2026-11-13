"""routes/resource.py: CRUD resource utama (buku)."""
from fastapi import APIRouter, HTTPException, Query, status

import database as db
from models import Book, BookCreate

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("", response_model=list[Book], status_code=status.HTTP_200_OK)
async def daftar_buku(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return await db.list_books(skip, limit)


@router.get("/{book_id}", response_model=Book)
async def detail_buku(book_id: int):
    book = await db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return book


@router.post("", response_model=Book, status_code=status.HTTP_201_CREATED)
async def tambah_buku(data: BookCreate):
    new_id = await db.insert_book(data.model_dump())
    return await db.get_book(new_id)


@router.put("/{book_id}", response_model=Book)
async def perbarui_buku(book_id: int, data: BookCreate):
    if not await db.update_book(book_id, data.model_dump()):
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return await db.get_book(book_id)


@router.delete("/{book_id}")
async def hapus_buku(book_id: int):
    # Hard delete: data dihapus permanen dari SQLite
    if not await db.delete_book(book_id):
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return {"message": f"Buku {book_id} dihapus permanen"}
