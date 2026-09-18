# สรุป field ทุกตาราง — LMS (v1.3)

> Quick reference คู่กับ [`database.md`](./database.md) (สเปกเต็ม) และ [`database-erd.md`](./database-erd.md) (ERD)
> ทุกตารางมี `id` (PK, BigAutoField), `created_at`, `updated_at` — ไม่ลิสต์ซ้ำด้านล่าง
> ชื่อ/หัวข้อทุกตาราง = field เดียว (ไม่แยก `_th/_en`)

---

## 📁 accounts

### `User` — บัญชีผู้ใช้ทุกคน (admin/teacher/student)
| field | เก็บอะไร |
|---|---|
| `email` | อีเมล (ไม่ซ้ำ) — ใช้ login ได้ |
| `student_or_staff_id` | รหัสนักศึกษา/พนักงาน (ไม่ซ้ำ, ว่างได้) — ใช้ login ได้ |
| `role` | บทบาทระดับระบบ: `admin` / `teacher` / `student` |
| `first_name`, `last_name` | ชื่อ-นามสกุล (ภาษาที่ผู้ใช้กรอก) |
| `first_name_en`, `last_name_en` | ชื่อ-นามสกุลภาษาอังกฤษของบุคคล (ไม่บังคับ) — สำหรับเอกสารทางการ |
| `is_email_verified` | ยืนยันอีเมลแล้วหรือยัง (บัญชีสมัครเอง) |
| `is_active` | บัญชีเปิดใช้งานอยู่ไหม (Admin ปิดได้) |
| `is_staff`, `is_superuser` | สิทธิ์เข้า Django admin (คนละเรื่องกับ `role`) |
| `avatar_url` | ลิงก์รูปโปรไฟล์ (Cloudinary) |
| `created_by` | ใครสร้างบัญชีนี้ (ว่าง = สมัครเอง) |
| `last_login`, `date_joined` | เวลาล็อกอินล่าสุด / วันสร้างบัญชี |

### `EmailVerificationToken` — โทเคนยืนยันอีเมล / รีเซ็ตรหัสผ่าน
| field | เก็บอะไร |
|---|---|
| `user` | โทเคนนี้ของใคร |
| `token` | สตริงสุ่ม (ไม่ซ้ำ) ที่ส่งไปในลิงก์ |
| `purpose` | `verify_email` / `reset_password` |
| `expires_at` | หมดอายุเมื่อไหร่ |
| `used_at` | ใช้ไปแล้วเมื่อไหร่ (ว่าง = ยังไม่ใช้) |

---

## 📁 academics

### `Term` — ภาคเรียน / ปีการศึกษา
| field | เก็บอะไร |
|---|---|
| `academic_year` | ปีการศึกษา เช่น 2568 |
| `semester` | ภาคเรียน: `1` / `2` / `3` (3 = ฤดูร้อน) |
| `name` | ป้ายชื่อ เช่น "1/2568" |
| `start_date`, `end_date` | วันเริ่ม-สิ้นสุดเทอม |
| `is_current` | เป็นเทอมปัจจุบันไหม (มีได้ตัวเดียว) |

### `Course` — รายวิชา (1 วิชา 1 เทอม = 1 แถว)
| field | เก็บอะไร |
|---|---|
| `term` | อยู่เทอมไหน |
| `code` | รหัสวิชา เช่น "204491" |
| `section` | ตอนเรียน (ว่างได้) |
| `name` | ชื่อวิชา |
| `description` | คำอธิบายรายวิชา |
| `self_enroll_enabled` | เปิดให้ลงทะเบียนเองด้วยรหัสไหม |
| `invite_code` | รหัสเข้าเรียน (ไม่ซ้ำ, ว่างได้) |
| `is_published` | เผยแพร่แล้วไหม (นักศึกษาเห็นเมื่อ true) |
| `created_by` | ใครสร้างวิชานี้ |

### `CourseTeacher` — ตารางกลาง: ผู้สอนของแต่ละวิชา
| field | เก็บอะไร |
|---|---|
| `course` | วิชาไหน |
| `user` | ครูคนไหน |
| `course_role` | `owner` / `co_teacher` / `ta` |
| `added_by` | ใครเพิ่มครูคนนี้เข้ามา |

---

## 📁 content

### `Module` — บทเรียนในวิชา
| field | เก็บอะไร |
|---|---|
| `course` | อยู่วิชาไหน |
| `title` | ชื่อบท |
| `description` | คำอธิบายบท (ว่างได้) |
| `order` | ลำดับบทในวิชา |
| `is_published` | เผยแพร่แล้วไหม |

### `Content` — เนื้อหาย่อยในบท (ข้อความ/ไฟล์/วิดีโอ/ลิงก์)
| field | เก็บอะไร |
|---|---|
| `module` | อยู่บทไหน |
| `title` | ชื่อหัวข้อ |
| `content_type` | ชนิด: `text` / `file` / `image` / `video` / `audio` / `link` |
| `body` | เนื้อหา rich text (สำหรับชนิด text) |
| `order` | ลำดับในบท |
| `is_published` | เผยแพร่แล้วไหม |
| `available_from` | ตั้งเวลาปล่อยเนื้อหา (ว่าง = เปิดเลย) |
| `file_url` | ลิงก์ไฟล์ Cloudinary — ชนิด file/image/audio |
| `file_name`, `file_size`, `mime_type` | ข้อมูลไฟล์: ชื่อ / ขนาด / ประเภท |
| `video_source` | `cloudinary` / `youtube` — ชนิด video |
| `video_url` | ลิงก์วิดีโอ |
| `external_url` | ลิงก์ภายนอก — ชนิด link |

---

## 📁 enrollment

### `Enrollment` — ตารางกลาง: การลงทะเบียนเรียนของนักศึกษา
| field | เก็บอะไร |
|---|---|
| `course` | วิชาไหน |
| `student` | นักศึกษาคนไหน |
| `status` | `invited` / `active` / `dropped` / `completed` (admin เพิ่ม = `active` ทันที) |
| `method` | `admin_assigned` (ครูใส่ให้) / `self_enrolled` (ลงเอง) |
| `enrolled_by` | ใครลงทะเบียนให้ (ว่าง = ลงเอง) |
| `enrolled_at` | ลงทะเบียนเมื่อไหร่ |
| `dropped_at` | ถอนเมื่อไหร่ (ว่าง = ยังไม่ถอน) |

---

## 📁 assessments (Quiz)

### `Quiz` — แบบทดสอบ / แบบฝึกหัดท้ายบท
| field | เก็บอะไร |
|---|---|
| `course` | อยู่วิชาไหน (บังคับ) |
| `module` | ผูกกับบทไหน (ไม่บังคับ) |
| `title` | ชื่อ quiz |
| `description` | คำอธิบาย (ว่างได้) |
| `is_graded` | เข้า gradebook ไหม (default True) — False = quiz ฝึก ไม่เข้าเกรดรวม |
| `grading_category` | คะแนนเข้าหมวดไหนในสมุดคะแนน |
| `max_score` | คะแนนเต็ม (รวมจาก Question.points) |
| `is_timed` | จับเวลาไหม |
| `time_limit_minutes` | จำกัดกี่นาที (ใช้เมื่อ is_timed) |
| `attempt_policy` | `single` (ครั้งเดียว) / `multiple_highest` (หลายครั้ง เก็บสูงสุด) |
| `max_attempts` | ทำได้กี่ครั้ง (ว่าง = ไม่จำกัด) |
| `available_from`, `available_until` | ช่วงเวลาที่เปิดให้ทำ |
| `shuffle_questions` | สลับลำดับข้อไหม |
| `show_correct_answers` | `never` / `after_submit` / `after_close` |
| `is_published` | เผยแพร่แล้วไหม (publish + is_graded → สร้าง GradeItem อัตโนมัติ) |
| `created_by` | ใครสร้าง |

> มี `QuizAttempt` แล้ว → ล็อกแก้เชิงโครงสร้าง (เพิ่ม/ลบ/เรียงข้อ, คะแนน, เฉลย) ; แก้จริงต้องใช้ action `regrade`

### `Question` — คำถามในแต่ละ quiz
| field | เก็บอะไร |
|---|---|
| `quiz` | อยู่ quiz ไหน |
| `question_type` | `mcq` / `true_false` / `matching` / `dropdown` / `short_answer` |
| `text` | โจทย์ (rich text) |
| `order` | ลำดับข้อ |
| `points` | คะแนนของข้อนี้ |
| `explanation` | เฉลย/คำอธิบาย แสดงหลังทำ (ว่างได้) |
| `shuffle_choices` | สลับตัวเลือกไหม (mcq/dropdown) |
| `accepted_answers` | รายการคำตอบที่ยอมรับ (JSON) — short_answer แบบตรวจอัตโนมัติ |
| `manual_grading` | ครูตรวจเองไหม — เฉพาะ short_answer |

### `Choice` — ตัวเลือก (mcq / true_false / dropdown)
| field | เก็บอะไร |
|---|---|
| `question` | ของคำถามข้อไหน |
| `text` | ข้อความตัวเลือก |
| `is_correct` | เป็นคำตอบที่ถูกไหม |
| `order` | ลำดับตัวเลือก |

### `MatchingPair` — คู่จับคู่ที่ถูกต้อง (matching)
| field | เก็บอะไร |
|---|---|
| `question` | ของคำถามข้อไหน |
| `left_text` | ข้อความฝั่งซ้าย (โจทย์) |
| `right_text` | ข้อความฝั่งขวา (คำตอบที่คู่กัน) |
| `order` | ลำดับคู่ |

> คะแนน = บางส่วน: `points × (คู่ถูก / คู่ทั้งหมด)`

### `QuizAttempt` — การเข้าทำ quiz 1 ครั้งของนักศึกษา 1 คน · *soft delete*
| field | เก็บอะไร |
|---|---|
| `quiz` | ทำ quiz ไหน |
| `student` | ใครทำ |
| `attempt_number` | ครั้งที่เท่าไหร่ (1, 2, 3…) |
| `status` | `in_progress` / `submitted` / `auto_submitted` / `graded` |
| `started_at` | เริ่มทำเมื่อไหร่ (server บันทึก) |
| `due_at` | ต้องส่งก่อนเวลานี้ (snapshot = min(started_at + เวลาจำกัด, available_until)) |
| `submitted_at` | ส่งเมื่อไหร่ |
| `score` | คะแนนที่ได้ (หลังตรวจ) |
| `max_score` | คะแนนเต็ม ณ ตอนเริ่มทำ (snapshot) |
| `graded_at`, `graded_by` | ตรวจเสร็จเมื่อไหร่ / ใครตรวจ |
| `deleted_at`, `deleted_by` | ครูลบทิ้งเมื่อไหร่ / ใครลบ (soft) |

### `Answer` — คำตอบ 1 ข้อ ต่อ 1 คำถาม ต่อ 1 attempt
| field | เก็บอะไร |
|---|---|
| `attempt` | ของการทำครั้งไหน |
| `question` | ตอบคำถามข้อไหน |
| `response` | คำตอบจริง (JSON) — รูปแบบต่างกันตามชนิดคำถาม |
| `selected_choice` | ตัวเลือกที่เลือก (denormalize เพื่อทำรายงาน) |
| `is_correct` | ถูกไหม (ว่าง = ยังไม่ตรวจ) |
| `points_awarded` | ได้กี่คะแนน |
| `feedback` | ความเห็นครู (กรณีตรวจมือ) |
| `graded_by`, `graded_at` | ใครตรวจ / เมื่อไหร่ |

รูปแบบ `response`: mcq/dropdown/true_false → `{"choice_id": 123}` · matching → `{"pairs": {"<left_id>": right_id}}` · short_answer → `{"text": "..."}`

---

## 📁 assignments

### `Assignment` — งานที่มอบหมาย
| field | เก็บอะไร |
|---|---|
| `course` | อยู่วิชาไหน |
| `module` | ผูกกับบทไหน (ไม่บังคับ) |
| `grading_category` | คะแนนเข้าหมวดไหน |
| `is_graded` | เข้า gradebook ไหม (default True) — False = งานฝึก ไม่เข้าเกรดรวม |
| `title` | ชื่องาน |
| `description` | โจทย์ (rich text) |
| `max_score` | คะแนนเต็ม |
| `due_at` | กำหนดส่ง (ว่างได้ = ไม่มีกำหนด, ไม่มีสถานะ late) |
| `late_policy` | `closed_after_due` (ปิดรับ) / `accept_with_penalty` (รับแบบหักคะแนน) |
| `accept_until` | เส้นตายเด็ดขาด (ว่างได้) — เลยนี้ปิดรับจริงแม้ policy = หักคะแนน |
| `penalty_percent_per_day` | หักกี่ % ต่อวัน |
| `penalty_max_percent` | เพดานการหัก เช่น 50% |
| `allow_resubmission` | ส่งซ้ำได้ไหม |
| `allowed_file_types` | นามสกุลไฟล์ที่รับ (JSON) เช่น ["pdf","docx"] |
| `max_file_size_mb` | ขนาดไฟล์สูงสุด |
| `max_files` | จำนวนไฟล์สูงสุด |
| `available_from` | เปิดให้เห็นเมื่อไหร่ |
| `is_published` | เผยแพร่แล้วไหม (publish + is_graded → สร้าง GradeItem อัตโนมัติ) |
| `created_by` | ใครสร้าง |

### `AssignmentAttachment` — ไฟล์โจทย์ที่ครูแนบ
| field | เก็บอะไร |
|---|---|
| `assignment` | ของงานไหน |
| `file_url`, `file_name`, `file_size`, `mime_type` | ลิงก์ + ข้อมูลไฟล์ |

### `Submission` — งานที่นักศึกษาส่ง · *soft delete*
| field | เก็บอะไร |
|---|---|
| `assignment` | ส่งงานไหน |
| `student` | ใครส่ง |
| `attempt_number` | ส่งครั้งที่เท่าไหร่ |
| `is_latest` | เป็นฉบับล่าสุดไหม |
| `status` | `draft` / `submitted` / `graded` / `returned` |
| `submitted_at` | ส่งเมื่อไหร่ |
| `is_late` | ส่งสายไหม |
| `days_late` | สายกี่วัน |
| `text_response` | คำตอบแบบพิมพ์ในระบบ (ว่างได้) |
| `raw_score` | คะแนนก่อนหักสาย |
| `penalty_applied_percent` | หักไปกี่ % |
| `final_score` | คะแนนหลังหัก → ตัวนี้เข้าสมุดคะแนน |
| `feedback` | ความเห็นครู |
| `graded_by`, `graded_at` | ใครตรวจ / เมื่อไหร่ |
| `deleted_at`, `deleted_by` | ครูลบทิ้งเมื่อไหร่ / ใครลบ (soft) |

### `SubmissionFile` — ไฟล์ที่นักศึกษาอัปโหลด
| field | เก็บอะไร |
|---|---|
| `submission` | ของการส่งครั้งไหน |
| `file_url`, `file_name`, `file_size`, `mime_type` | ลิงก์ + ข้อมูลไฟล์ |

---

## 📁 grading

### `GradingCategory` — หมวดคะแนน + น้ำหนัก
| field | เก็บอะไร |
|---|---|
| `course` | ของวิชาไหน |
| `name` | ชื่อหมวด เช่น "Quiz" |
| `weight_percent` | น้ำหนัก % เช่น 20.00 |
| `order` | ลำดับหมวด |

### `GradeItem` — 1 คอลัมน์คะแนนในสมุดคะแนน
| field | เก็บอะไร |
|---|---|
| `course` | ของวิชาไหน |
| `category` | อยู่หมวดไหน (ว่าง = ยังไม่จัดหมวด → ไม่นับในเกรดรวม) |
| `title` | ชื่อคอลัมน์ |
| `max_score` | คะแนนเต็มของคอลัมน์นี้ |
| `source_type` | `quiz` / `assignment` / `manual` |
| `quiz` | ชี้ไป quiz ต้นทาง (เมื่อ source เป็น quiz) |
| `assignment` | ชี้ไป assignment ต้นทาง (เมื่อ source เป็น assignment) |
| `weight_within_category` | น้ำหนักในหมวด (ว่าง = ถ่วงตามสัดส่วน max_score) |
| `is_published` | นักศึกษาเห็นคะแนนคอลัมน์นี้ไหม |
| `order` | ลำดับ |

### `Score` — คะแนนของนักศึกษา 1 คน ต่อ 1 คอลัมน์ · *soft delete*
| field | เก็บอะไร |
|---|---|
| `grade_item` | คอลัมน์ไหน |
| `student` | ของใคร |
| `raw_score` | คะแนนดิบ (จาก attempt/submission หรือกรอกมือ) |
| `adjusted_score` | คะแนนที่ครู override (ถ้ามี ใช้ตัวนี้แทน) |
| `comment` | หมายเหตุ (ว่างได้) |
| `source_attempt` | มาจาก quiz attempt ไหน |
| `source_submission` | มาจาก submission ไหน |
| `updated_by` | ใครแก้คะแนนล่าสุด |
| `deleted_at`, `deleted_by` | ครูลบทิ้งเมื่อไหร่ / ใครลบ (soft) |

### `CourseGrade` — cache คะแนนรวมถ่วงน้ำหนัก (บังคับมี, recompute อัตโนมัติ)
| field | เก็บอะไร |
|---|---|
| `course` | ของวิชาไหน |
| `student` | ของใคร |
| `weighted_total_percent` | คะแนนรวมถ่วงน้ำหนักสุดท้าย (%) |
| `breakdown` | คะแนน % แยกตามหมวด (JSON) |
| `computed_at` | คำนวณล่าสุดเมื่อไหร่ |

---

## 📁 announcements

### `Announcement` — ประกาศในรายวิชา (ครูเขียนเอง)
| field | เก็บอะไร |
|---|---|
| `course` | ของวิชาไหน |
| `author` | ใครเขียน |
| `title` | หัวข้อ |
| `body` | เนื้อหา (rich text) |
| `is_pinned` | ปักหมุดไว้บนสุดไหม |
| `is_published` | เผยแพร่แล้วไหม |
| `published_at` | เผยแพร่เมื่อไหร่ |

### `AnnouncementRead` — สถานะอ่าน/ยังไม่อ่าน ต่อผู้ใช้
| field | เก็บอะไร |
|---|---|
| `announcement` | ประกาศไหน |
| `user` | ใครอ่าน |
| `read_at` | อ่านเมื่อไหร่ |

---

## 📁 notifications

### `Notification` — แจ้งเตือนรายบุคคลจาก event ระบบ (web ล้วน ไม่ส่งออกนอก)
| field | เก็บอะไร |
|---|---|
| `recipient` | ผู้รับ (นักศึกษา/ครู) |
| `notification_type` | ชนิด event: `submission_graded` / `quiz_graded` / `assignment_published` / `quiz_published` / `announcement_posted` / `due_soon` / `enrolled` |
| `context` | พารามิเตอร์สำหรับประกอบข้อความ (JSON) เช่น `{"course_name": "...", "score": 8}` |
| `link_url` | path ในเว็บที่กดแล้วไป เช่น `/courses/12/assignments/5` |
| `is_read` | อ่านแล้วไหม |
| `read_at` | อ่านเมื่อไหร่ |
| `created_at` | เกิดเมื่อไหร่ (มี index) |

---

## 📁 audit

### `AuditLog` — บันทึกการกระทำทั้งระบบ
| field | เก็บอะไร |
|---|---|
| `actor` | ใครทำ (ว่าง = ระบบทำเอง) |
| `impersonated_by` | Admin ตัวจริงเบื้องหลัง (ถ้าอยู่โหมดสวมสิทธิ์) |
| `action` | `create` / `update` / `delete` / `login` / `logout` / `impersonate_start` / `impersonate_end` / `publish` / `enroll` / `unenroll` / `regrade` |
| `content_type` | ทำกับตารางไหน |
| `object_id` | ทำกับแถวไหน (pk) |
| `object_repr` | ข้อความอ่านออกของแถวนั้น ณ ตอนนั้น |
| `changes` | อะไรเปลี่ยนบ้าง `{"field": [ค่าเก่า, ค่าใหม่]}` (JSON) |
| `context` | IP, user-agent, path ฯลฯ (JSON) |
| `created_at` | เกิดเมื่อไหร่ (มี index) |

---

## 📁 common (abstract — ไม่ใช่ตารางจริง)

| ตัว | field ที่ให้ | ใช้ทำอะไร |
|---|---|---|
| `TimeStampedModel` | `created_at`, `updated_at` | ทุกตาราง inherit |
| `Auditable` | (ไม่มี field) | marker ให้ signal เขียน `AuditLog` อัตโนมัติเมื่อ save/delete |
| `SoftDeleteModel` | `deleted_at`, `deleted_by` | ใช้กับ `Submission`, `QuizAttempt`, `Score` — `.delete()` = ซ่อน ไม่ลบจริง |

---

**รวม 25 ตารางจริง ใน 10 แอป** (+ common abstracts)

> soft-delete 3 ตาราง (`Submission`, `QuizAttempt`, `Score`) ใช้ `UniqueConstraint` แบบ `condition=Q(deleted_at__isnull=True)`
> **v1.3**: `*.student` / `Score.grade_item` / `GradeItem.category` / `QuizAttempt.quiz` / `Submission.assignment` = `PROTECT` ; User ที่มีประวัติ = ปิด `is_active` ไม่ลบจริง ; sync คะแนน attempt/submission → Score ผ่าน signal
> ตารางที่จะเพิ่มทีหลัง (ดู `database.md` §13): `ContentProgress`, `QuizException`, `AssignmentGroup(+Member)`
