// บทบาทระดับระบบ (ตรงกับ backend: accounts/roles.py)
export type Role = 'admin' | 'teacher' | 'student'

// ข้อมูลผู้ใช้ที่ backend ส่งมา (ตรงกับ accounts/serializers.py → UserSerializer)
export type User = {
  id: number
  email: string
  student_or_staff_id: string | null
  role: Role
  first_name: string
  last_name: string
  first_name_en: string
  last_name_en: string
  is_email_verified: boolean
  avatar_url: string
}

// ผลของ login / refresh: access token (เก็บในหน่วยความจำ) + ข้อมูลผู้ใช้ล่าสุด
export type Session = {
  access: string
  user: User
}
