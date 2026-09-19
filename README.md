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
   uv run --env-file ../.env python manage.py migrate
   uv run --env-file ../.env python manage.py runserver 8010
   ```
   - `migrate` สร้างตารางในฐานข้อมูล (รันครั้งแรกและทุกครั้งที่มี migration ใหม่)
   - สร้างผู้ดูแลระบบคนแรกด้วย `uv run --env-file ../.env python manage.py createsuperuser`
     แล้วเข้าหน้าจัดการที่ http://localhost:8010/admin/ (ใช้ชั่วคราวจนกว่าจะมีหน้าจัดการผู้ใช้จริง)
   - สร้างบัญชีทดสอบครบ 3 บทบาท: ตั้ง `DEMO_PASSWORD=รหัสที่คุณเลือก` ใน `.env` (ยาวอย่างน้อย 12 ตัวอักษร)
     แล้วรัน `uv run --env-file ../.env python manage.py seed_demo` (รันซ้ำได้ — จะรีเซ็ตบัญชีเหล่านี้ให้ตรงเดิม)

     | บทบาท | รหัส | อีเมล |
     |---|---|---|
     | ผู้ดูแลระบบ | `ADM001` | `admin.demo@mangosteen.test` |
     | ผู้สอน | `TCH001` | `teacher.demo@mangosteen.test` |
     | ผู้เรียน | `6501001` | `student.demo@mangosteen.test` |

     ล็อกอินที่ http://localhost:5180/login ด้วยรหัสหรืออีเมลก็ได้ — คำสั่งนี้ทำงานเฉพาะเมื่อ `DJANGO_DEBUG=1` (ห้ามใช้บนเว็บจริง)
4. **รัน frontend** (โฟลเดอร์ `frontend/`)
   ```
   pnpm install
   pnpm dev
   ```
   เปิด http://localhost:5180 — คำขอที่ขึ้นต้นด้วย `/api` จะถูก proxy ไปหา Django ที่ `http://localhost:8010`

### พอร์ตที่โปรเจกต์นี้ใช้
โปรเจกต์นี้ใช้พอร์ตของตัวเอง (ไม่ใช่ค่ามาตรฐาน) เพื่อไม่ให้ชนกับโปรเจกต์อื่นที่รันอยู่บนเครื่อง

| ส่วน | พอร์ต | ตั้งค่าที่ |
|---|---|---|
| Frontend (Vite) | 5180 | `frontend/vite.config.ts` (ถ้าพอร์ตถูกใช้อยู่ Vite จะหยุดพร้อมแจ้ง ไม่เลื่อนไปพอร์ตอื่นเงียบ ๆ) |
| Backend (Django) | 8010 | ระบุตอนรัน `runserver 8010` |
| Postgres | 5432 (ค่าเริ่มต้น) | `POSTGRES_PORT` ใน `.env` |

- ถ้าเปลี่ยนพอร์ต backend ให้ตั้ง `API_PROXY_TARGET` ให้ตรงตอนรัน frontend
  (PowerShell: `$env:API_PROXY_TARGET="http://localhost:8011"`)
- **Postgres**: ถ้ามี PostgreSQL อื่นใช้พอร์ต 5432 อยู่แล้ว (จะต่อผิดตัวและล็อกอินไม่ผ่าน) ให้ตั้ง `POSTGRES_PORT=5433` ใน `.env`
  แล้วรัน `docker compose up -d db` ใหม่

## ตรวจโค้ดก่อน push (ตรงกับที่ CI รัน)

| ส่วน | คำสั่ง |
|---|---|
| Backend (ใน `backend/`) | `uv run ruff check .` · `uv run ruff format --check .` · `uv run --env-file ../.env pytest` |
| Frontend (ใน `frontend/`) | `pnpm run typecheck` · `pnpm run lint` · `pnpm run test` |
