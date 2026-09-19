# เอกสารออกแบบฐานข้อมูล — LMS

> สถานะ: **freeze แล้ว (v1.4)** — ผ่านรีวิวเชิงวิจารณ์ 2 รอบ (2026-09-09) + ปรับ v1.4 ตามการตัดสินใจของผู้ใช้
> อัปเดตล่าสุด: v1.4 (ดูรายการที่ §11 "รีวิว v1.4")
>
> **v1.1** = ยกเลิกการแยก `_th/_en` ทั้งหมด
> **v1.2** = เส้นแบ่ง hard-delete ชัดขึ้น, soft-delete ใช้ conditional unique, สูตร weighted total เขียนใหม่ (นับข้อที่ไม่ทำ = 0), `is_graded` บน Quiz/Assignment, `Assignment.due_at` nullable + `accept_until`, กลไก AuditLog กันเขียนซ้ำ, มาตรฐาน Decimal precision
> **v1.3** = ปิดขอบ hard-delete ที่เหลือ (User ไม่ลบจริง + `student`/`grade_item` FK → PROTECT), `GradingCategory` → PROTECT, `matching` ให้คะแนนบางส่วน, กลไก sync คะแนน submission/attempt → Score, `due_at` timed quiz เทียบ `available_until`
> **v1.4** = `EmailVerificationToken.token` → `token_hash` (เก็บ SHA-256 ไม่เก็บโทเคนจริง), กฎ normalize `User.email` (ตัวพิมพ์เล็ก) และ `User.student_or_staff_id` (ตัดช่องว่างหัวท้าย แยกตัวพิมพ์ ห้ามมี `@`), รูปแบบ `Course.invite_code`

เอกสารนี้กำหนด "แผนที่" ของ data model ทั้งระบบก่อนเริ่ม code ตามที่ระบุใน `CLAUDE.md`
(หัวข้อ "Data Model — การตัดสินใจสำคัญ") field ปลีกย่อยยังปรับได้ภายหลังด้วย migration
แต่ **ความสัมพันธ์ระหว่างตาราง (cardinality) + ชนิด PK ถือว่า freeze แล้ว** — แก้ได้แต่ต้องมีเหตุผลชัด

**บันทึกการตัดสินใจอยู่ที่ §11 · สิ่งที่ตั้งใจไม่ทำใน MVP อยู่ที่ §13**

เอกสารชุดนี้: ไฟล์นี้ (สเปก) · [`database-erd.md`](./database-erd.md) (ERD) · [`database-fields.md`](./database-fields.md) (quick ref ราย field) · [`database-guide.md`](./database-guide.md) (**ใครเขียน/ใครอ่าน/lifecycle/workflow ครบวงจร** — อ่านตัวนี้ถ้าต้องเข้าใจว่าแต่ละส่วนใช้ยังไง)

---

## 1. หลักการออกแบบร่วม (ใช้กับทุก model)

| หัวข้อ | การตัดสินใจ | เหตุผล |
|---|---|---|
| Primary key | `BigAutoField` (int) ทุกตาราง | เรียบง่าย พอสำหรับ MVP — ค่อยเพิ่ม public UUID/slug เฉพาะ resource ที่ต้องเปิดใน URL ทีหลังได้ |
| Timestamp | ทุก model หลัก inherit `TimeStampedModel` (`created_at`, `updated_at`) | audit / เรียงลำดับ |
| Timezone | เก็บ `datetime` เป็น UTC ใน DB, แปลงเป็น `Asia/Bangkok` ตอนแสดง — **การคำนวณที่อิง"วัน" (เช่น `days_late`) ต้องทำใน `Asia/Bangkok`** ไม่ใช่ UTC | มาตรฐาน Django (`USE_TZ = True`) ; ส่งงานตี 2 UTC = คนละวันกับเวลาไทย |
| Decimal | คะแนน (`max_score`, `points`, `raw_score`, `score` ฯลฯ) = `DecimalField(max_digits=7, decimal_places=2)` ; เปอร์เซ็นต์ (`weight_percent`, `*_percent`) = `DecimalField(max_digits=5, decimal_places=2)` | มาตรฐานเดียวทั้งระบบ กัน float error |
| **เส้นแบ่งการลบ (v1.2/v1.3)** | **hard-delete จริงได้เฉพาะ record ที่ยังเป็น draft — ไม่เคย `is_published=True` และไม่มีข้อมูลนักศึกษาอ้างถึง** ; นอกนั้น = ซ่อนด้วย `is_published`/`status` หรือ soft-delete. FK ที่เชื่อมเข้าสู่ระบบคะแนนใช้ `PROTECT`: `GradeItem.quiz` / `GradeItem.assignment` / `GradeItem.category` / `Score.grade_item` / `Score.student` / `Submission.student` / `QuizAttempt.student` | กันคะแนน/หลักฐานหายจาก cascade — และกัน hard-delete ทะลุ soft-delete ทุกขอบ |
| **User ไม่ hard-delete (v1.3)** | `User` ที่มีประวัติการเรียน/การสอน (มี `Enrollment`/`CourseTeacher`/`Submission`/`QuizAttempt`/`Score`) → ปิดด้วย `is_active=False` เท่านั้น ไม่ลบจริง ; คำขอ "ลบบัญชี" ตาม PDPA = ทำเป็น anonymize (แทนที่ชื่อ/อีเมลด้วย placeholder) ทีหลัง — ยังไม่ทำใน MVP | คะแนน/หลักฐานผูกกับ User ทั้งหมด |
| Soft delete | **ทำเฉพาะ `Submission`, `QuizAttempt`, `Score`** (inherit `SoftDeleteModel`). unique ของ 3 ตารางนี้ใช้ `UniqueConstraint(..., condition=Q(deleted_at__isnull=True))` — unique เฉพาะแถวที่ยังไม่ลบ (กรอกใหม่หลังลบได้) | 3 ตารางนี้เป็นหลักฐาน/คะแนน ครูต้องมีปุ่มลบทิ้ง (Q10) แต่ลบจริงไม่ได้ |
| การจัดลำดับ (ordering) | field `order` (int) — **ไม่**ใส่ unique constraint ; reorder ผ่าน API ที่เขียนค่า `order` ใหม่ทั้ง list ใน transaction เดียว | unique constraint ทำให้สลับลำดับยาก |
| ภาษาของข้อมูล (Q1) | **ไม่แยก `_th` / `_en` เลย — field เดียวทั้งระบบ** (`Course.name`, `Module.title`, `Content.title`, `Quiz.title`, `Assignment.title` ฯลฯ). ครู/นักศึกษาพิมพ์ภาษาใดก็ได้ | i18n ในโปรเจกต์นี้ = **UI chrome เท่านั้น** (ปุ่ม/ป้าย/ข้อความระบบ แยกเป็น translation key) ไม่บังคับ user-generated content เป็น 2 ภาษา — ถ้าจะเพิ่มทีหลังค่อยทำเป็น translation table แยก |
| ไฟล์ | Content: เก็บ field ไฟล์ inline (1 content = 1 ไฟล์หลัก) / งานที่มีหลายไฟล์ (submission, assignment attachment) แยกตาราง `*File` | ตรงกับพฤติกรรมจริงของแต่ละส่วน |

### Abstract / mixin models

- **`TimeStampedModel`** (abstract): `created_at`, `updated_at`
- **`Auditable`** (abstract): marker ให้ signal `post_save` / `post_delete` เขียน `AuditLog` อัตโนมัติ — domain model เกือบทั้งหมด inherit ตัวนี้ (ไม่รวม infra เช่น session, token, ตัว `AuditLog` เอง) ดู §9
- **`SoftDeleteModel`** (abstract): `deleted_at` (datetime, `null=True`), `deleted_by` (FK → `User`, `SET_NULL`, `null=True`) + custom manager (`objects` = ซ่อนแถวที่ลบแล้ว, `all_objects` = เห็นทั้งหมด). ใช้กับ `Submission`, `QuizAttempt`, `Score` เท่านั้น (Q10) — `.delete()` = set `deleted_at`, ไม่ลบจริง. **unique constraint ของ model ที่ใช้ mixin นี้ต้องมี `condition=Q(deleted_at__isnull=True)`** เพื่อให้กรอกข้อมูลชุดเดิมใหม่ได้หลังลบ

---

## 2. Django apps (แบ่งโดเมน)

```
backend/
  accounts/       User, EmailVerificationToken
  academics/      Term, Course, CourseTeacher
  content/        Module, Content
  enrollment/     Enrollment
  assessments/    Quiz, Question, Choice, MatchingPair, QuizAttempt, Answer
  assignments/    Assignment, AssignmentAttachment, Submission, SubmissionFile
  grading/        GradingCategory, GradeItem, Score, CourseGrade
  announcements/  Announcement, AnnouncementRead
  notifications/  Notification
  audit/          AuditLog
  common/         TimeStampedModel, Auditable, SoftDeleteModel, utilities
```

---

## 3. Accounts

### `User` (custom, extends `AbstractBaseUser` + `PermissionsMixin`)

| field | type | หมายเหตุ |
|---|---|---|
| `email` | Email, **unique**, required | ใช้ login ได้ (ช่องทางสมัครเอง) — **เก็บเป็นตัวพิมพ์เล็กเสมอ** (แปลงก่อนบันทึก) จึงห้ามซ้ำแบบไม่สนตัวพิมพ์ (v1.4) |
| `student_or_staff_id` | Char, **unique**, `null=True` | รหัส นศ./พนักงาน — ใช้ login ได้ (ช่องทาง Admin สร้าง) นศ.สมัครเองอาจยังไม่มี. **กฎ (v1.4):** ตัดช่องว่างหัวท้ายก่อนบันทึก, **แยกตัวพิมพ์เล็ก/ใหญ่** (`S123` ≠ `s123`), ห้ามมีอักขระ `@` (ใช้แยกจากอีเมลตอน login), ถ้าไม่มีรหัสต้องเป็น `NULL` ไม่ใช่สตริงว่าง (กัน unique ชนกัน) |
| `role` | Char choices: `admin` / `teacher` / `student` | เก็บใน token claims ด้วย |
| `first_name`, `last_name` | Char | ชื่อที่ผู้ใช้กรอก (ภาษาใดก็ได้) |
| `first_name_en`, `last_name_en` | Char, blank | ชื่ออังกฤษ (optional) สำหรับเอกสาร/รายชื่อทางการ |
| `is_email_verified` | Bool, default `False` | ต้อง `True` ก่อนเข้าใช้งาน (เฉพาะบัญชีสมัครเอง) |
| `is_active` | Bool, default `True` | Django — Admin ปิดบัญชีได้ |
| `is_staff` / `is_superuser` | Bool | สำหรับ Django admin เท่านั้น (แยกจาก `role`) |
| `avatar_url` | URL, blank | Cloudinary |
| `created_by` | FK → `User`, `null=True`, `SET_NULL` | ใครสร้างบัญชีนี้ (null = สมัครเอง) |
| `last_login`, `date_joined` | Django default | |

**กฎ role** (ปรับ v1.2 — Q5/E)
- สมัครเองผ่านอีเมล → บังคับ `role = student` เสมอ, `is_email_verified = False` จนกว่ายืนยัน
- `teacher` / `admin` → Admin สร้าง หรือ Admin เลื่อนขั้นเท่านั้น (เขียน `AuditLog` ทุกครั้ง)
- `User.role` = **สิทธิ์ระดับระบบ** (เช่น เข้า Admin panel ได้ไหม, สร้างรายวิชาได้ไหม) — 1 บัญชี = 1 role
- **บทบาทในรายวิชาแยกอิสระจาก `User.role`** — ดูจาก `CourseTeacher` / `Enrollment` ต่อวิชา:
  - คนที่ `role=student` **เป็น TA ได้** (`CourseTeacher.course_role=ta` ในวิชา X)
  - คนที่ `role=teacher` **ถูก enroll เป็นนักศึกษาได้** (`Enrollment` ในวิชา Y)
  - permission check ทำ**ต่อวิชา** จาก 2 ตารางนี้ ไม่ใช่จาก `User.role` อย่างเดียว

### `EmailVerificationToken`

| field | type | หมายเหตุ |
|---|---|---|
| `user` | FK → `User`, `CASCADE` | |
| `token_hash` | Char(64), unique | SHA-256 (hex) ของโทเคนสุ่ม — สร้างโทเคนด้วย `secrets.token_urlsafe(32)` แล้วส่งทางอีเมลเท่านั้น **ไม่เก็บโทเคนจริงใน DB** ตอนตรวจลิงก์ให้แฮชโทเคนที่ได้รับแล้วหาด้วย `token_hash` (v1.4) |
| `purpose` | Char choices: `verify_email` / `reset_password` | |
| `expires_at` | datetime, **บังคับ** (ไม่มีโทเคนที่ไม่หมดอายุ) | ผู้สร้างโทเคนกำหนดตามกรณี (v1.4): ยืนยันอีเมลตอนสมัคร +24 ชม. · ลิงก์ตั้งรหัสผ่านที่ Admin ส่งให้บัญชีใหม่ **+7 วัน** · "ลืมรหัสผ่าน" ที่ผู้ใช้ขอเอง +1 ชม. (สองกรณีหลังใช้ `purpose=reset_password` เหมือนกัน ต่างกันที่ `expires_at` จึงไม่ต้องเพิ่ม field) |
| `used_at` | datetime, `null=True` | ใช้แล้วใช้ซ้ำไม่ได้ |

---

## 4. Academics (Term / Course / Teacher)

### `Term`

| field | type | หมายเหตุ |
|---|---|---|
| `academic_year` | int | ปีการศึกษา (เช่น 2568) |
| `semester` | smallint choices: `1` / `2` / `3` | 3 = ภาคฤดูร้อน |
| `name` | Char | label เช่น `"1/2568"` (generate ได้จาก 2 field บน) |
| `start_date`, `end_date` | date | |
| `is_current` | Bool, default `False` | เทอมปัจจุบัน — บังคับ "มีได้ตัวเดียว" ด้วย partial unique index `WHERE is_current` (ไม่พึ่ง validate ในแอปอย่างเดียว) |
| — | unique_together | `(academic_year, semester)` |

### `Course`

| field | type | หมายเหตุ |
|---|---|---|
| `term` | FK → `Term`, `PROTECT` | วิชาเดียวกันคนละเทอม = คนละ record |
| `code` | Char | รหัสวิชา เช่น `"204491"` |
| `section` | Char, `blank=True`, **default `""`** (ไม่ใช่ null) | ตอนเรียน — ใช้ `""` เสมอเมื่อไม่มี เพื่อให้ `unique_together` ทำงานถูก |
| `name` | Char | ชื่อวิชา (ภาษาใดก็ได้) |
| `description` | Text, blank | |
| `self_enroll_enabled` | Bool, default `False` | เปิดให้ลงทะเบียนเองด้วยรหัสไหม |
| `invite_code` | Char, unique, `null=True` | รหัสเข้าเรียน (generate เมื่อเปิด self-enroll). **รูปแบบ (v1.4):** 8 ตัวอักษรจาก `A–Z` (ตัด `I` `L` `O`) และ `2–9` (ตัด `0` `1`) รวม 31 ตัวอักษร เก็บเป็นตัวพิมพ์ใหญ่ไม่มีขีด แสดงเป็น `XXXX-XXXX` ตอนผู้เรียนกรอกไม่สนตัวพิมพ์เล็ก/ใหญ่และตัดช่องว่าง/ขีดออกก่อนเทียบ |
| `is_published` | Bool, default `False` | นักศึกษาเห็น/เข้าได้เมื่อ `True` |
| `created_by` | FK → `User`, `SET_NULL`, `null=True` | |
| — | unique_together | `(term, code, section)` |

### `CourseTeacher` (through: `Course` ↔ `User` แบบ M2M)

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `user` | FK → `User`, `CASCADE` | ปกติเป็น role `teacher`; ระบบไม่ห้าม role อื่นเป็น TA |
| `course_role` | Char choices: `owner` / `co_teacher` / `ta` | |
| `added_by` | FK → `User`, `SET_NULL`, `null=True` | |
| — | unique_together | `(course, user)` |

> **สิทธิ์**: `owner` + `co_teacher` = จัดการรายวิชาได้เต็ม / `ta` = ตามที่ผู้สอนกำหนด (ค่าเริ่มต้น: ตรวจงาน + ดูคะแนน, แก้โครงสร้างวิชาไม่ได้) — รายละเอียดสิทธิ์ที่แน่นอนกำหนดตอนทำฟีเจอร์ grading/permission
> **บังคับในแอป**: ทุกวิชาต้องมี `owner` อย่างน้อย 1 คนเสมอ — ลบ/ย้าย owner คนสุดท้ายไม่ได้ถ้าไม่ตั้งคนใหม่ก่อน

---

## 5. Content (`Course → Module → Content`)

### `Module`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `title` | Char | ชื่อบท |
| `description` | Text, blank | |
| `order` | int | ลำดับใน course |
| `is_published` | Bool, default `False` | |

### `Content`

| field | type | หมายเหตุ |
|---|---|---|
| `module` | FK → `Module`, `CASCADE` | |
| `title` | Char | ชื่อหัวข้อ |
| `content_type` | Char choices: `text` / `file` / `image` / `video` / `audio` / `link` | discriminator |
| `body` | Text, blank | เนื้อหา rich text (สำหรับ `text`) |
| `order` | int | |
| `is_published` | Bool, default `False` | |
| `available_from` | datetime, `null=True` | ตั้งเวลาปล่อยเนื้อหา |
| **ไฟล์ (ใช้เมื่อ type = file/image/audio):** | | |
| `file_url` | URL, blank | Cloudinary |
| `file_name`, `file_size`, `mime_type` | Char/int | metadata |
| **วิดีโอ (ใช้เมื่อ type = video):** | | |
| `video_source` | Char choices: `cloudinary` / `youtube`, `null=True` | ตาม `CLAUDE.md` — Cloudinary เป็นหลัก + แปะ YouTube ได้ |
| `video_url` | URL, blank | URL วิดีโอ Cloudinary หรือลิงก์ YouTube |
| **ลิงก์ (ใช้เมื่อ type = link):** | | |
| `external_url` | URL, blank | |

> **ทางเลือกที่พิจารณาแล้วไม่เลือก**: แยกตาราง `ContentAsset` (1 content หลายไฟล์) — เกินความจำเป็นของ MVP, ถ้าต้องการหลายไฟล์ต่อ 1 หัวข้อให้สร้างหลาย `Content` แทน

---

## 6. Enrollment

### `Enrollment` (through: `Course` ↔ `User` (student) แบบ M2M)

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `student` | FK → `User`, `CASCADE` | |
| `status` | Char choices: `invited` / `active` / `dropped` / `completed` | |
| `method` | Char choices: `admin_assigned` / `self_enrolled` | (1) Admin/Teacher assign หรือ (2) รหัสเข้าเรียน |
| `enrolled_by` | FK → `User`, `SET_NULL`, `null=True` | null = ลงทะเบียนเอง |
| `enrolled_at` | datetime | |
| `dropped_at` | datetime, `null=True` | |
| — | unique_together | `(course, student)` |

> รองรับ 2 flow ตาม `CLAUDE.md`:
> - Admin/Teacher เพิ่มรายชื่อ → สร้าง `Enrollment(status=active, method=admin_assigned)` — **active ทันที ไม่ต้องให้ นศ. กดยืนยัน (Q7)**
> - นศ. กรอก `Course.invite_code` → สร้าง `Enrollment(status=active, method=self_enrolled)`
>
> status `invited` ยังคงไว้ใน choices — เผื่อ flow "อนุมัติก่อนเข้า" ในอนาคต (ยังไม่ใช้ใน MVP)

---

## 7. Assessments (Quiz / แบบฝึกหัดท้ายบท)

### `Quiz`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | denormalized เพื่อ query/permission ง่าย |
| `module` | FK → `Module`, `SET_NULL`, `null=True` | "ท้ายบท" — ผูกกับ module ได้ (ไม่บังคับ) — Q2 |
| `title` | Char | ชื่อ quiz |
| `description` | Text, blank | |
| `is_graded` | Bool, default `True` | `True` = publish แล้วสร้าง `GradeItem` เข้า gradebook ; `False` = quiz ฝึกหัด เห็นคะแนนตัวเอง แต่ไม่เข้าเกรดรวม (v1.2) |
| `grading_category` | FK → `GradingCategory`, `SET_NULL`, `null=True` | คะแนนไปเข้าหมวดไหน (ใช้เมื่อ `is_graded=True`) |
| `max_score` | Decimal | รวมจาก `Question.points` (คำนวณใหม่เมื่อแก้คำถาม) |
| `is_timed` | Bool, default `False` | |
| `time_limit_minutes` | int, `null=True` | ใช้เมื่อ `is_timed` |
| `attempt_policy` | Char choices: `single` / `multiple_highest` | ตาม `CLAUDE.md` |
| `max_attempts` | int, `null=True` | ใช้เมื่อ `multiple_highest` (null = ไม่จำกัด) |
| `available_from`, `available_until` | datetime, `null=True` | ช่วงเวลาเปิดทำ |
| `shuffle_questions` | Bool, default `False` | |
| `show_correct_answers` | Char choices: `never` / `after_submit` / `after_close` | |
| `is_published` | Bool, default `False` | |
| `created_by` | FK → `User`, `SET_NULL`, `null=True` | |

> **แก้ Quiz หลังมีคนทำ (v1.2 — ข้อ C)**: เมื่อมี `QuizAttempt` ของ quiz นี้แล้ว (ใครก็ตามเริ่มทำ) → **ล็อกการแก้เชิงโครงสร้าง**: เพิ่ม/ลบ/เรียงลำดับ `Question`, แก้ `points`, แก้ `Choice.is_correct` / `MatchingPair` ทำไม่ได้ผ่าน API ปกติ. แก้ได้เฉพาะข้อความ (`text`, `explanation`), กำหนดเวลา, `show_correct_answers`.
> ถ้าครูต้องแก้เฉลยที่ผิดจริง → action **`regrade`**: ปลดล็อก, แก้, แล้วสั่ง recompute ทุก `QuizAttempt` + `Answer` ที่กระทบ → เขียน `AuditLog(action=regrade)` 1 แถว

### `Question`

| field | type | หมายเหตุ |
|---|---|---|
| `quiz` | FK → `Quiz`, `CASCADE` | |
| `question_type` | Char choices: `mcq` / `true_false` / `matching` / `dropdown` / `short_answer` | |
| `text` | Text | โจทย์ (rich text) |
| `order` | int | |
| `points` | Decimal | คะแนนของข้อนี้ |
| `explanation` | Text, blank | เฉลย/คำอธิบาย แสดงหลังทำ |
| `shuffle_choices` | Bool, default `False` | ใช้กับ `mcq` / `dropdown` |
| `accepted_answers` | JSON (list[str]), `null=True` | เฉพาะ `short_answer` แบบตรวจอัตโนมัติ — เทียบแบบ normalize (ตัดช่องว่างหัวท้าย, case-insensitive, **Thai-aware**: จัดการวรรณยุกต์/สระซ้ำ — กฎละเอียดกำหนดตอน implement) |
| `manual_grading` | Bool, default `False` | เฉพาะ `short_answer` — `True` = ครูตรวจเอง |

### `Choice` (ใช้กับ `mcq`, `true_false`, `dropdown`)

| field | type | หมายเหตุ |
|---|---|---|
| `question` | FK → `Question`, `CASCADE` | |
| `text` | Char | |
| `is_correct` | Bool | `mcq`/`dropdown` = ถูกได้ตัวเดียว (MVP) ; `true_false` = 2 choice |
| `order` | int | |

> **`dropdown`** ใน MVP = เลือก 1 ตัวจาก list (render เป็น `<select>`) — โครงสร้างเหมือน `mcq` ต่างที่ UI
> ถ้าอนาคตต้องการ "เติมคำในช่องว่างหลายช่อง" ค่อยเพิ่ม field `blank_key` ที่ `Choice` + `Question`

### `MatchingPair` (ใช้กับ `matching`)

| field | type | หมายเหตุ |
|---|---|---|
| `question` | FK → `Question`, `CASCADE` | |
| `left_text` | Char | ฝั่งโจทย์ |
| `right_text` | Char | ฝั่งคำตอบที่ถูกต้อง |
| `order` | int | |

> ตอนทำข้อสอบ ระบบสับ `right_text` ของทุก pair เป็นตัวเลือก — คู่ที่ถูก = `left_i ↔ right_i`
> **การให้คะแนน (v1.3): บางส่วน (partial)** — `points_awarded = Question.points × (จำนวนคู่ที่ถูก / จำนวนคู่ทั้งหมด)` ปัดทศนิยม 2 ตำแหน่ง

### `QuizAttempt` — inherit `SoftDeleteModel` (Q10)

| field | type | หมายเหตุ |
|---|---|---|
| `quiz` | FK → `Quiz`, `PROTECT` | (v1.3 — enforce กฎ §1 ที่ระดับ DB) |
| `student` | FK → `User`, `PROTECT` | (v1.3 — User ไม่ hard-delete) |
| `attempt_number` | int | 1, 2, 3… |
| `status` | Char choices: `in_progress` / `submitted` / `auto_submitted` / `graded` | |
| `started_at` | datetime | **บันทึกฝั่ง server** — ใช้ enforce timed quiz |
| `due_at` | datetime, `null=True` | snapshot ตอนเริ่มทำ = **`min(started_at + time_limit, Quiz.available_until)`** (v1.3) — แก้ setting ทีหลังไม่กระทบ attempt ที่เปิดอยู่ |
| `submitted_at` | datetime, `null=True` | |
| `score` | Decimal, `null=True` | รวมหลังตรวจ |
| `max_score` | Decimal | snapshot ตอนเริ่มทำ |
| `graded_at` | datetime, `null=True` | |
| `graded_by` | FK → `User`, `SET_NULL`, `null=True` | (กรณีมีข้อ manual) |
| `deleted_at`, `deleted_by` | จาก `SoftDeleteModel` | ครูลบ attempt ทิ้งได้ (soft) |
| — | UniqueConstraint | `(quiz, student, attempt_number)` `condition=Q(deleted_at__isnull=True)` |

> `Answer` **ไม่**เป็น soft-delete — `Answer` ของ attempt ที่ถูก soft-delete ยังอยู่ในตาราง : query สถิติ/รายงานต้อง filter ผ่าน `attempt__deleted_at__isnull=True`

**Timed quiz — การบังคับฝั่ง backend** (ตาม `CLAUDE.md` หัวข้อ security):
- ทุกครั้งที่ save คำตอบ / submit → เช็ค `now() <= due_at` ; ถ้าเลย → ปฏิเสธคำตอบใหม่ แล้ว auto-submit ด้วยคำตอบที่มีอยู่ (`status = auto_submitted`)
- attempt ที่ค้าง `in_progress` เกินเวลา → finalize ด้วย **ตัวตั้งเวลา** (คำสั่ง management ที่รันซ้ำได้อย่างปลอดภัย รันทุกนาที) เป็นหลัก + finalize แบบ lazy ตอนมีการเข้าถึงเป็นตาข่ายรอง (ตัดสินใจใน v1.4; ตัวรันจริงเลือกตอนเลือก hosting) — การปฏิเสธคำตอบหลัง `due_at` ทำที่ทุก request อยู่แล้ว ตัวตั้งเวลามีผลแค่ว่าคะแนนออกเมื่อไหร่
- **ตอน submit / auto-submit → สร้างแถว `Answer` ให้ครบทุก `Question` ในชุด** ข้อที่ นศ. ไม่ได้ตอบ = `Answer` ที่ `response` ว่าง, `is_correct=False`, `points_awarded=0` (v1.2 — ข้อ 1) เพื่อให้รายงาน/สถิติต่อข้อครบ

### `Answer` (1 คำตอบต่อ 1 คำถาม ต่อ 1 attempt)

| field | type | หมายเหตุ |
|---|---|---|
| `attempt` | FK → `QuizAttempt`, `CASCADE` | |
| `question` | FK → `Question`, `PROTECT` | |
| `response` | JSON | **canonical store** — รูปแบบตามชนิดคำถาม (ดูตารางล่าง) |
| `selected_choice` | FK → `Choice`, `SET_NULL`, `null=True` | denormalize เฉพาะ `mcq`/`true_false`/`dropdown` เพื่อทำรายงาน |
| `is_correct` | Bool, `null=True` | null = ยังไม่ตรวจ / รอตรวจ manual |
| `points_awarded` | Decimal, `null=True` | |
| `feedback` | Text, blank | ครูใส่ (กรณี manual) |
| `graded_by` | FK → `User`, `SET_NULL`, `null=True` | |
| `graded_at` | datetime, `null=True` | |
| — | unique_together | `(attempt, question)` |

**รูปแบบ `response` ตามชนิดคำถาม:**

| question_type | `response` | ตรวจอัตโนมัติ? |
|---|---|---|
| `mcq`, `dropdown`, `true_false` | `{"choice_id": 123}` | ได้ (เทียบ `Choice.is_correct`) |
| `matching` | `{"pairs": {"<left_id>": <right_id>, ...}}` | ได้ (เทียบทีละคู่ — ให้คะแนนบางส่วน) |
| `short_answer` (auto) | `{"text": "คำตอบ"}` | ได้ (เทียบ `accepted_answers` แบบ normalize) |
| `short_answer` (manual) | `{"text": "คำตอบ"}` | ไม่ได้ — รอครูให้ `points_awarded` |

---

## 8. Assignments

### `Assignment`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `module` | FK → `Module`, `SET_NULL`, `null=True` | |
| `grading_category` | FK → `GradingCategory`, `SET_NULL`, `null=True` | ใช้เมื่อ `is_graded=True` |
| `is_graded` | Bool, default `True` | `True` = publish แล้วสร้าง `GradeItem` ; `False` = งานฝึก ไม่เข้าเกรดรวม (v1.2) |
| `title` | Char | ชื่องาน |
| `description` | Text | rich text |
| `max_score` | Decimal | |
| `due_at` | datetime, **`null=True`** | กำหนดส่ง — null = ไม่มีกำหนด (ไม่มีสถานะ late เลย) (v1.2 — F) |
| `late_policy` | Char choices: `closed_after_due` / `accept_with_penalty` | ใช้เมื่อ `due_at` ไม่ null |
| `accept_until` | datetime, `null=True` | **เส้นตายเด็ดขาด** — เลยเวลานี้ปิดรับจริงแม้ policy = `accept_with_penalty` ; null = ไม่มีเส้นตายเด็ดขาด (v1.2 — G) |
| `penalty_percent_per_day` | Decimal, `null=True` | ใช้เมื่อ `accept_with_penalty` |
| `penalty_max_percent` | Decimal, `null=True` | เพดานการหัก (เช่น 50%) |
| `allow_resubmission` | Bool, default `True` | |
| `allowed_file_types` | JSON (list[str]), `null=True` | เช่น `["pdf","docx"]` (null = ไม่จำกัด) |
| `max_file_size_mb` | int, `null=True` | |
| `max_files` | int, default `1` | |
| `available_from` | datetime, `null=True` | |
| `is_published` | Bool, default `False` | |
| `created_by` | FK → `User`, `SET_NULL`, `null=True` | |

### `AssignmentAttachment` (ไฟล์ประกอบจากผู้สอน)

| field | type |
|---|---|
| `assignment` | FK → `Assignment`, `CASCADE` |
| `file_url`, `file_name`, `file_size`, `mime_type` | Cloudinary + metadata |

### `Submission` — inherit `SoftDeleteModel` (Q10)

| field | type | หมายเหตุ |
|---|---|---|
| `assignment` | FK → `Assignment`, `PROTECT` | (v1.3 — enforce กฎ §1 ที่ระดับ DB) |
| `student` | FK → `User`, `PROTECT` | (v1.3 — User ไม่ hard-delete) |
| `attempt_number` | int, default `1` | เพิ่มเมื่อส่งซ้ำ |
| `is_latest` | Bool | ใช้กรองงานล่าสุดเร็ว ๆ — บังคับ "True ได้ตัวเดียวต่อ (assignment, student)" ด้วย partial unique index `WHERE is_latest AND deleted_at IS NULL` ; soft-delete แถว latest → ต้อง promote แถวก่อนหน้าเป็น latest |
| `status` | Char choices: `draft` / `submitted` / `graded` / `returned` | |
| `submitted_at` | datetime, `null=True` | |
| `is_late` | Bool, default `False` | คำนวณตอน submit (`submitted_at > due_at`, เทียบใน `Asia/Bangkok`) — `False` เสมอถ้า `due_at` null |
| `days_late` | int, default `0` | คำนวณเป็น "วัน" ใน `Asia/Bangkok` |
| `text_response` | Text, blank | คำตอบพิมพ์ในระบบ |
| `raw_score` | Decimal, `null=True` | คะแนนก่อนหักสาย |
| `penalty_applied_percent` | Decimal, `null=True` | |
| `final_score` | Decimal, `null=True` | หลังหักสาย → ตัวนี้เข้า gradebook |
| `feedback` | Text, blank | |
| `graded_by` | FK → `User`, `SET_NULL`, `null=True` | |
| `graded_at` | datetime, `null=True` | |
| `deleted_at`, `deleted_by` | จาก `SoftDeleteModel` | ครูลบ submission ทิ้งได้ (soft) |
| — | UniqueConstraint | `(assignment, student, attempt_number)` `condition=Q(deleted_at__isnull=True)` |

### `SubmissionFile`

| field | type |
|---|---|
| `submission` | FK → `Submission`, `CASCADE` |
| `file_url`, `file_name`, `file_size`, `mime_type` | Cloudinary + metadata |

---

## 9. Grading (ถ่วงน้ำหนักตาม category)

> **ผลลัพธ์ที่ระบบออก**: คะแนน % ต่อ category + **weighted total (%)** — **ไม่มีเกรดตัวอักษร / GPA** ใน MVP

```
Course
  └── GradingCategory (weight %)         เช่น Quiz 20% / Assignment 30% / Final 50%
        └── GradeItem (max_score)        1 quiz / 1 assignment / คอลัมน์กรอกมือ
              └── Score (per student)    คะแนนดิบ + คะแนนปรับ (override)
```

### `GradingCategory`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `name` | Char | ชื่อหมวด เช่น `"Quiz"` |
| `weight_percent` | Decimal | เช่น `20.00` |
| `order` | int | |

> validate ว่าผลรวม `weight_percent` ต่อ course = 100 → **เตือน** ไม่ hard-block (ผู้สอนอาจตั้งค้างระหว่างทำ)
> **ลบ (v1.3)**: `GradeItem.category` → `PROTECT` — ลบหมวดที่ยังมี `GradeItem` อยู่ไม่ได้ ต้องย้าย item ไปหมวดอื่น (หรือปลด category) ก่อน

### `GradeItem`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `category` | FK → `GradingCategory`, **`PROTECT`**, `null=True` | `null` = ยังไม่จัดหมวด → **ไม่ถูกนับใน weighted_total** จนกว่าครูจะตั้งหมวด (v1.3) |
| `title` | Char | ชื่อคอลัมน์ |
| `max_score` | Decimal | |
| `source_type` | Char choices: `quiz` / `assignment` / `manual` | |
| `quiz` | FK → `Quiz`, **`PROTECT`**, `null=True` | ตั้งเมื่อ `source_type=quiz` — PROTECT: ลบ Quiz ที่มี GradeItem ไม่ได้ (v1.2 — A) |
| `assignment` | FK → `Assignment`, **`PROTECT`**, `null=True` | ตั้งเมื่อ `source_type=assignment` — PROTECT เช่นกัน |
| `weight_within_category` | Decimal, `null=True` | น้ำหนักในหมวด (null = ถ่วงตามสัดส่วน `max_score`) |
| `is_published` | Bool, default `False` | นักศึกษาเห็นคะแนนข้อนี้ไหม |
| `order` | int | |

> **การสร้าง (Q3 — auto)**: signal `post_save` ของ `Quiz` / `Assignment` ตอน `is_published` เปลี่ยนเป็น `True` **และ `is_graded=True`** → สร้าง `GradeItem` (`source_type` ตรงกับต้นทาง, `quiz`/`assignment` FK ตั้งให้, `max_score` copy มา, `category` = `grading_category` ของต้นทางถ้ามี). ผู้สอนย้าย category / แก้น้ำหนักได้ภายหลัง ; unpublish ไม่ลบ `GradeItem` (แค่ `is_published=False`) ; ถ้าครูเปลี่ยน `is_graded` เป็น `False` ทีหลัง → `GradeItem.is_published=False` (ไม่ลบ) ; คอลัมน์ `manual` ผู้สอนสร้างเอง

### `Score` — inherit `SoftDeleteModel` (Q10)

| field | type | หมายเหตุ |
|---|---|---|
| `grade_item` | FK → `GradeItem`, **`PROTECT`** | (v1.3) ลบ `GradeItem` ที่มี `Score` ไม่ได้ — ทำได้แค่ `is_published=False` (ซ่อน) |
| `student` | FK → `User`, **`PROTECT`** | (v1.3 — User ไม่ hard-delete) |
| `raw_score` | Decimal, `null=True` | มาจาก attempt/submission หรือกรอกมือ (ดูกลไก sync ล่าง) |
| `adjusted_score` | Decimal, `null=True` | override โดยผู้สอน (ถ้ามี ใช้ตัวนี้แทน) |
| `comment` | Text, blank | |
| `source_attempt` | FK → `QuizAttempt`, `SET_NULL`, `null=True` | ที่มาของคะแนน |
| `source_submission` | FK → `Submission`, `SET_NULL`, `null=True` | ที่มาของคะแนน |
| `updated_by` | FK → `User`, `SET_NULL`, `null=True` | |
| `deleted_at`, `deleted_by` | จาก `SoftDeleteModel` | ครูลบคะแนนช่องนี้ทิ้งได้ (soft) |
| — | UniqueConstraint | `(grade_item, student)` `condition=Q(deleted_at__isnull=True)` |

**กลไก sync คะแนน → `Score` (v1.3):**
- **Quiz**: เมื่อ `QuizAttempt.status` → `submitted`/`auto_submitted`/`graded` และตรวจครบ → signal เขียน/อัปเดต `Score` ของ `GradeItem` ที่ผูกกับ quiz นั้น. `attempt_policy=single` → ใช้ attempt เดียว ; `multiple_highest` → ใช้ **attempt ที่ `score` สูงสุดในบรรดา attempt ที่ตรวจเสร็จ** (`source_attempt` ชี้ไป attempt นั้น)
- **Assignment**: เมื่อ `Submission.status` → `graded` → signal เขียน/อัปเดต `Score` ด้วย `Submission.final_score` (`source_submission` ชี้ไป submission ล่าสุดที่ graded)
- ครู override ได้ที่ `adjusted_score` เสมอ — sync ไม่ทับ `adjusted_score`

### `CourseGrade` (cache — บังคับมี, Q9)

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `student` | FK → `User`, `CASCADE` | |
| `weighted_total_percent` | Decimal | ผลลัพธ์สุดท้าย |
| `breakdown` | JSON | คะแนน % แยกตาม category (สำหรับแสดง/ export) |
| `computed_at` | datetime | |
| — | unique_together | `(course, student)` |

> **Q9 (ปรับ v1.3)**: **source of truth = คำนวณสดจากสูตรล่าง** — `CourseGrade` เป็น cache ที่ refresh ได้เสมอ ไม่ใช่ค่าที่เชื่อถือเดี่ยว ๆ. API คะแนนคำนวณสดได้ถ้า cache หมดอายุ/หาย
> **invalidate + recompute** เมื่อสิ่งเหล่านี้เปลี่ยน (นศ. คนนั้น + คอร์สนั้น): `Score` (raw/adjusted/soft-delete), `GradeItem` (`is_published` / `max_score` / `weight_within_category` / `category` / สร้าง / ลบ), `GradingCategory` (`weight_percent` / สร้าง / ลบ), `Enrollment` (enroll ใหม่ = สร้าง row, drop = คงไว้). งานหนัก/bulk → background job

**สูตร weighted total (v1.2):**

1. คะแนนของแต่ละ `GradeItem` ที่ `is_published` สำหรับ นศ. คนหนึ่ง:
   `s(item)`  = `Score.adjusted_score` ถ้ามี, ไม่งั้น `Score.raw_score`, **ไม่งั้น 0** (ไม่มี Score / ยังไม่ทำ = 0 — ข้อ 1 [B])
   `m(item)`  = `GradeItem.max_score`

2. `%` ของแต่ละหมวด `c`:
   - ถ้ามี item ใน `c` ตั้ง `weight_within_category` (`w_i`):
     `category_pct(c) = Σ [ (s_i / m_i) × w_i ] / Σ w_i`
   - ไม่งั้น (ถ่วงตามสัดส่วน `max_score`):
     `category_pct(c) = Σ s_i / Σ m_i`
   - หมวดที่ไม่มี published item เลย → `category_pct(c) = 0`
   - `GradeItem` ที่ `category = NULL` (ยังไม่จัดหมวด) → **ไม่นับ** ในหมวดใดเลย

3. คะแนนรวม:
   `weighted_total = Σ [ category_pct(c) × weight_percent(c) / 100 ]`   ทุกหมวด

**หมายเหตุ:**
- ผลรวม `weight_percent` **ไม่บังคับ = 100** — ถ้าไม่ครบ `weighted_total` ก็ออกมา < หรือ > ตามจริง (ข้อ 2 [B]) แสดงพร้อมป้ายเตือน ไม่ normalize
- **ผลข้างเคียงของ "นับข้อที่ไม่ทำ = 0"**: วินาทีที่ครู `is_published=True` ที่ `GradeItem` → นศ. ทุกคนที่ยังไม่ได้ทำเห็นเกรดตกทันที → **แนะนำครู publish `GradeItem` หลังปิด quiz/assignment แล้ว**
- `breakdown` JSON เก็บ `category_pct(c)` ราย c + คะแนนรวม เพื่อแสดง/export

---

## 10. Announcements / Notifications / Audit

### `Announcement`

| field | type | หมายเหตุ |
|---|---|---|
| `course` | FK → `Course`, `CASCADE` | |
| `author` | FK → `User`, `SET_NULL`, `null=True` | |
| `title` | Char | หัวข้อ |
| `body` | Text | rich text |
| `is_pinned` | Bool, default `False` | |
| `is_published` | Bool, default `False` | |
| `published_at` | datetime, `null=True` | |

### `AnnouncementRead` (สถานะอ่าน/ยังไม่อ่าน ต่อผู้ใช้)

| field | type |
|---|---|
| `announcement` | FK → `Announcement`, `CASCADE` |
| `user` | FK → `User`, `CASCADE` |
| `read_at` | datetime |
| — unique_together | `(announcement, user)` |

> MVP ส่ง **in-app อย่างเดียว** — ไม่มี email/push การแจ้งเตือน = query announcement ในคอร์สที่ยังไม่มี `AnnouncementRead`

### `Notification` (แจ้งเตือนรายบุคคลจาก event ของระบบ — web ล้วน)

> ต่างจาก `Announcement`: อันนี้ระบบสร้างเอง 1 แถว/ผู้รับ 1 คน trigger จาก event (ตรวจงานเสร็จ, publish assignment/quiz, ใกล้ครบกำหนด, ถูก enroll)
> **MVP = ไม่มีการส่งออกนอก** (ไม่มี email/push/LINE) — เก็บแถวไว้ให้ frontend ดึงไปแสดงกระดิ่ง 🔔 + นับที่ยังไม่อ่าน
> การส่งออกช่องทางอื่นในอนาคต = เพิ่ม delivery layer ที่อ่านจากตารางนี้ **ไม่ต้องแก้ schema**

| field | type | หมายเหตุ |
|---|---|---|
| `recipient` | FK → `User`, `CASCADE` | ผู้รับ |
| `notification_type` | Char choices: `submission_graded` / `quiz_graded` / `assignment_published` / `quiz_published` / `announcement_posted` / `due_soon` / `enrolled` | ชนิด event (เพิ่มได้ภายหลัง) — `due_soon` คงไว้ใน choices แต่ **MVP ไม่สร้างแถว** (คำนวณสดตอนเปิดแอปแทน, v1.4) |
| `context` | JSON | พารามิเตอร์สำหรับ render ข้อความ เช่น `{"course_name": "...", "item_title": "...", "score": 8}` — frontend ประกอบข้อความจาก translation key ตาม `notification_type` (i18n ไม่ต้องเก็บ `_th/_en`) |
| `link_url` | Char | path ใน SPA ที่กดแล้วไป เช่น `/courses/12/assignments/5` |
| `is_read` | Bool, default `False` | |
| `read_at` | datetime, `null=True` | |
| `created_at` | datetime, **db_index** | เรียงตามเวลา + query "ยังไม่อ่าน" |

> ดัชนี: `(recipient, is_read)` และ `(recipient, created_at)` — ไม่ inherit `Auditable` (ปริมาณเยอะ + เป็น derived data)

### `AuditLog`

| field | type | หมายเหตุ |
|---|---|---|
| `actor` | FK → `User`, `SET_NULL`, `null=True` | null = ระบบ |
| `impersonated_by` | FK → `User`, `SET_NULL`, `null=True` | Admin ตัวจริงเบื้องหลัง (ถ้าอยู่ในโหมด impersonation) |
| `action` | Char choices: `create` / `update` / `delete` / `login` / `logout` / `impersonate_start` / `impersonate_end` / `publish` / `enroll` / `unenroll` / `regrade` | (v1.2: ตัด `grade` / `submit` ออก — ดูกลไก ; เพิ่ม `regrade`) |
| `content_type` | FK → `ContentType`, `null=True` | target model |
| `object_id` | Char, `null=True` | pk ของ target (string) |
| `object_repr` | Char | snapshot ข้อความอ่านออก |
| `changes` | JSON, `null=True` | `{"field": [old, new]}` สำหรับ update |
| `context` | JSON, `null=True` | IP, user-agent, request path ฯลฯ |
| `created_at` | datetime, **db_index** | |
| — | index | **`(content_type, object_id)`** — query "ประวัติทั้งหมดของ object นี้" (v1.2) |

**กลไก (v1.2 — กันเขียนซ้ำ, ข้อ H):**
- **`Auditable` signal** รับงาน CRUD ทั้งหมด: domain model inherit `Auditable` → `post_save` / `post_delete` เขียน `AuditLog` อัตโนมัติ (create/update/delete + field diff). **การให้คะแนน = save `Score`, การส่งงาน = save `Submission` → signal จับให้แล้ว ไม่ต้องเรียกซ้ำ**
- **`log_action(...)`** เรียกเองเฉพาะสิ่งที่ signal จับไม่ได้:
  - ไม่มี model save: `login` / `logout` / `impersonate_start` / `impersonate_end`
  - 1 การกระทำ → กระทบหลายแถว: `publish` (สร้าง GradeItem + Notification พร้อมกัน), `enroll` / `unenroll` (batch), `regrade` (recompute หลาย attempt)
- ไม่ audit: infra / derived model (session, token, `AuditLog`, `AnnouncementRead`, `Notification`, `CourseGrade`, cache)

---

## 11. บันทึกการตัดสินใจ (freeze 2026-09-09)

| # | ประเด็น | ✅ สรุป |
|---|---|---|
| 1 | ขอบเขต `_th` / `_en` | **ไม่แยกเลย — field เดียวทั้งระบบ** (revised v1.1 2026-09-09). i18n = UI chrome เท่านั้น (ปุ่ม/ป้าย/ข้อความระบบ) ; user-generated content พิมพ์ภาษาใดก็ได้ |
| 2 | Quiz ผูกกับอะไร | `course` บังคับ + `module` ไม่บังคับ |
| 3 | สร้าง `GradeItem` | อัตโนมัติผ่าน signal ตอน Quiz/Assignment `is_published → True` **และ `is_graded=True`** |
| 4 | `dropdown` | เลือก 1 ตัวจาก list (โครงเหมือน MCQ, ต่างที่ UI render `<select>`) |
| 5 | ตรวจ `short_answer` | flag `manual_grading` ต่อข้อ: auto (เทียบ `accepted_answers` แบบ normalize) หรือ manual (ครูให้คะแนน) |
| 6 | PK | `BigAutoField` (int) ทุกตาราง — ไม่มี UUID |
| 7 | `Enrollment` เมื่อ Admin เพิ่มรายชื่อ | `status=active` ทันที (คง `invited` ไว้ใน choices เผื่ออนาคต) |
| 8 | น้ำหนักภายใน category | ถ่วงตามสัดส่วน `max_score` (`weight_within_category` null); ตั้งค่ารายข้อได้ |
| 9 | `CourseGrade` cache | บังคับมี + recompute ผ่าน signal ของ `Score` |
| 10 | Soft delete | `SoftDeleteModel` (`deleted_at`, `deleted_by`) กับ `Submission`, `QuizAttempt`, `Score` เท่านั้น |
| + | `Notification` model | เพิ่มใหม่ — แจ้งเตือนรายบุคคลจาก event, **web ล้วน** ไม่มีส่งออกนอกใน MVP (ดู §10) |

### รีวิว v1.2 (2026-09-09)

| ประเด็น | ✅ สรุป |
|---|---|
| A — เส้นแบ่ง hard-delete | hard-delete จริงเฉพาะ draft ที่ไม่เคย publish + ไม่มีข้อมูล นศ. ; `GradeItem.quiz/assignment` → `PROTECT` ; soft-delete ใช้ conditional `UniqueConstraint` |
| B — สูตร weighted total | ข้อที่ไม่ทำ = **0** ; weight ไม่ครบ 100 → แสดงตามจริง (ดู §9 สูตรใหม่) |
| C — แก้ quiz หลังมีคนทำ | ล็อกแก้เชิงโครงสร้างเมื่อมี `QuizAttempt` ; มี action `regrade` |
| E — 1 บัญชี หลายบทบาทในวิชา | `User.role` = สิทธิ์ระดับระบบ ; TA/นักเรียนดูต่อวิชาจาก `CourseTeacher`/`Enrollment` |
| F — Assignment ไม่มี deadline | `due_at` nullable |
| G — เส้นตายเด็ดขาด | เพิ่ม `Assignment.accept_until` |
| H — AuditLog | `Auditable` signal จับ CRUD ; `log_action` เฉพาะ auth + multi-row ; ตัด `grade`/`submit` ; เพิ่ม index `(content_type, object_id)` |
| is_graded | เพิ่ม `Quiz.is_graded` + `Assignment.is_graded` (default `True`) |
| ข้ามข้อใน quiz | สร้าง `Answer` เปล่า (0 คะแนน) ตอน submit |
| Decimal | มาตรฐาน `7,2` (คะแนน) / `5,2` (เปอร์เซ็นต์) |

### รีวิว v1.3 (2026-09-09 — รอบ 2)

| ประเด็น | ✅ สรุป |
|---|---|
| A — ลบ User | **ห้าม hard-delete** User ที่มีประวัติ (ปิด `is_active=False`) ; `Submission/QuizAttempt/Score.student` → `PROTECT` |
| B — ลบ `GradeItem` | `Score.grade_item` → `PROTECT` — ลบไม่ได้ถ้ามีคะแนน (ซ่อนด้วย `is_published=False`) |
| C — `matching` | ให้คะแนนบางส่วน: `points × (คู่ถูก / คู่ทั้งหมด)` |
| D — ลบ `GradingCategory` | `GradeItem.category` → `PROTECT` — ย้าย item ออกก่อน ; item ที่ `category=NULL` ไม่นับในเกรดรวม |
| sync คะแนน | signal: `QuizAttempt`/`Submission` graded → เขียน `Score` (`multiple_highest` = attempt สูงสุด) ; ไม่ทับ `adjusted_score` |
| timed quiz | `QuizAttempt.due_at = min(started_at + limit, Quiz.available_until)` |
| CourseGrade | เป็น cache ; source of truth = คำนวณสด ; รายการ invalidate ครบขึ้น |
| FK hardening | `QuizAttempt.quiz` / `Submission.assignment` → `PROTECT` |

### รีวิว v1.4 (ตามการตัดสินใจของผู้ใช้)

| ประเด็น | ✅ สรุป |
|---|---|
| โทเคนยืนยันอีเมล/ตั้งรหัสผ่าน | เก็บ **SHA-256 ของโทเคน** (`token_hash`) แทนตัวโทเคนจริง — ฐานข้อมูลรั่วก็ใช้ลิงก์ไม่ได้ |
| อีเมล | เก็บตัวพิมพ์เล็กเสมอ ห้ามซ้ำแบบไม่สนตัวพิมพ์ |
| รหัสนักศึกษา/พนักงาน | ตัดช่องว่างหัวท้าย **แยกตัวพิมพ์** ห้ามมี `@` ไม่มีรหัส = `NULL` |
| บัญชีที่ Admin สร้าง | `is_email_verified=True` ตั้งแต่สร้าง (คงตาม W2) แต่ยังไม่มีรหัสผ่านจนกว่าเจ้าของกดลิงก์ตั้งรหัสผ่าน |
| รหัสเข้าเรียน | 8 ตัวอักษร ตัดตัวที่สับสน แสดงเป็น `XXXX-XXXX` กรอกแบบไม่สนตัวพิมพ์ |
| ส่งควิซอัตโนมัติเมื่อหมดเวลา | ใช้ **ตัวตั้งเวลา** (คำสั่งที่รันซ้ำได้อย่างปลอดภัย) + ตรวจตอนมีคนเข้าถึงเป็นตาข่ายรอง — ไม่กระทบ schema |
| แจ้งเตือน `due_soon` | คำนวณสดตอนเปิดแอป ไม่สร้างแถว `Notification` ล่วงหน้า (ตัด `due_soon` ออกจาก MVP) — ไม่กระทบ schema |
| อายุโทเคน / สิทธิ์ | access 15 นาที, refresh 7 วัน (หมุนเวียน + blacklist); role ใน token ใช้แสดงเมนู ส่วนสิทธิ์จริง backend ตรวจจาก DB ทุกครั้ง |

**ปรับภายหลังได้** (migration ปกติ): field ใด ๆ, ตารางใหม่, choice เพิ่ม
**ปรับยาก / เลี่ยง**: เปลี่ยน cardinality ของ FK, เปลี่ยนชนิด PK (Q6 = ถาวร)

### Index ที่ต้องเพิ่มตอน implement (ไม่กระทบ schema freeze)

`Enrollment(student, status)` · `Enrollment(course, status)` · `Content(module, order)` · `Module(course, order)` · `Submission(assignment, is_latest)` · `QuizAttempt(quiz, student)` · `Notification(recipient, is_read)` · `AuditLog(content_type, object_id)` · `Score(grade_item)` — Django สร้าง index ให้ FK เดี่ยวอยู่แล้ว ที่ list นี้คือ composite

---

## 12. ERD

ดูไฟล์ [`database-erd.md`](./database-erd.md) (diagram Mermaid แยกตามโดเมน) หรือหน้า Artifact ที่แนบให้

---

## 13. สิ่งที่ตั้งใจ "ไม่ทำ" ใน MVP (retrofit ได้)

| ฟีเจอร์ | วิธีเพิ่มทีหลัง | ต้นทุน |
|---|---|---|
| **Content progress tracking** (ดูบทเรียนแล้ว/ยัง, progress bar) | ตารางใหม่ `ContentProgress(content, student, first_viewed_at, completed_at)` — ไม่แตะตารางเดิม, ไม่ต้อง backfill | 🟢 ต่ำ |
| **การผ่อนผันรายคน** (นศ. บางคนได้เวลา/attempt เพิ่ม, ขยาย deadline) | ตารางใหม่ `QuizException(quiz, student, extra_time_minutes, extra_attempts, available_until_override)` — เช็คตอน นศ. เริ่มทำ | 🟢 ต่ำ |
| **งานกลุ่ม (group assignment)** | ตารางใหม่ `AssignmentGroup` + `AssignmentGroupMember` ; `Submission` เพิ่ม FK `group` (nullable) ; logic กระจายคะแนนกลุ่ม → สมาชิก | 🟡 กลาง (แตะ `Submission` + `Score` แต่ไม่แตะ core ที่ freeze) |
| **เกรดตัวอักษร / GPA** | ตาราง `GradeScale` + mapping `%` → เกรด ต่อวิชา ; อ่านจาก `CourseGrade.weighted_total_percent` | 🟡 กลาง |
| **Bulk import ผู้ใช้ (CSV)** | ไม่ต้องแก้ schema — เป็น endpoint + parser | 🟢 ต่ำ |
| **ส่ง Notification ออกนอก (email/push)** | delivery layer อ่านจาก `Notification` ที่มีอยู่ | 🟢 ต่ำ |
