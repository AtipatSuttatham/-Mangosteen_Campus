# Mangosteen Campus

ระบบ LMS (Learning Management System) แบบ 3 บทบาท: ผู้ดูแลระบบ / ผู้สอน / ผู้เรียน
รายละเอียดข้อกำหนดและ tech stack อยู่ใน [`CLAUDE.md`](./CLAUDE.md) · โครงสร้างไฟล์อยู่ใน [`PROJECT_STRUCTURE.md`](./PROJECT_STRUCTURE.md)

## สิ่งที่ต้องมีในเครื่อง
Docker Desktop · [uv](https://docs.astral.sh/uv/) · Node.js 22+ · [pnpm](https://pnpm.io/)

## เริ่มใช้งานในเครื่อง (dev)

1. **ตั้งค่า environment** — คัดลอก `.env.example` เป็น `.env` ที่ root แล้วใส่รหัสผ่าน Postgres ในช่อง `POSTGRES_PASSWORD`
   (ไฟล์ `.env` ไม่เข้า git)
2. **เปิดฐานข้อมูล** — เปิด Docker Desktop แล้วรัน `docker compose up -d db`
3. **รัน backend** (โฟลเดอร์ `backend/`)
   ```
   uv sync
   uv run --env-file ../.env python manage.py runserver
   ```
   > ⚠️ ยังไม่ต้องรัน `migrate` — ต้องรอให้มี User model แบบกำหนดเอง (ก้อนระบบ login) ก่อน มิฉะนั้นตารางผู้ใช้จะถูกสร้างผิดแบบ
4. **รัน frontend** (โฟลเดอร์ `frontend/`)
   ```
   pnpm install
   pnpm dev
   ```
   เปิด http://localhost:5173 — คำขอที่ขึ้นต้นด้วย `/api` จะถูก proxy ไปหา Django ที่ `http://localhost:8000`

### ถ้าพอร์ตชนกับโปรแกรมอื่น
- **Postgres (5432)**: ถ้ามี PostgreSQL อื่นใช้พอร์ตนี้อยู่ ให้ตั้ง `POSTGRES_PORT=5433` ใน `.env` แล้วรัน `docker compose up -d db` ใหม่
- **Backend (8000)**: `uv run --env-file ../.env python manage.py runserver 8001` แล้วเปิด frontend ด้วย
  `API_PROXY_TARGET=http://localhost:8001` (PowerShell: `$env:API_PROXY_TARGET="http://localhost:8001"`)
- **Frontend (5173)**: `pnpm dev --port 5174`

## ตรวจโค้ดก่อน push (ตรงกับที่ CI รัน)

| ส่วน | คำสั่ง |
|---|---|
| Backend (ใน `backend/`) | `uv run ruff check .` · `uv run ruff format --check .` · `uv run --env-file ../.env pytest` |
| Frontend (ใน `frontend/`) | `pnpm run typecheck` · `pnpm run lint` · `pnpm run test` |
