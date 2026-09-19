# โปรเจกต์: LMS (Learning Management System)

ระบบ LMS ลักษณะคล้าย Mango CMU (LMS ของมหาวิทยาลัยเชียงใหม่) รองรับการใช้งานแบบออนไลน์ แบ่งสิทธิ์ผู้ใช้เป็น 3 ระดับ: Administrator, Teacher/Instructor, Student

## Tech Stack

- **Backend**: Django 5.2 + Django REST Framework — Python 3.13
- **Frontend**: React + Vite + TypeScript + Tailwind CSS v4
- **Database**: PostgreSQL — dev local รันผ่าน Docker Compose (ไม่ต้องติดตั้ง Postgres ลงเครื่องโดยตรง) — Docker Compose ครอบคลุม **เฉพาะ Postgres** เท่านั้น ส่วน backend (Django/uv) และ frontend (Vite/pnpm) รันตรงบนเครื่องตามปกติ ไม่ containerize
- **File Storage**:
  - Cloudinary (free tier) — สำหรับรูปภาพ / เอกสาร (PDF, Word ฯลฯ) / ไฟล์งานทั่วไป / **วิดีโอ (ช่องทางหลัก)**
  - วิดีโอ: เก็บบน Cloudinary เป็นหลัก **และ** รองรับให้ผู้สอนแปะลิงก์ YouTube เอง (embed) เป็นทางเลือกได้ด้วย → `Content` วิดีโอต้องมี field แยกว่าเป็น `cloudinary_upload` หรือ `youtube_url`
  - **ไม่ใช้ YouTube Data API upload** (ตัดออกจากแผนเดิม — ติดข้อจำกัด OAuth, โควตา ~6 คลิป/วัน, และคลิปถูกล็อก private จนกว่า Google จะ audit)
- **Package Manager**: `uv` (Python/backend) + `pnpm` (Node/frontend) — ใช้ตัวนี้เสมอ อย่าสลับไป pip/npm
- **Authentication**: JWT ผ่าน `djangorestframework-simplejwt` (frontend/backend แยก origin กันชัดเจน — JWT เลี่ยงปัญหา CORS/CSRF ที่ยุ่งยากกว่าถ้าใช้ session-based ของ Django) ใช้ access/refresh token, เก็บ role ไว้ใน user model แล้ว custom serializer ใส่ role ลงใน token claims เพื่อให้ frontend ตรวจสิทธิ์ได้จาก token
  - **2 ช่องทางเข้าระบบ**: (1) รหัสนักศึกษา/รหัสพนักงาน — Admin สร้างบัญชีให้ (รองรับ bulk import CSV ภายหลัง) และ (2) อีเมล + สมัครเอง → **ต้องยืนยันอีเมลก่อน** แล้วได้ role `Student` อัตโนมัติเท่านั้น (role Teacher/Admin ต้อง Admin สร้างหรือเลื่อนขั้นเท่านั้น) → `User` model ต้องมีทั้ง `student_or_staff_id` (nullable, unique) และ `email` (unique) + flag `is_email_verified`
    - การสมัครด้วยอีเมล (ช่องทางที่ 2) **เปิดรับทุกโดเมนอีเมล** ไม่จำกัดเฉพาะโดเมนมหาวิทยาลัย
  - **การเก็บ token ฝั่ง frontend (ตัดสินใจแล้ว)**: access token เก็บ**ในหน่วยความจำ**เท่านั้น (ไม่ใช้ localStorage) ส่วน refresh token เก็บใน **httpOnly cookie** — เพื่อกัน XSS ขโมย token. เปิด refresh token rotation + blacklist ของ simplejwt. ตอน deploy ต้องให้ frontend/backend เป็น same-site (frontend proxy `/api` ไปหา backend หรือใช้โดเมนเดียวกัน) เพื่อไม่ให้เบราว์เซอร์บล็อก cookie — ผูกกับการเลือก hosting (ยังไม่ตัดสินใจ)
  - **หน้า login (ตัดสินใจแล้ว)**: ช่องเดียวรับทั้งรหัสนักศึกษา/พนักงานและอีเมล — ระบบเดาชนิดจากการมีอักขระ `@` (มี = อีเมล, ไม่มี = รหัส)
- **Email**: ตอน dev ใช้ Django console backend ไปก่อน — เขียนโค้ดผ่าน abstraction ของ Django (`send_mail` / templated email) ไม่ hard-code provider ใด **ยังไม่เลือก provider สำหรับ production** (จะถามผู้ใช้ตอนใกล้ deploy)
- **i18n**: รองรับ 2 ภาษา (ไทย/อังกฤษ) **ตั้งแต่แรก** — frontend แยกข้อความเป็น translation key ทั้งหมด (ค่า default = ไทย) อย่า hard-code ข้อความลง component
- **Timezone**: `Asia/Bangkok` (สมมติเป็นค่าเริ่มต้นเพราะเป็น LMS มหาวิทยาลัยไทย — แจ้งผู้ใช้ถ้าต้องเปลี่ยน) เก็บ datetime เป็น UTC ใน DB, แปลงตอนแสดงผล
- **CI**: ตั้ง GitHub Actions **ตั้งแต่ก้อนแรก** — รันอัตโนมัติตอน push/PR: backend = `pytest` + `ruff`; frontend = `tsc --noEmit` + `eslint` + `vitest`
- **External APIs อื่นๆ**: ยังไม่ได้เลือก — ผู้ใช้จะแจ้งให้ช่วยแนะนำในภายหลัง อย่าเพิ่ม API ใหม่เองโดยไม่ถาม

## โครงสร้างโปรเจกต์

แยกโฟลเดอร์ชัดเจนระหว่าง backend และ frontend ที่ root ของ repo:

```
/backend    → Django + DRF project
/frontend   → React + Vite + TypeScript + Tailwind v4
```

## Code Comments & เอกสารโครงสร้างไฟล์

- **Comment ในโค้ด**: เขียน comment กำกับไว้ในโค้ดของโปรเจกต์นี้เสมอ เพื่อให้อ่านแล้วเข้าใจว่าส่วนนั้น ๆ ทำอะไร ในทุกส่วน(ไม่ต้องรอให้ไม่ชัดเจนก่อนค่อยเขียน) — เน้นอธิบายว่าโค้ดส่วนนั้นทำหน้าที่อะไร เป็นภาษไทย
- **ไฟล์โครงสร้างโปรเจกต์**: ต้องมีไฟล์เอกสารแยกต่างหาก (เช่น `PROJECT_STRUCTURE.md` ที่ root ของ repo) ที่บอกโครงสร้างไฟล์/โฟลเดอร์ทั้งหมดของโปรเจกต์ — แต่ละโฟลเดอร์/ไฟล์ต้องมีคำอธิบายกำกับว่าใช้เก็บ/ทำหน้าที่อะไร
  - ต้องอัปเดตไฟล์นี้ให้ตรงกับโครงสร้างจริงอยู่เสมอเมื่อมีการเพิ่ม/ย้าย/ลบไฟล์หรือโฟลเดอร์สำคัญ

## สิทธิ์การใช้งานตาม Role (Baseline — เพิ่มเติมได้ภายหลัง)

### ทุก Role (All Roles)
- Authentication: Login / Logout
- Dashboard: หน้าสรุปภาพรวม คัดกรองเนื้อหาตามสิทธิ์ของแต่ละ role

### Administrator
- User Management: เพิ่ม/แก้ไขบัญชีผู้เรียนและผู้สอน
- System Support: เข้าจัดการข้อมูล/ฟังก์ชันแทนผู้สอนเพื่อช่วยแก้ปัญหา
- Role Impersonation: สลับมุมมอง (preview) เป็น role อื่นได้
- Audit Log: ดูประวัติการกระทำ (log) ย้อนหลังเพื่อตรวจสอบการเปลี่ยนแปลงข้อมูล

### Teacher / Instructor
- Course Management: สร้าง/เตรียมโครงสร้างรายวิชา
- Content Management: เพิ่มสื่อการสอน รองรับไฟล์มัลติมีเดีย (รูปภาพ, วิดีโอ, เสียง)
- Assessment Management: สร้างแบบฝึกหัดท้ายบท — รองรับ ปรนัย 4 ตัวเลือก, ถูก/ผิด, จับคู่, Dropdown, อัตนัยแบบสั้น; ตั้งค่า Timed Quiz ได้
- Assignment Management: สร้างชิ้นงาน เขียนคำอธิบาย แนบไฟล์ประกอบ รองรับการอัปโหลดไฟล์ส่งงานจากผู้เรียน
- Grading System: จัดการและบันทึกคะแนนผู้เรียนในรายวิชา
- Announcement: สร้างประกาศแจ้งเตือนภายในรายวิชา

### Student
- เข้าถึงรายวิชา เนื้อหาบทเรียน และประกาศ
- เข้าทำ Quiz / สอบย่อย ดูรายละเอียดภาระงาน (assignment) และอัปโหลดไฟล์ส่งงาน

> หมายเหตุ: รายการฟีเจอร์ข้างต้นเป็น baseline เบื้องต้น สามารถเพิ่มเติมได้ในอนาคต — อย่าตัดขอบเขตหรือ assume ว่านี่คือ scope สุดท้าย

## Data Model — การตัดสินใจสำคัญ (ตัดสินใจไว้ก่อนเริ่ม code)

> **เอกสารออกแบบฐานข้อมูลฉบับเต็มอยู่ที่ `docs/`** (v1.4 freeze แล้ว) — เริ่มอ่านที่ `docs/database-guide.md` (ใครเขียน/ใครอ่าน/workflow ครบวงจร) แล้วดู `docs/database.md` (สเปก field/constraint), `docs/database-erd.md` (ERD), `docs/database-fields.md` (quick ref). หัวข้อด้านล่างเป็นเพียงสรุปการตัดสินใจหลัก ถ้ามีรายละเอียดขัดกันให้ยึด `docs/` และถามผู้ใช้

- **Enrollment**: รองรับทั้ง 2 แบบ — (1) Admin/Teacher เป็นคน assign นักศึกษาเข้ารายวิชา และ (2) นักศึกษาลงทะเบียนเองด้วยรหัสวิชา (course code/invite code) ต้องมี model `Enrollment` แยกจาก `Course` และ `User` (many-to-many ผ่าน model กลาง)
  - **Invite code**: ระบบสุ่มให้อัตโนมัติ (ไม่ให้ผู้สอนพิมพ์เอง) ผู้สอนสามารถ regenerate รหัสใหม่ได้ภายหลังหากต้องการ
- **Co-teacher / TA**: 1 รายวิชารองรับผู้สอนได้หลายคน (co-teacher) — ความสัมพันธ์ Course↔Teacher เป็น many-to-many ไม่ใช่ FK เดี่ยว
- **Grading**: ถ่วงน้ำหนักตาม category (เช่น Quiz 20% + Assignment 30% + Final 50%) — ต้องมี model สำหรับ "Grading Category/Component" ต่อรายวิชา พร้อม weight, แล้วคะแนนรวมของนักศึกษาคำนวณจาก weighted sum ไม่ใช่ raw score รวมตรงๆ ออกแบบ schema ให้รองรับตั้งแต่แรกเพราะ retrofit ทีหลังยาก
  - **ผลลัพธ์สุดท้าย**: ระบบออกเป็น **คะแนน % ต่อ category + weighted total (%)** เท่านั้น — **ไม่ต้องมีเกรดตัวอักษร (A/B+/...) / GPA** ใน MVP (ถ้าจะเพิ่มภายหลังค่อยว่ากัน — ไม่ต้องออกแบบเผื่อตอนนี้)
- **Term / Semester**: มี model ภาคเรียน/ปีการศึกษา (เช่น "1/2568") — `Course` ผูกกับ `Term` (FK) วิชาเดียวกันที่เปิดสอนหลายเทอมถือเป็นคนละ `Course` record แยก enrollment/คะแนนกัน
- **Quiz attempts**: กำหนดได้ต่อ Quiz ตอนสร้าง (field เช่น `max_attempts` / `attempt_policy`) — เลือกได้ระหว่าง "ทำได้ครั้งเดียว" หรือ "ทำได้หลายครั้งแล้วเก็บคะแนนสูงสุด" ไม่ fix ค่าใดค่าหนึ่งตายตัวทั้งระบบ
- **Late submission (Assignment)**: กำหนดได้ต่อ Assignment ตอนสร้าง — เลือกได้ระหว่าง "ปิดรับตายตัวเมื่อเลย deadline" หรือ "รับส่งสายแบบหักคะแนน (penalty)" ต้องมี field เก็บ policy + penalty rate ต่อชิ้นงาน
- **โครงสร้างเนื้อหารายวิชา**: มีลำดับชั้น `Course → Module → Content` (ไม่ใช่ list เนื้อหาแบบเรียงตรงๆ ใต้ Course)
- **Timed Quiz**: เมื่อหมดเวลา ให้ **auto-submit ทันที** (เก็บคำตอบที่มีอยู่ ณ ตอนนั้น) — enforce ฝั่ง backend ตาม `start_time` ที่บันทึกไว้ (ดูหัวข้อ security ด้านล่าง)
- **Audit Log**: ครอบคลุม action ที่เปลี่ยนแปลงข้อมูลสำคัญ**ทุกส่วน** ไม่จำกัดเฉพาะบาง model — ได้แก่ user, course, enrollment, grade, content, announcement รวมถึง role impersonation (แยก log ชัดเจนตามที่ระบุไว้ในหัวข้อ Administrator) ออกแบบเป็น log กลางแบบ generic ที่จับที่ระดับ model save/delete แทนการ whitelist เฉพาะบาง model
- **Announcement / Notification**: MVP ส่งประกาศ **in-app อย่างเดียว** (แสดงใน dashboard + รายวิชา) ยังไม่ส่งอีเมล — แต่แยก model `Announcement` (เนื้อหา) กับการ "อ่านแล้ว/ยังไม่อ่าน" ต่อผู้ใช้ให้ชัด เผื่อเพิ่มช่องทางส่งภายหลัง

## UI / Design

- มี wireframe แล้ว (dashboard ทั้ง 3 role + หน้า auth) — ต้นฉบับอยู่ที่ https://claude.ai/artifact/QB2y8Qod4AtkfVVFEoWxaZ และสรุปสี/ฟอนต์/โครงหน้าไว้ที่ `docs/design.md` (ยึดตามนี้ ไม่ต้องออกแบบใหม่) โทนสะอาด เรียบ เน้นใช้งานง่าย อ้างอิงสไตล์ Mango CMU ใช้ Tailwind v4 — หน้าที่ยังไม่มี wireframe ให้ Claude เสนอก่อนทำ
- ก่อนลงมือทำหน้าจอที่ซับซ้อน ควรเสนอแนวทาง/wireframe ให้ผู้ใช้ดูก่อน (เช่นผ่าน design canvas) แล้วค่อย implement
- ทุกหน้าจอต้องรองรับ 2 ภาษา (ดู i18n ข้างบน) และ responsive

## Hosting — ยังไม่ตัดสินใจ

ผู้ใช้ยังไม่เลือก hosting provider ที่ชัดเจน อย่า deploy หรือผูก config เข้ากับ provider ใดโดยไม่ถามก่อน แนวทางที่พอจะแนะนำเมื่อถึงเวลาตัดสินใจ (ต้องคุยกับผู้ใช้ก่อนเลือกจริง):
- Frontend (static/Vite build): Vercel, Netlify, Cloudflare Pages
- Backend (Django/DRF): Render, Railway, Fly.io
- Postgres: Supabase, Neon, Railway Postgres, Render Postgres

## Git / Commit Workflow

- **Repo**: https://github.com/AtipatSuttatham/-Mangosteen_Campus.git
- ทำงานทีละส่วนย่อย (incremental) แล้ว push ขึ้น GitHub เป็นก้อนเล็กๆ **ห้าม push เป็นก้อนใหญ่รวมหลายฟีเจอร์ในครั้งเดียว**
- ข้อความ commit (subject) ใช้**ภาษาอังกฤษ** สั้น กระชับ เข้าใจได้ทันทีว่าทำอะไร
- ใน commit ให้เพิ่ม description อธิบายรายละเอียดงานเป็น**ภาษาไทย**
- ตัวอย่างรูปแบบ commit:
  ```
  Add student quiz submission endpoint

  เพิ่ม API endpoint สำหรับให้ผู้เรียนส่งคำตอบแบบฝึกหัด รองรับการบันทึกคำตอบ
  แบบปรนัยและอัตนัยแบบสั้น
  ```

## แนวทางการทำงานร่วมกับ Claude

- ผู้ใช้จะเลือก API ฟรีเพิ่มเติมเพื่อเสริมประสิทธิภาพระบบในภายหลัง — รอให้ผู้ใช้แจ้งก่อน ไม่ต้องเสนอ/เพิ่มเองล่วงหน้า
- เมื่อ implement แต่ละ role's permission ให้ยึดตามสิทธิ์ที่ระบุไว้ข้างต้นเป็นหลัก
- **แนวทางพัฒนา MVP**: ทำทีละฟีเจอร์ให้ครบทุก role ที่เกี่ยวข้อง (vertical slice) ก่อนย้ายไปฟีเจอร์ถัดไป ไม่ใช่ทำ role เดียวให้ครบก่อน — สอดคล้องกับ workflow push เป็นก้อนเล็กๆ ทีละส่วน

### หลักการทำงาน (สำคัญ — ต้องยึดตามนี้เสมอ)

- **ต้องเข้าใจสิ่งที่กำลังทำอยู่จริง ๆ ก่อนลงมือ** — อ่าน context / โค้ด / ข้อกำหนดที่เกี่ยวข้องให้เข้าใจ ไม่เดา ไม่ทำแบบผ่าน ๆ
- **ห้ามคิดเอาเอง / assume แบบไม่มีเหตุผลรองรับ** — ทุกการตัดสินใจต้องอ้างอิงได้ว่ามาจากข้อกำหนดในไฟล์นี้ จากโค้ดที่มีอยู่ หรือจากสิ่งที่ผู้ใช้บอก
- **ส่วนไหนที่ไม่ชัดเจน (unclear) ให้หยุดแล้วถามผู้ใช้ก่อน** พร้อมเสนอทางเลือกให้เลือก (พร้อมข้อดี/ข้อเสียของแต่ละทาง) ไม่ตัดสินใจแทนเองแล้วเดินหน้าต่อ
- **ถ้าต้องการข้อมูลเพิ่มเพื่อทำงานให้ถูกต้อง ให้ถาม / ขอความเห็นจากผู้ใช้** อย่าเติมช่องว่างด้วยการสมมติ
- กรณีที่มีค่า default ที่เป็นมาตรฐานชัดเจนและความเสี่ยงต่ำ ให้เลือก default นั้นได้ แต่ต้องบอกผู้ใช้ว่าเลือกอะไรและเพราะอะไร
- **ทุกครั้งที่แก้ไขโค้ดแล้วต้องรอให้ผู้ใช้ accept การแก้ไข** ให้อธิบายก่อน/พร้อมกับการแก้ไขนั้นว่า (1) แก้อะไร — ไฟล์/ส่วนไหน เปลี่ยนจากอะไรเป็นอะไร (2) ทำไมถึงต้องแก้ — อ้างอิงปัญหา/ความต้องการที่มาของการแก้ และ (3) ทำไมถึงเลือกวิธีนี้ — เหตุผลเบื้องหลังแนวทางที่เลือก โดยเฉพาะถ้ามีทางเลือกอื่นที่เป็นไปได้
