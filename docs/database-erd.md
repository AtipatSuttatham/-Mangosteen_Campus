# ERD — LMS (Mermaid) · v1.4

> ประกอบกับ [`database.md`](./database.md) — แยก diagram ตามโดเมนเพื่อให้อ่านง่าย
> GitHub render Mermaid ในไฟล์ `.md` ได้โดยตรง

## ภาพรวมความสัมพันธ์หลัก

```mermaid
erDiagram
    TERM        ||--o{ COURSE            : "มี"
    COURSE      ||--o{ COURSE_TEACHER    : "ผู้สอน (M2M)"
    USER        ||--o{ COURSE_TEACHER    : ""
    COURSE      ||--o{ ENROLLMENT        : "ผู้เรียน (M2M)"
    USER        ||--o{ ENROLLMENT        : ""
    COURSE      ||--o{ MODULE            : "มี"
    MODULE      ||--o{ CONTENT           : "มี"
    MODULE      ||--o{ QUIZ              : "แบบฝึกหัดท้ายบท"
    COURSE      ||--o{ QUIZ              : ""
    COURSE      ||--o{ ASSIGNMENT        : ""
    COURSE      ||--o{ GRADING_CATEGORY  : ""
    COURSE      ||--o{ GRADE_ITEM        : ""
    COURSE      ||--o{ ANNOUNCEMENT      : ""
    QUIZ        ||--o| GRADE_ITEM        : "auto-create (is_graded, PROTECT)"
    ASSIGNMENT  ||--o| GRADE_ITEM        : "auto-create (is_graded, PROTECT)"
    GRADING_CATEGORY ||--o{ GRADE_ITEM   : "จัดหมวด"
    GRADE_ITEM  ||--o{ SCORE             : ""
    USER        ||--o{ SCORE             : ""
    USER        ||--o{ NOTIFICATION      : "recipient"
    USER        ||--o{ AUDIT_LOG         : "actor"
```

> ชื่อ/หัวข้อทุกตารางเป็น **field เดียว** (ไม่แยก `_th` / `_en`) — i18n = UI chrome เท่านั้น
> `SUBMISSION` / `QUIZ_ATTEMPT` / `SCORE` = soft delete (`deleted_at`, `deleted_by`) + unique constraint แบบ `WHERE deleted_at IS NULL`
> hard-delete จริงได้เฉพาะ draft ที่ไม่เคย publish + ไม่มีข้อมูลนักศึกษา
> **v1.3**: FK เข้าสู่ระบบคะแนนใช้ `PROTECT` ทั้งหมด — `*.student`, `Score.grade_item`, `GradeItem.category/quiz/assignment`, `QuizAttempt.quiz`, `Submission.assignment` ; **User ที่มีประวัติ = ปิด `is_active` ไม่ลบจริง**

## 1. Accounts / Academics / Enrollment

```mermaid
erDiagram
    USER {
        bigint   id PK
        string   email UK
        string   student_or_staff_id UK "nullable"
        string   role "admin|teacher|student"
        string   first_name
        string   last_name
        string   first_name_en "nullable"
        string   last_name_en "nullable"
        bool     is_email_verified
        bool     is_active
        string   avatar_url "nullable"
        bigint   created_by FK "nullable"
    }
    EMAIL_VERIFICATION_TOKEN {
        bigint   id PK
        bigint   user_id FK
        string   token_hash UK "SHA-256 ของโทเคน"
        string   purpose "verify_email|reset_password"
        datetime expires_at
        datetime used_at "nullable"
    }
    TERM {
        bigint   id PK
        int      academic_year
        smallint semester "1|2|3"
        string   name "1/2568"
        date     start_date
        date     end_date
        bool     is_current
    }
    COURSE {
        bigint   id PK
        bigint   term_id FK
        string   code
        string   section "nullable"
        string   name
        text     description
        bool     self_enroll_enabled
        string   invite_code UK "nullable"
        bool     is_published
        bigint   created_by FK
    }
    COURSE_TEACHER {
        bigint   id PK
        bigint   course_id FK
        bigint   user_id FK
        string   course_role "owner|co_teacher|ta"
        bigint   added_by FK "nullable"
    }
    ENROLLMENT {
        bigint   id PK
        bigint   course_id FK
        bigint   student_id FK
        string   status "invited|active|dropped|completed"
        string   method "admin_assigned|self_enrolled"
        bigint   enrolled_by FK "nullable"
        datetime enrolled_at
        datetime dropped_at "nullable"
    }

    USER ||--o{ EMAIL_VERIFICATION_TOKEN : ""
    USER ||--o{ USER : "created_by"
    TERM ||--o{ COURSE : ""
    COURSE ||--o{ COURSE_TEACHER : ""
    USER   ||--o{ COURSE_TEACHER : ""
    COURSE ||--o{ ENROLLMENT : ""
    USER   ||--o{ ENROLLMENT : "student"
```

## 2. Content

```mermaid
erDiagram
    COURSE {
        bigint id PK
    }
    MODULE {
        bigint id PK
        bigint course_id FK
        string title
        text   description
        int    order
        bool   is_published
    }
    CONTENT {
        bigint   id PK
        bigint   module_id FK
        string   title
        string   content_type "text|file|image|video|audio|link"
        text     body
        int      order
        bool     is_published
        datetime available_from "nullable"
        string   file_url "nullable"
        string   file_name "nullable"
        int      file_size "nullable"
        string   mime_type "nullable"
        string   video_source "cloudinary|youtube (nullable)"
        string   video_url "nullable"
        string   external_url "nullable"
    }
    COURSE ||--o{ MODULE  : ""
    MODULE ||--o{ CONTENT : ""
```

## 3. Assessments (Quiz)

```mermaid
erDiagram
    QUIZ {
        bigint   id PK
        bigint   course_id FK
        bigint   module_id FK "nullable"
        bigint   grading_category_id FK "nullable"
        string   title
        bool     is_graded "default true"
        decimal  max_score
        bool     is_timed
        int      time_limit_minutes "nullable"
        string   attempt_policy "single|multiple_highest"
        int      max_attempts "nullable"
        datetime available_from "nullable"
        datetime available_until "nullable"
        bool     shuffle_questions
        string   show_correct_answers "never|after_submit|after_close"
        bool     is_published
    }
    QUESTION {
        bigint   id PK
        bigint   quiz_id FK
        string   question_type "mcq|true_false|matching|dropdown|short_answer"
        text     text
        int      order
        decimal  points
        text     explanation
        bool     shuffle_choices
        json     accepted_answers "nullable (short_answer)"
        bool     manual_grading "short_answer"
    }
    CHOICE {
        bigint   id PK
        bigint   question_id FK
        string   text
        bool     is_correct
        int      order
    }
    MATCHING_PAIR {
        bigint   id PK
        bigint   question_id FK
        string   left_text
        string   right_text
        int      order
    }
    QUIZ_ATTEMPT {
        bigint   id PK
        bigint   quiz_id FK "PROTECT"
        bigint   student_id FK "PROTECT"
        int      attempt_number
        string   status "in_progress|submitted|auto_submitted|graded"
        datetime started_at
        datetime due_at "nullable (snapshot)"
        datetime submitted_at "nullable"
        decimal  score "nullable"
        decimal  max_score "snapshot"
        bigint   graded_by FK "nullable"
        datetime deleted_at "nullable (soft delete)"
    }
    ANSWER {
        bigint   id PK
        bigint   attempt_id FK
        bigint   question_id FK
        json     response "canonical"
        bigint   selected_choice_id FK "nullable"
        bool     is_correct "nullable"
        decimal  points_awarded "nullable"
        text     feedback
        bigint   graded_by FK "nullable"
    }

    QUIZ         ||--o{ QUESTION      : ""
    QUESTION     ||--o{ CHOICE        : "mcq/true_false/dropdown"
    QUESTION     ||--o{ MATCHING_PAIR : "matching"
    QUIZ         ||--o{ QUIZ_ATTEMPT  : ""
    QUIZ_ATTEMPT ||--o{ ANSWER        : ""
    QUESTION     ||--o{ ANSWER        : ""
    CHOICE       ||--o{ ANSWER        : "selected_choice"
```

## 4. Assignments

```mermaid
erDiagram
    ASSIGNMENT {
        bigint   id PK
        bigint   course_id FK
        bigint   module_id FK "nullable"
        bigint   grading_category_id FK "nullable"
        string   title
        bool     is_graded "default true"
        text     description
        decimal  max_score
        datetime due_at "nullable"
        datetime accept_until "nullable (hard deadline)"
        string   late_policy "closed_after_due|accept_with_penalty"
        decimal  penalty_percent_per_day "nullable"
        decimal  penalty_max_percent "nullable"
        bool     allow_resubmission
        json     allowed_file_types "nullable"
        int      max_file_size_mb "nullable"
        int      max_files
        bool     is_published
    }
    ASSIGNMENT_ATTACHMENT {
        bigint   id PK
        bigint   assignment_id FK
        string   file_url
        string   file_name
        int      file_size
        string   mime_type
    }
    SUBMISSION {
        bigint   id PK
        bigint   assignment_id FK "PROTECT"
        bigint   student_id FK "PROTECT"
        int      attempt_number
        bool     is_latest
        string   status "draft|submitted|graded|returned"
        datetime submitted_at "nullable"
        bool     is_late
        int      days_late
        text     text_response
        decimal  raw_score "nullable"
        decimal  penalty_applied_percent "nullable"
        decimal  final_score "nullable"
        text     feedback
        bigint   graded_by FK "nullable"
        datetime deleted_at "nullable (soft delete)"
    }
    SUBMISSION_FILE {
        bigint   id PK
        bigint   submission_id FK
        string   file_url
        string   file_name
        int      file_size
        string   mime_type
    }

    ASSIGNMENT ||--o{ ASSIGNMENT_ATTACHMENT : ""
    ASSIGNMENT ||--o{ SUBMISSION            : ""
    SUBMISSION ||--o{ SUBMISSION_FILE       : ""
```

## 5. Grading

```mermaid
erDiagram
    COURSE {
        bigint id PK
    }
    GRADING_CATEGORY {
        bigint  id PK
        bigint  course_id FK
        string  name
        decimal weight_percent
        int     order
    }
    GRADE_ITEM {
        bigint  id PK
        bigint  course_id FK
        bigint  category_id FK "nullable, PROTECT"
        string  title
        decimal max_score
        string  source_type "quiz|assignment|manual"
        bigint  quiz_id FK "nullable, PROTECT"
        bigint  assignment_id FK "nullable, PROTECT"
        decimal weight_within_category "nullable"
        bool    is_published
        int     order
    }
    SCORE {
        bigint  id PK
        bigint  grade_item_id FK "PROTECT"
        bigint  student_id FK "PROTECT"
        decimal raw_score "nullable"
        decimal adjusted_score "nullable"
        text    comment
        bigint  source_attempt_id FK "nullable"
        bigint  source_submission_id FK "nullable"
        bigint  updated_by FK
        datetime deleted_at "nullable (soft delete)"
    }
    COURSE_GRADE {
        bigint  id PK
        bigint  course_id FK
        bigint  student_id FK
        decimal weighted_total_percent
        json    breakdown
        datetime computed_at
    }

    COURSE           ||--o{ GRADING_CATEGORY : ""
    COURSE           ||--o{ GRADE_ITEM       : ""
    GRADING_CATEGORY ||--o{ GRADE_ITEM       : ""
    GRADE_ITEM       ||--o{ SCORE            : ""
    COURSE           ||--o{ COURSE_GRADE     : ""
```

## 6. Announcements / Notifications / Audit

```mermaid
erDiagram
    COURSE {
        bigint id PK
    }
    USER {
        bigint id PK
    }
    ANNOUNCEMENT {
        bigint   id PK
        bigint   course_id FK
        bigint   author_id FK
        string   title
        text     body
        bool     is_pinned
        bool     is_published
        datetime published_at "nullable"
    }
    ANNOUNCEMENT_READ {
        bigint   id PK
        bigint   announcement_id FK
        bigint   user_id FK
        datetime read_at
    }
    NOTIFICATION {
        bigint   id PK
        bigint   recipient_id FK
        string   notification_type "submission_graded|assignment_published|due_soon|..."
        json     context "params for i18n render"
        string   link_url "SPA path"
        bool     is_read
        datetime read_at "nullable"
        datetime created_at "index"
    }
    AUDIT_LOG {
        bigint   id PK
        bigint   actor_id FK "nullable"
        bigint   impersonated_by FK "nullable"
        string   action "create|update|delete|login|logout|impersonate_*|publish|enroll|unenroll|regrade"
        int      content_type_id FK "nullable"
        string   object_id "nullable, index(content_type,object_id)"
        string   object_repr
        json     changes "nullable"
        json     context "nullable"
        datetime created_at "index"
    }

    COURSE       ||--o{ ANNOUNCEMENT      : ""
    USER         ||--o{ ANNOUNCEMENT      : "author"
    ANNOUNCEMENT ||--o{ ANNOUNCEMENT_READ : ""
    USER         ||--o{ ANNOUNCEMENT_READ : ""
    USER         ||--o{ NOTIFICATION      : "recipient"
    USER         ||--o{ AUDIT_LOG         : "actor"
```

> `NOTIFICATION` = web ล้วนใน MVP (ไม่มี email/push) — ระบบสร้าง 1 แถว/ผู้รับ trigger จาก event
