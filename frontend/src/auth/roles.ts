import type { Role } from '../types/auth'

// หน้าแรก (dashboard) ของแต่ละบทบาท — ล็อกอินแล้วพาไปที่นี่ และผิดบทบาทจะถูกส่งกลับมาที่นี่
const HOME_PATH: Record<Role, string> = {
  admin: '/admin',
  teacher: '/teacher',
  student: '/student',
}

export function homePathForRole(role: Role): string {
  return HOME_PATH[role]
}
