# คู่มือการใช้งานฐานข้อมูล — LMS (v1.4)

> เอกสารนี้ตอบว่า **แต่ละตารางใช้ทำอะไร ใครเขียน ใครอ่าน เชื่อมกับอะไร และ workflow ครบวงจรเป็นยังไง**
> ใช้คู่กับ:
> - [`database.md`](./database.md) — สเปกเต็ม (field, type, constraint, ความสัมพันธ์)
> - [`database-erd.md`](./database-erd.md) — ERD (Mermaid)
> - [`database-fields.md`](./database-fields.md) — คำอธิบายสั้นราย field
>
> สำหรับ session/คนที่เพิ่งเข้ามา: **อ่าน `CLAUDE.md` ก่อน** (บริบทโปรเจกต์ + tech stack + สิทธิ์ตาม role) แล้วค่อยอ่านไฟล์นี้

---

## 0. สถาปัตยกรรมโดยรวม (ต้องเข้าใจก่อน)

- **Backend**: Django 5.2 + DRF, PostgreSQL. **Frontend**: React + Vite + TS (SPA เรียก `/api` ผ่าน proxy จึงเป็น origin เดียวกับหน้าเว็บ). Auth = JWT (ดู `docs/api-auth.md`).
- **ทิศทางข้อมูล**: frontend เรียก REST API → DRF serializer/viewset → service layer → model. **ไม่มี** business logic ใน frontend.
- **3 กลไกอัตโนมัติที่ต้องรู้**:
  1. **`Auditable` signal** — ทุก model ที่ inherit `Auditable` เขียน `AuditLog` อัตโนมัติทุกครั้งที่ save/delete
  2. **`SoftDeleteModel`** — `Submission`/`QuizAttempt`/`Score` : `.delete()` = ตั้ง `deleted_at` ไม่ลบจริง ; manager `objects` ซ่อนแถวที่ลบ
  3. **signal sync คะแนน** — `QuizAttempt`/`Submission` ที่ `graded` → เขียน `Score` → เขียน/invalidate `CourseGrade`
- **Timezone**: เก็บ UTC, แสดง/คำนวณ "วัน" ใน `Asia/Bangkok`
- **ภาษา**: field เดียว (ไม่แยก `_th/_en`) ; i18n = UI chrome ฝั่ง frontend

### role ระดับระบบ vs ระดับรายวิชา (สำคัญมาก)

| | เก็บที่ | ตอบคำถาม |
|---|---|---|
| **ระดับระบบ** | `User.role` (`admin`/`teacher`/`student`) | เข้า Admin panel ได้ไหม, สร้างรายวิชาได้ไหม, เห็น AuditLog ไหม |
| **ระดับรายวิชา** | `CourseTeacher` (owner/co_teacher/ta) + `Enrollment` (student) | จัดการวิชา X ได้ไหม, เห็นคะแนนวิชา X ไหม, ส่งงานวิชา X ได้ไหม |

→ 1 คน `role=student` เป็น TA วิชา A ได้ + เรียนวิชา B ได้ พร้อมกัน. **permission check ทำต่อวิชาเสมอ** โดยดู 2 ตารางล่าง ไม่ใช่ดูแค่ `User.role`

### gradebook pipeline (ภาพรวม)

```
Quiz/Assignment  --publish (is_graded)-->  GradeItem  --(นศ.ทำ+ตรวจ)-->  Score  --signal-->  CourseGrade (cache)
     (ครูสร้าง)         signal สร้างให้         (1 คอลัมน์)     signal เขียน       (1 แถว/นศ./วิชา)
```

---

## 1. คำอธิบายราย table

รูปแบบ: **หน้าที่ · ใครเขียน · ใครอ่าน · lifecycle/invariant · เชื่อมกับ**

---

### 📁 accounts

#### `User`
- **หน้าที่**: บัญชีผู้ใช้ทุกคนในระบบ (admin/teacher/student) — 1 ตารางรวมทุก role
- **เขียนโดย**:
  - self-register endpoint → สร้างแถว `role=student`, `is_email_verified=False`, `created_by=NULL`
  - Admin (user management) → สร้างครู/นักศึกษา, ตั้ง `student_or_staff_id`, `created_by=<admin>`
  - Admin → แก้ `role` (เลื่อนขั้น), `is_active` (ปิดบัญชี)
  - ตัวผู้ใช้เอง → แก้ `first_name`/`last_name`/`avatar_url` ในหน้า profile
- **อ่านโดย**: auth (login), JWT serializer (ใส่ `role` ลง token claims), ทุก serializer ที่แสดงชื่อคน, permission layer
- **lifecycle**: สร้าง → (ยืนยันอีเมลถ้า self-register) → ใช้งาน → `is_active=False` เมื่อเลิกใช้. **ไม่ hard-delete ถ้ามีประวัติเรียน/สอน**
- **invariant** (บังคับใน app): self-register บังคับ `role=student` ; `teacher`/`admin` ตั้งได้โดย Admin เท่านั้น + เขียน AuditLog
- **เชื่อมกับ**: แทบทุกตาราง (FK `created_by`, `student`, `author`, `actor`, `graded_by`, `updated_by`, …)
- **field ที่ต้องเข้าใจ**:
  - `email` (unique, บังคับ) — login ได้ ; `student_or_staff_id` (unique, nullable) — login ได้เหมือนกัน. นศ.สมัครเองยังไม่มีรหัส
  - `first_name_en`/`last_name_en` — ชื่ออังกฤษของ**บุคคล** (สำหรับเอกสารทางการ) ไม่ใช่การแปล field
  - `is_staff`/`is_superuser` — Django admin เท่านั้น คนละเรื่องกับ `role`

#### `EmailVerificationToken`
- **หน้าที่**: โทเคนแบบใช้ครั้งเดียวสำหรับ (1) ยืนยันอีเมลตอนสมัคร (2) ตั้ง/รีเซ็ตรหัสผ่าน (รวมบัญชีที่ Admin สร้างให้) — เก็บเฉพาะค่าแฮช `token_hash` ตัวโทเคนจริงมีแค่ในลิงก์ที่ส่งทางอีเมล
- **เขียนโดย**: register endpoint, "resend verification", "forgot password" endpoint
- **อ่านโดย**: verify endpoint (`GET /verify?token=…`), reset-password endpoint
- **lifecycle**: สร้าง (มี `expires_at`) → ผู้ใช้กดลิงก์ → ตั้ง `used_at` → ใช้ซ้ำไม่ได้. โทเคนหมดอายุ/ใช้แล้ว = cleanup job ลบทีหลัง
- **invariant**: 1 โทเคนใช้ได้ครั้งเดียว ; `verify_email` อายุ ~24 ชม., `reset_password` ~1 ชม.

---

### 📁 academics

#### `Term`
- **หน้าที่**: ภาคเรียน/ปีการศึกษา (เช่น "1/2568") — ทุก `Course` ต้องผูกกับ Term
- **เขียนโดย**: Admin (ตั้งเทอมใหม่ต้นภาค, ตั้ง `is_current`)
- **อ่านโดย**: course list (กรองตามเทอม), dashboard (เทอมปัจจุบัน)
- **invariant**: `is_current=True` มีได้แถวเดียว (partial unique index) ; `(academic_year, semester)` unique
- **เชื่อมกับ**: `Course` (1:หลาย, `PROTECT` — ลบเทอมที่มีวิชาไม่ได้)

#### `Course`
- **หน้าที่**: รายวิชา 1 ตัวใน 1 เทอม. วิชาเดิมเปิดใหม่คนละเทอม = คนละแถว (แยกนักศึกษา/คะแนน)
- **เขียนโดย**: teacher/admin (สร้าง, แก้ชื่อ/คำอธิบาย, เปิด self-enroll → generate `invite_code`, กด publish)
- **อ่านโดย**: course list, ทุกหน้าในวิชา, permission layer (เช็คว่าวิชา published ไหมก่อนให้ นศ.เข้า)
- **lifecycle**: draft (`is_published=False`) → published → (จบเทอม, ยังอยู่ในระบบ ไม่มี archive แยก)
- **invariant**: `(term, code, section)` unique ; `section` ว่าง = `""` ไม่ใช่ null
- **field**: `self_enroll_enabled` + `invite_code` ใช้คู่กัน — เปิด self-enroll ถึง generate code ; `is_published` = นศ.เห็น/เข้าได้
- **เชื่อมกับ**: `Term` (แม่), `CourseTeacher`/`Enrollment`/`Module`/`Assignment`/`Quiz`/`GradingCategory`/`GradeItem`/`Announcement`/`CourseGrade` (ลูก ทั้งหมด CASCADE ยกเว้นที่มีข้อมูล นศ.)

#### `CourseTeacher` (ตารางกลาง Course ↔ User)
- **หน้าที่**: ครูที่สอนวิชานี้ + บทบาทในวิชา (owner/co_teacher/ta)
- **เขียนโดย**: owner/co_teacher/admin (เพิ่ม-ลบครู, ตั้ง `course_role`) → `added_by` บันทึกคนเพิ่ม
- **อ่านโดย**: permission layer (ทุก request ในวิชา), หน้า "ทีมผู้สอน"
- **invariant** (app): ทุกวิชาต้องมี `owner` ≥ 1 — ลบ/เปลี่ยน owner คนสุดท้ายไม่ได้ถ้าไม่ตั้งคนใหม่ก่อน ; `(course, user)` unique
- **สิทธิ์** *(provisional — สรุปแน่นอนตอนทำฟีเจอร์ permission)*: `owner`+`co_teacher` = จัดการวิชาได้เต็ม ; `ta` = ค่าเริ่มต้นตรวจงาน+ดูคะแนน แก้โครงสร้างวิชาไม่ได้

---

### 📁 content

#### `Module`
- **หน้าที่**: บทเรียน — กล่องจัดกลุ่ม `Content` ในวิชา
- **เขียนโดย**: teacher/co_teacher (สร้าง, แก้ชื่อ, จัดลำดับผ่าน `order`, publish)
- **อ่านโดย**: หน้าเนื้อหาวิชา (ทั้งฝั่งครูและ นศ. — นศ.เห็นเฉพาะ `is_published=True`)
- **เชื่อมกับ**: `Course` (แม่, CASCADE), `Content`/`Quiz`/`Assignment` (ลูก — Quiz/Assignment ใช้ SET_NULL/nullable เพราะผูก module ไม่บังคับ)

#### `Content`
- **หน้าที่**: เนื้อหาย่อย 1 ชิ้น — ข้อความ / ไฟล์ / รูป / วิดีโอ / เสียง / ลิงก์ (`content_type` เป็น discriminator)
- **เขียนโดย**: teacher/co_teacher (สร้าง, อัปโหลดไฟล์ → เก็บ URL Cloudinary, ตั้ง `available_from`, publish)
- **อ่านโดย**: หน้าเรียนของ นศ. (กรอง `is_published` + `available_from <= now`)
- **field ตามชนิด**:
  - `text` → ใช้ `body` (rich text)
  - `file`/`image`/`audio` → ใช้ `file_url` + `file_name`/`file_size`/`mime_type`
  - `video` → ใช้ `video_source` (`cloudinary`/`youtube`) + `video_url`
  - `link` → ใช้ `external_url`
- **invariant**: 1 Content = 1 ไฟล์หลัก. อยากได้หลายไฟล์ → สร้างหลาย Content
- **ยังไม่ทำ**: การติดตามว่า นศ.ดูแล้ว/ยัง → ตาราง `ContentProgress` ในอนาคต (ดู §13 ของ database.md)

---

### 📁 enrollment

#### `Enrollment` (ตารางกลาง Course ↔ User)
- **หน้าที่**: นักศึกษา 1 คน ลงทะเบียนวิชา 1 ตัว + สถานะ + วิธีลง
- **เขียนโดย**:
  - teacher/admin (เพิ่มรายชื่อ) → `status=active`, `method=admin_assigned`, `enrolled_by=<คนเพิ่ม>`
  - นศ. (กรอก `Course.invite_code`) → `status=active`, `method=self_enrolled`, `enrolled_by=NULL`
  - teacher/admin หรือ นศ. (ถอน) → `status=dropped`, ตั้ง `dropped_at`
- **อ่านโดย**: permission layer (นศ.คนนี้เรียนวิชานี้ไหม), course roster, gradebook (รายชื่อ นศ.), dashboard นศ. (วิชาที่เรียน)
- **lifecycle**: `active` ←→ `dropped` ; `completed` ตั้งตอนจบเทอม (manual หรือ job)
- **invariant**: `(course, student)` unique — นศ.ลงวิชาเดิมซ้ำไม่ได้ (ถ้าถอนแล้วกลับมา = อัปเดตแถวเดิมเป็น `active`)
- **หมายเหตุ**: `status=invited` มีใน choices แต่ยังไม่ใช้ใน MVP (เผื่อ flow อนุมัติก่อนเข้า)

---

### 📁 assessments (Quiz)

#### `Quiz`
- **หน้าที่**: แบบทดสอบ/แบบฝึกหัด 1 ชุด + การตั้งค่าการทำ (จับเวลา, จำนวนครั้ง, เฉลย)
- **เขียนโดย**: teacher/co_teacher (สร้าง, ตั้งค่า, publish) ; TA *(provisional)*
- **อ่านโดย**: หน้าทำ quiz (นศ.), หน้าจัดการ quiz (ครู), signal สร้าง GradeItem
- **lifecycle**: draft → **publish** (ถ้า `is_graded=True` → signal สร้าง `GradeItem`) → มีคนทำ (`QuizAttempt` เกิด) → **ล็อกแก้เชิงโครงสร้าง** → ครูตรวจข้อ manual → ปิด (`available_until` ผ่าน)
- **field สำคัญ**:
  - `is_graded` — `False` = ฝึกหัด ไม่สร้าง GradeItem ไม่เข้าเกรดรวม (นศ.ยังเห็นคะแนนตัวเอง)
  - `attempt_policy` — `single` / `multiple_highest` (+ `max_attempts`) ; ตอน sync คะแนน `multiple_highest` เอา attempt คะแนนสูงสุด
  - `is_timed` + `time_limit_minutes` → ตอน นศ.เริ่ม เก็บ `QuizAttempt.due_at = min(started_at + limit, available_until)`
  - `show_correct_answers` — `never`/`after_submit`/`after_close` คุมว่าจะโชว์เฉลยเมื่อไหร่
- **invariant**: `max_score` = Σ `Question.points` (คำนวณใหม่เมื่อแก้คำถาม — แต่แก้คะแนนถูกล็อกเมื่อมี attempt)
- **การลบ**: มี GradeItem → ลบไม่ได้ (`GradeItem.quiz` = PROTECT) ; ทำได้แค่ unpublish

#### `Question`
- **หน้าที่**: คำถาม 1 ข้อ + ชนิด (`question_type`) — 5 ชนิด
- **เขียนโดย**: teacher/co_teacher (ตอน quiz ยังไม่มี attempt) ; ห้ามแก้ `points`/ลบ/เพิ่ม เมื่อมี attempt (ยกเว้น action `regrade`)
- **อ่านโดย**: หน้าทำ quiz, auto-grader, หน้าแก้ quiz
- **field ตามชนิด**:
  - `mcq`/`true_false`/`dropdown` → มี `Choice` ลูก
  - `matching` → มี `MatchingPair` ลูก
  - `short_answer` → `accepted_answers` (JSON list, สำหรับ auto) + `manual_grading` (bool)
- **เชื่อมกับ**: `Answer.question` = **PROTECT** (มีคำตอบแล้วลบคำถามไม่ได้)

#### `Choice`
- **หน้าที่**: ตัวเลือก 1 ตัว (mcq/true_false/dropdown) + ธง `is_correct`
- **เขียนโดย**: teacher (ตอนแก้ได้)
- **อ่านโดย**: หน้าทำ quiz (ซ่อน `is_correct`), auto-grader (ใช้ `is_correct`)
- **invariant**: mcq/dropdown ถูกได้ตัวเดียว (MVP) ; true_false = 2 แถว

#### `MatchingPair`
- **หน้าที่**: คู่ที่ถูกต้อง 1 คู่ (`left_text` ↔ `right_text`) สำหรับข้อจับคู่
- **อ่านโดย**: หน้าทำ quiz (สับ `right_text` ทุกคู่เป็นตัวเลือก), auto-grader
- **การให้คะแนน**: **บางส่วน** — `points_awarded = Question.points × (คู่ถูก / คู่ทั้งหมด)` ปัด 2 ตำแหน่ง

#### `QuizAttempt` · *soft delete*
- **หน้าที่**: การเข้าทำ quiz 1 ครั้งของ นศ. 1 คน + สถานะ + คะแนนรวม
- **เขียนโดย**:
  - นศ. กด "เริ่มทำ" → สร้างแถว `status=in_progress`, `started_at`=server now, `due_at`=snapshot, `max_score`=snapshot
  - นศ. กด submit หรือหมดเวลา → `status=submitted`/`auto_submitted`, `submitted_at`
  - auto-grader → คำนวณ `score` ของข้อ auto ; ถ้าไม่มีข้อ manual → `status=graded`
  - ครู (ตรวจข้อ manual) → เติม `Answer.points_awarded` ครบ → `status=graded`, `graded_by`, `graded_at`
  - ครู (ลบ) → soft delete
- **อ่านโดย**: หน้าผลของ นศ., signal sync → `Score`, รายงานของครู
- **lifecycle**: `in_progress → submitted|auto_submitted → graded`
- **invariant**: `(quiz, student, attempt_number)` unique **เฉพาะแถวที่ยังไม่ลบ** ; attempt_number ไม่ reuse หลัง soft-delete
- **timed enforcement**: ทุก save คำตอบ/submit → เช็ค `now() <= due_at` ; เลย → ปฏิเสธ + auto-submit
- **เชื่อมกับ**: `quiz`/`student` = **PROTECT**

#### `Answer`
- **หน้าที่**: คำตอบ 1 ข้อ ต่อ 1 คำถาม ต่อ 1 attempt — canonical store คือ `response` (JSON)
- **เขียนโดย**:
  - นศ. (ตอบ/แก้คำตอบระหว่างทำ) → `response`, `selected_choice` (denorm)
  - ตอน submit → สร้างแถวให้ครบทุก Question ที่ยังไม่มี (ข้ามข้อ = `response` ว่าง, `is_correct=False`, `points_awarded=0`)
  - auto-grader → `is_correct`, `points_awarded`
  - ครู (ข้อ manual) → `points_awarded`, `feedback`, `graded_by`, `graded_at`
- **อ่านโดย**: auto-grader, หน้าทบทวนของ นศ., **รายงานวิเคราะห์ข้อสอบ** (ใช้ `selected_choice`)
- **field**:
  - `response` — รูปแบบตามชนิด: `{"choice_id": N}` / `{"pairs": {left_id: right_id}}` / `{"text": "…"}` → **ใช้ตรวจคะแนน**
  - `selected_choice` — denormalize เฉพาะ mcq/tf/dropdown → **ใช้ทำรายงาน** ไม่ใช่ตรวจคะแนน
  - `is_correct=NULL` = ยังไม่ตรวจ / รอครู
- **invariant**: `(attempt, question)` unique. `Answer` ไม่เป็น soft-delete → ถ้า attempt ถูก soft-delete ต้อง filter `attempt__deleted_at__isnull=True`

---

### 📁 assignments

#### `Assignment`
- **หน้าที่**: งานที่มอบหมาย + กติกาส่ง (deadline, late policy, ชนิด/ขนาดไฟล์)
- **เขียนโดย**: teacher/co_teacher (สร้าง, ตั้งกติกา, publish)
- **อ่านโดย**: หน้ารายละเอียดงาน (นศ.), หน้าตรวจงาน (ครู), signal สร้าง GradeItem
- **field สำคัญ**:
  - `is_graded` — เหมือน Quiz
  - `due_at` **nullable** — null = ไม่มีกำหนดส่ง ไม่มีสถานะ late
  - `late_policy` — `closed_after_due` (เลย due ปิดรับ) / `accept_with_penalty` (รับต่อ หักคะแนน)
  - `accept_until` **nullable** — เส้นตายเด็ดขาด เลยนี้ปิดรับจริงแม้ policy = หักคะแนน
  - `penalty_percent_per_day` + `penalty_max_percent` — ใช้เมื่อ `accept_with_penalty`
  - `allow_resubmission` — คุมว่าส่งซ้ำได้ไหม
- **การลบ**: มี GradeItem → PROTECT ; ทำได้แค่ unpublish

#### `AssignmentAttachment`
- **หน้าที่**: ไฟล์โจทย์/ใบงานที่ครูแนบ (หลายไฟล์ได้ → แยกตาราง)
- **เขียนโดย**: teacher ตอนสร้าง/แก้งาน
- **อ่านโดย**: หน้ารายละเอียดงาน (นศ. ดาวน์โหลด)

#### `Submission` · *soft delete*
- **หน้าที่**: งานที่ นศ. 1 คนส่ง 1 ครั้ง + คะแนน + สถานะ
- **เขียนโดย**:
  - นศ. (บันทึกร่าง) → `status=draft`
  - นศ. (ส่ง) → `status=submitted`, `submitted_at`, คำนวณ `is_late`/`days_late` (เทียบ `due_at` ใน Asia/Bangkok)
  - นศ. (ส่งซ้ำ ถ้า `allow_resubmission`) → สร้างแถวใหม่ `attempt_number+1`, ตั้ง `is_latest=True` แถวใหม่ + `False` แถวเก่า
  - ครู (ตรวจ) → `raw_score` → คำนวณ `penalty_applied_percent` → `final_score` → `status=graded`, `feedback`, `graded_by`, `graded_at`
  - ครู (ส่งกลับให้แก้) → `status=returned`
  - ครู (ลบ) → soft delete ; ถ้าลบแถว `is_latest` ต้อง promote แถวก่อนหน้า
- **อ่านโดย**: หน้าสถานะงานของ นศ., หน้าตรวจงานของครู, **signal sync → `Score`** (ใช้ `final_score`)
- **lifecycle**: `draft → submitted → graded` (หรือ `→ returned → submitted` วนได้)
- **invariant**: `(assignment, student, attempt_number)` unique เฉพาะแถวที่ไม่ลบ ; `is_latest=True` มีได้แถวเดียวต่อ (assignment, student) ที่ไม่ลบ
- **field**: `final_score` = ตัวที่เข้า gradebook (ไม่ใช่ `raw_score`)
- **เชื่อมกับ**: `assignment`/`student` = **PROTECT**

#### `SubmissionFile`
- **หน้าที่**: ไฟล์ที่ นศ. อัปโหลดในการส่ง 1 ครั้ง (หลายไฟล์ได้)
- **เขียนโดย**: นศ. ตอนส่ง
- **อ่านโดย**: หน้าตรวจงานของครู (ดาวน์โหลด)

---

### 📁 grading

#### `GradingCategory`
- **หน้าที่**: หมวดคะแนน + น้ำหนัก % (เช่น Quiz 20% / Assignment 30% / Final 50%)
- **เขียนโดย**: teacher/co_teacher (ตั้งหมวด, ปรับ `weight_percent`, จัดลำดับ)
- **อ่านโดย**: gradebook, สูตรคำนวณ `CourseGrade`
- **invariant**: ผลรวม `weight_percent` ต่อวิชา **ควร** = 100 → ระบบเตือน ไม่บล็อก
- **การลบ**: มี `GradeItem` ในหมวด → **PROTECT** (ต้องย้าย item ออกก่อน)

#### `GradeItem`
- **หน้าที่**: 1 คอลัมน์ในสมุดคะแนน — มาจาก quiz / assignment / กรอกมือ (`source_type`)
- **เขียนโดย**:
  - **signal** (publish quiz/assignment ที่ `is_graded=True`) → สร้างอัตโนมัติ, ตั้ง `source_type`, `quiz`/`assignment` FK, `max_score` (copy), `category` (จาก `grading_category` ต้นทางถ้ามี)
  - ครู → ย้าย `category`, ปรับ `weight_within_category`, `order`, กด `is_published`
  - ครู → สร้างคอลัมน์ `manual` เอง
- **อ่านโดย**: gradebook, สูตร `CourseGrade` (เฉพาะ `is_published=True`)
- **field**:
  - `weight_within_category` — null = ถ่วงตามสัดส่วน `max_score` ; ตั้งค่า = ถ่วงตามค่านั้น
  - `category=NULL` — คอลัมน์ที่ยังไม่จัดหมวด → **ไม่ถูกนับใน weighted_total**
  - `is_published` — นศ. เห็นคะแนนคอลัมน์นี้ไหม + เข้าสูตรไหม
- **เชื่อมกับ**: `quiz`/`assignment`/`category` = **PROTECT** ทั้งหมด

#### `Score` · *soft delete*
- **หน้าที่**: คะแนนของ นศ. 1 คน ต่อ 1 `GradeItem`
- **เขียนโดย**:
  - **signal sync** — `QuizAttempt`/`Submission` ที่ `graded` → เขียน `raw_score` (`multiple_highest` = attempt สูงสุด), ตั้ง `source_attempt`/`source_submission`
  - ครู (กรอกคอลัมน์ manual) → `raw_score`
  - ครู (override) → `adjusted_score` — **signal ไม่ทับ** field นี้
  - ครู (ลบ) → soft delete
- **อ่านโดย**: gradebook, สูตร `CourseGrade`, หน้าคะแนนของ นศ.
- **invariant**: `(grade_item, student)` unique เฉพาะแถวที่ไม่ลบ ; คะแนนที่ใช้จริง = `adjusted_score` ถ้ามี ไม่งั้น `raw_score` ไม่งั้น 0
- **เชื่อมกับ**: `grade_item`/`student` = **PROTECT** (ลบ GradeItem ที่มี Score ไม่ได้)

#### `CourseGrade` (cache)
- **หน้าที่**: คะแนนรวมถ่วงน้ำหนักของ นศ. 1 คน ในวิชา 1 ตัว — cache เพื่อเร่ง dashboard/รายงาน
- **เขียนโดย**: **signal/job** — คำนวณใหม่เมื่อ `Score` / `GradeItem` (`is_published`/`max_score`/`weight_within_category`/`category`/สร้าง/ลบ) / `GradingCategory` (`weight_percent`/สร้าง/ลบ) / `Enrollment` เปลี่ยน
- **อ่านโดย**: dashboard นศ., รายงานเกรดของครู, export
- **สำคัญ**: **source of truth คือการคำนวณสดจากสูตร** — ตารางนี้คือ cache ที่ refresh ได้เสมอ ; API คำนวณสดได้ถ้า cache หาย/หมดอายุ
- **สูตร**: ดู `database.md` §9

---

### 📁 announcements

#### `Announcement`
- **หน้าที่**: ประกาศในวิชา — ครูเขียนเอง ทั้งวิชาเห็น
- **เขียนโดย**: teacher/co_teacher (เขียน, ปักหมุด, publish)
- **อ่านโดย**: หน้าวิชา + dashboard นศ. (เฉพาะ `is_published=True`)
- **lifecycle**: draft → publish (`published_at`) ; อาจ signal สร้าง `Notification(type=announcement_posted)` ให้ นศ.ทุกคน

#### `AnnouncementRead`
- **หน้าที่**: บันทึกว่า user X อ่านประกาศ Y แล้ว
- **เขียนโดย**: frontend เมื่อ นศ. เปิดอ่าน (upsert)
- **อ่านโดย**: badge "ยังไม่อ่าน" = ประกาศในวิชาที่ยังไม่มีแถวของ user นี้
- **invariant**: `(announcement, user)` unique. **ไม่ audit** (ปริมาณเยอะ)

---

### 📁 notifications

#### `Notification`
- **หน้าที่**: แจ้งเตือนรายบุคคลจาก event ระบบ (ตรวจงานเสร็จ, มีงานใหม่, ใกล้ครบกำหนด, ถูก enroll) — **web ล้วน MVP ไม่ส่งออกนอก**
- **เขียนโดย**: **service layer / signal** ตอนเกิด event — ตั้ง `recipient`, `notification_type`, `context` (params), `link_url`
  - `due_soon`: **MVP ไม่สร้างแถว** — หน้า dashboard คำนวณ "งานที่ต้องทำเร็ว ๆ นี้" สดตอนเปิดแอป (ตัดสินใจใน v1.4; ถ้าจะสร้างแถวภายหลังต้องมี scheduled job สแกน)
- **อ่านโดย**: frontend (กระดิ่ง 🔔 + นับ `is_read=False`) ; frontend ประกอบข้อความจาก translation key ตาม `notification_type` + `context`
- **lifecycle**: สร้าง → นศ.เปิด → `is_read=True`, `read_at` ; cleanup job ลบที่อ่านแล้ว > N วัน
- **สำคัญ**: `context` เป็น JSON params ไม่ใช่ข้อความสำเร็จรูป → i18n อยู่ที่ frontend. **ไม่ audit**
- **ขยายอนาคต**: ส่ง email/push = เพิ่ม delivery layer อ่านจากตารางนี้ ไม่แก้ schema

---

### 📁 audit

#### `AuditLog`
- **หน้าที่**: บันทึกการกระทำที่เปลี่ยนข้อมูลสำคัญทั้งระบบ — log กลางแบบ generic
- **เขียนโดย** (2 ทาง):
  1. **`Auditable` signal** (อัตโนมัติ) — ทุก model ที่ inherit `Auditable` save/delete → เขียน `action=create/update/delete` + `changes` (field diff)
  2. **`log_action()`** (เรียกเองใน service layer) — เฉพาะ:
     - ไม่มี model save: `login`, `logout`, `impersonate_start`, `impersonate_end`
     - 1 การกระทำกระทบหลายแถว: `publish`, `enroll`, `unenroll`, `regrade`
- **อ่านโดย**: Admin เท่านั้น — หน้า audit log (กรอง actor/action/ช่วงเวลา), หน้า "ประวัติของ object นี้" (ใช้ index `(content_type, object_id)`)
- **field**:
  - `actor` — คนทำ (NULL = ระบบ) ; `impersonated_by` — Admin ตัวจริงถ้าอยู่โหมด impersonation
  - `content_type` + `object_id` — ชี้ไปแถวใดก็ได้ (Django ContentType framework)
  - `changes` — `{"field": [old, new]}` ; `context` — IP, user-agent, path
- **ไม่ audit**: session, token, `AuditLog` เอง, `AnnouncementRead`, `Notification`, `CourseGrade`, cache

---

## 2. State machines

### `Enrollment.status`
```
         admin เพิ่ม / นศ. ใส่ code
                    │
                    ▼
                 active ──── นศ./ครู ถอน ───► dropped
                    │                            │
                    │ ◄──── ครู เพิ่มกลับ ────────┘
                    │
              จบเทอม (job/manual)
                    ▼
                completed
```
(`invited` — สงวนไว้ ไม่ใช้ MVP)

### `QuizAttempt.status`
```
in_progress ──► submitted ────────┐
     │                            ├──► graded
     └──► auto_submitted (หมดเวลา)─┘
```
- `submitted`/`auto_submitted` → `graded` เมื่อ: ไม่มีข้อ manual (auto-grader จบเลย) **หรือ** ครูตรวจข้อ manual ครบ

### `Submission.status`
```
draft ──► submitted ──► graded
              ▲            │
              └── returned ◄┘  (ครูส่งกลับให้แก้ ; นศ. แก้แล้วส่งใหม่)
```

### publish lifecycle (Course / Module / Content / Quiz / Assignment)
```
is_published = False (draft)  ──► True (published, นศ.เห็น)  ──► False (ซ่อนกลับ, ไม่ลบข้อมูล)
```
- Quiz/Assignment: publish ครั้งแรก + `is_graded=True` → signal สร้าง `GradeItem` (unpublish ไม่ลบ GradeItem แค่ set `is_published=False`)

---

## 3. Workflow ครบวงจร

### W1 — สมัครเอง + ยืนยันอีเมล
1. `POST /auth/register` (email + password) → สร้าง `User(role=student, is_email_verified=False)` + `EmailVerificationToken(purpose=verify_email)` → ส่งอีเมล (dev = console)
2. นศ. กดลิงก์ → หน้าเว็บ `/verify-email?token=…` เรียก `POST /auth/verify-email/` (ใช้ POST ไม่ใช่ GET เพราะโปรแกรมสแกนอีเมลเปิดลิงก์ล่วงหน้า) → เช็ค `expires_at`/`used_at` → ตั้ง `User.is_email_verified=True` + `token.used_at`
3. login ได้เมื่อ `is_email_verified=True`

### W2 — Admin สร้างบัญชีครู
1. Admin กรอกฟอร์ม → `POST /admin/users` → สร้าง `User(role=teacher, student_or_staff_id=…, created_by=<admin>, is_email_verified=True)`
2. `Auditable` signal → `AuditLog(action=create, content_type=User, actor=<admin>)`
3. ส่งอีเมลลิงก์ตั้งรหัสผ่านครั้งแรก = `EmailVerificationToken(purpose=reset_password)` — บัญชีที่ Admin สร้างยังไม่มีรหัสผ่านจนกว่าเจ้าของกดลิงก์ — ลิงก์ที่ Admin ส่งให้ตั้งรหัสผ่านครั้งแรกมีอายุ **7 วัน** (Admin กด "ส่งลิงก์อีกครั้ง" ได้เมื่อหมดอายุ) ส่วนลิงก์ "ลืมรหัสผ่าน" ที่ผู้ใช้ขอเองอายุ **1 ชั่วโมง** — endpoint `POST /auth/forgot-password/` ส่งลิงก์เฉพาะบัญชีที่ยืนยันอีเมลแล้ว, `POST /auth/reset-password/` ตั้งรหัสใหม่และทำให้เซสชันเดิมทั้งหมดใช้ไม่ได้ (ดู `docs/api-auth.md`)

### W3 — สร้างรายวิชา + เพิ่ม co-teacher
1. teacher → `POST /courses` (term, code, name) → `Course(is_published=False, created_by=<teacher>)` + `CourseTeacher(user=<teacher>, course_role=owner)`
2. owner → `POST /courses/{id}/teachers` (user, role=co_teacher) → `CourseTeacher(added_by=<owner>)` → `AuditLog(action=create)`
3. owner → เปิด self-enroll → `Course.self_enroll_enabled=True` + generate `invite_code`
4. owner → publish → `Course.is_published=True` → `AuditLog(action=publish)`

### W4 — Enroll แบบ admin assign
1. teacher → หน้า roster → เพิ่มรายชื่อ (เลือก user หลายคน) → `POST /courses/{id}/enrollments` (bulk)
2. ต่อคน → `Enrollment(status=active, method=admin_assigned, enrolled_by=<teacher>)`
3. `log_action(action=enroll)` 1 แถว (ไม่ใช่ต่อคน)

### W5 — Enroll แบบ self ด้วย invite_code
1. นศ. → `POST /enroll` (invite_code) → หา `Course` จาก code → เช็ค `self_enroll_enabled` + `is_published`
2. → `Enrollment(status=active, method=self_enrolled, enrolled_by=NULL)`

### W6 — สร้างเนื้อหา
1. teacher → `POST /courses/{id}/modules` → `Module(order=next, is_published=False)`
2. teacher → `POST /modules/{id}/contents` (content_type, ...) → อัปโหลดไฟล์ผ่าน backend → Cloudinary → เก็บ URL ใน `Content.file_url`/`video_url`/…
3. teacher → publish module + contents → นศ. เห็น (ถ้า `available_from` ผ่านแล้ว)

### W7 — สร้าง + publish quiz → GradeItem เกิด
1. teacher → `POST /courses/{id}/quizzes` → `Quiz(is_published=False, is_graded=True)`
2. teacher → เพิ่ม `Question` + `Choice`/`MatchingPair` → `Quiz.max_score` อัปเดต = Σ points
3. teacher → publish → `Quiz.is_published=True`
4. **signal** `post_save(Quiz)` เห็น `is_published` เปลี่ยน + `is_graded=True` → สร้าง `GradeItem(source_type=quiz, quiz=<quiz>, max_score=<copy>, category=<quiz.grading_category>, is_published=False)`
5. `log_action(action=publish)`

### W8 — นักศึกษาทำ timed quiz → auto-grade → Score → CourseGrade
1. นศ. กด "เริ่มทำ" → `POST /quizzes/{id}/attempts` → เช็ค `available_from/until`, `attempt_policy`, `max_attempts` → `QuizAttempt(status=in_progress, started_at=now, due_at=min(now+limit, available_until), max_score=<snapshot>)`
2. นศ. ตอบแต่ละข้อ → `PUT /attempts/{id}/answers/{qid}` → upsert `Answer(response=…, selected_choice=…)` — ทุกครั้งเช็ค `now() <= due_at`
3. นศ. กด submit **หรือ** หมดเวลา:
   - สร้าง `Answer` เปล่าให้ข้อที่ยังไม่ตอบ (`points_awarded=0`)
   - `status=submitted` (หรือ `auto_submitted`)
4. **auto-grader** — ต่อ `Answer`:
   - mcq/tf/dropdown → เทียบ `response.choice_id` กับ `Choice.is_correct` → `is_correct`, `points_awarded`
   - matching → เทียบทีละคู่ → `points_awarded = points × คู่ถูก/คู่ทั้งหมด`
   - short_answer auto → normalize + เทียบ `accepted_answers`
   - short_answer manual → เว้น `is_correct=NULL` รอครู
5. ถ้าไม่มีข้อ manual → `QuizAttempt.score = Σ points_awarded`, `status=graded`
6. **signal sync** — `QuizAttempt` `graded` → หา `GradeItem` ของ quiz นี้ → เขียน `Score(raw_score=<score>, source_attempt=<attempt>)` (`multiple_highest` → เทียบกับ attempt อื่น เอาสูงสุด)
7. **signal** — `Score` เปลี่ยน → recompute `CourseGrade` ของ นศ.คนนั้น

### W9 — ครูตรวจข้อ manual (short_answer)
1. ครู → หน้าตรวจ quiz → เห็น `Answer` ที่ `is_correct=NULL`
2. ครู ให้คะแนน → `PATCH /attempts/{id}/answers/{aid}` → `points_awarded`, `feedback`, `graded_by`, `graded_at`
3. ครบทุกข้อ → `QuizAttempt.score` รวมใหม่, `status=graded`, `graded_by`, `graded_at`
4. → signal sync → `Score` → `CourseGrade` (เหมือน W8 ขั้น 6–7)

### W10 — ครูแก้เฉลยที่ผิด → regrade
1. quiz มี attempt แล้ว → การแก้ `Choice.is_correct` ถูกล็อกใน API ปกติ
2. ครู → `POST /quizzes/{id}/regrade` (ยืนยัน) → ปลดล็อก → แก้เฉลย → recompute **ทุก** `QuizAttempt` + `Answer` ที่กระทบ → อัปเดต `Score` → `CourseGrade`
3. `log_action(action=regrade)` 1 แถว + ราย attempt ใน `changes`

### W11 — นักศึกษาส่ง assignment (ปกติ / สาย / ส่งซ้ำ)
1. นศ. → บันทึกร่าง → `Submission(status=draft, attempt_number=1, is_latest=True)`
2. นศ. อัปโหลดไฟล์ → `SubmissionFile` หลายแถว
3. นศ. กดส่ง → `status=submitted`, `submitted_at=now`
   - ถ้า `due_at` ไม่ null และ `now > due_at` (เทียบ Asia/Bangkok):
     - `late_policy=closed_after_due` → ปฏิเสธ (เว้นแต่ก่อน `accept_until`... จริง ๆ `closed_after_due` = ปิดที่ due เลย)
     - `late_policy=accept_with_penalty` + (ไม่มี `accept_until` หรือ `now <= accept_until`) → รับ, `is_late=True`, `days_late=ceil(...)`
     - เลย `accept_until` → ปฏิเสธ
4. นศ. ส่งซ้ำ (ถ้า `allow_resubmission`) → `Submission(attempt_number=2, is_latest=True)` + set แถวเก่า `is_latest=False`

### W12 — ครูตรวจ assignment → final_score → Score
1. ครู → หน้าตรวจงาน → เห็น `Submission` ที่ `is_latest=True, status=submitted`
2. ครู ให้ `raw_score` + `feedback` → ระบบคำนวณ:
   - `penalty_applied_percent = min(days_late × penalty_percent_per_day, penalty_max_percent)` (ถ้า `is_late`)
   - `final_score = raw_score × (1 - penalty_applied_percent/100)`
   - `status=graded`, `graded_by`, `graded_at`
3. **signal sync** — `Submission` `graded` → `Score(raw_score=final_score, source_submission=<submission>)` → `CourseGrade`

### W13 — ตั้ง GradingCategory + weight → CourseGrade
1. teacher → `POST /courses/{id}/grading-categories` × N (Quiz 20, Assignment 30, Final 50) → ระบบเตือนถ้ารวม ≠ 100
2. teacher → ลาก `GradeItem` เข้าหมวด / ตั้ง `weight_within_category`
3. teacher → publish `GradeItem` ที่ต้องการให้ นศ.เห็น → `is_published=True`
4. **signal** → recompute `CourseGrade` ทุก นศ.ในวิชา (สูตร §9)
5. นศ. เห็นเกรด % ต่อหมวด + weighted total ใน dashboard

### W14 — ประกาศ + อ่าน/ยังไม่อ่าน
1. teacher → `POST /courses/{id}/announcements` → `Announcement(is_published=False)`
2. teacher → publish → `is_published=True`, `published_at` → (option) signal สร้าง `Notification(type=announcement_posted)` ให้ นศ.ทุกคนในวิชา
3. นศ. เปิดอ่าน → `POST /announcements/{id}/read` → upsert `AnnouncementRead(user, read_at)`
4. badge = count(`Announcement` published ในวิชาที่เรียน) − count(`AnnouncementRead` ของ user)

### W15 — Notification lifecycle
1. event เกิด (เช่น W12 ตรวจงานเสร็จ) → service สร้าง `Notification(recipient=<นศ.>, notification_type=submission_graded, context={course_name, assignment_title, score}, link_url=/courses/12/assignments/5)`
2. frontend poll/refresh กระดิ่ง → แสดง count `is_read=False`
3. นศ. กด → navigate ตาม `link_url` + `PATCH` → `is_read=True`, `read_at`
4. (ยังไม่ทำใน MVP) `due_soon` — จะใช้ cron สแกนงานที่ `due_at` ใน 24 ชม. แล้วสร้าง Notification ภายหลัง ตอนนี้ dashboard คำนวณสดแทน

### W16 — Admin impersonation
1. Admin → `POST /admin/impersonate` (target_user) → `log_action(action=impersonate_start, actor=<admin>, object=target)`
2. ระหว่างนั้นทุก AuditLog มี `impersonated_by=<admin>` + `actor=<target>`
3. Admin → exit → `log_action(action=impersonate_end)`

### W17 — การลบของ (3 ระดับ)
| สิ่งที่ลบ | เงื่อนไข | ผล |
|---|---|---|
| Quiz/Assignment/Module/Content **draft** | ไม่เคย publish + ไม่มี attempt/submission | hard delete (+ cascade Question/Choice/Attachment) |
| Quiz/Assignment **published** หรือมีข้อมูล นศ. | — | ลบไม่ได้ → `is_published=False` (ซ่อน) |
| Submission / QuizAttempt / Score | ครูกดลบ | **soft delete** (`deleted_at`) |
| GradeItem ที่มี Score | — | ลบไม่ได้ (PROTECT) → `is_published=False` |
| GradingCategory ที่มี GradeItem | — | ลบไม่ได้ (PROTECT) → ย้าย item ออกก่อน |
| User ที่มีประวัติเรียน/สอน | — | ลบไม่ได้ → `is_active=False` |

---

## 4. Access pattern ตามหน้าจอหลัก

### Student dashboard
- วิชาที่เรียน: `Enrollment(student=me, status=active)` → `Course`
- งานที่ต้องส่ง: `Assignment(course__in=…, is_published=True)` − `Submission(student=me, status__in=[submitted,graded])`
- quiz ที่ทำได้: `Quiz(course__in=…, is_published=True, available_from<=now<=available_until)`
- เกรด: `CourseGrade(student=me)` (cache) หรือคำนวณสด
- แจ้งเตือน: `Notification(recipient=me, is_read=False)` count
- ประกาศใหม่: ดู W14 ขั้น 4

### Teacher — course roster
- `Enrollment(course=X)` join `User` → รายชื่อ + status
- ต่อคน: progress = (นับ Submission/QuizAttempt เทียบจำนวนงาน)

### Teacher — gradebook (หน้าตาราง)
- แถว = `Enrollment(course=X, status=active)` → นศ.
- คอลัมน์ = `GradeItem(course=X)` เรียงตาม `category.order`, `order`
- เซลล์ = `Score(grade_item, student)` → แสดง `adjusted_score ?? raw_score ?? "-"`
- แถวสรุป = `CourseGrade(course=X)` ต่อ นศ.

### Notification bell
- list: `Notification(recipient=me)` order by `-created_at` limit 20
- unread count: `Notification(recipient=me, is_read=False).count()`

---

## 5. Invariant ที่บังคับใน application layer (ไม่ใช่ DB constraint)

1. self-register → `role=student` เสมอ
2. `teacher`/`admin` role ตั้งได้โดย Admin เท่านั้น + AuditLog
3. ทุก `Course` มี `CourseTeacher(course_role=owner)` ≥ 1
4. `GradingCategory.weight_percent` รวม = 100 → เตือน (ไม่บล็อก)
5. แก้ `Question.points` / `Choice.is_correct` / เพิ่ม-ลบ Question เมื่อ quiz มี `QuizAttempt` → บล็อก (ต้อง `regrade`)
6. `QuizAttempt` — ปฏิเสธ save คำตอบเมื่อ `now() > due_at`
7. `Submission` — 1 แถว `is_latest=True` ต่อ (assignment, student)
8. `Term.is_current` — แถวเดียว (มี DB partial index ช่วย แต่ logic set/unset อยู่ใน app)
9. `Score` sync ไม่ทับ `adjusted_score`

---

## 6. สิ่งที่ยังไม่ตัดสิน / ตัดสินตอน implement

- กฎ normalize `short_answer` ภาษาไทย (วรรณยุกต์/สระ/ช่องว่าง) — ให้ Thai-aware
- รายละเอียดสิทธิ์ `ta` ที่แน่นอน (ตอนทำฟีเจอร์ permission)
- `Content` progress tracking — ตาราง `ContentProgress` (§13)
- การผ่อนผันรายคน — `QuizException` (§13)
- งานกลุ่ม — `AssignmentGroup` (§13)
- retention: ลบ `Notification`/`AuditLog`/`EmailVerificationToken` เก่า
- composite index จริง (ดู `database.md` §11 ท้าย)
- background job vs signal สำหรับ recompute `CourseGrade` แบบ bulk

---

## 7. เช็กลิสต์ก่อนตอบคำถามเกี่ยวกับ schema นี้ (สำหรับ session อื่น)

- [ ] อ่าน `CLAUDE.md` (บริบท + tech stack + role permissions + working principles)
- [ ] อ่านไฟล์นี้ (§0–§3 อย่างน้อย)
- [ ] เปิด `database.md` เมื่อต้องการ field/type/constraint ที่แน่นอน
- [ ] เปิด `database-erd.md` เมื่อต้องการเห็นความสัมพันธ์เป็นภาพ
- [ ] จำ 3 กลไกอัตโนมัติ: Auditable signal / SoftDelete / score-sync signal
- [ ] จำเส้นแบ่ง hard vs soft delete (§3 W17)
- [ ] permission = ต่อวิชา (CourseTeacher + Enrollment) ไม่ใช่แค่ User.role
