import { homePathForRole } from '../auth/roles'
import type { IconName } from '../components/Icon'
import type { Role } from '../types/auth'

export type NavItem = {
  key: string
  icon: IconName
  /** กุญแจแปลชื่อเมนู */
  labelKey: string
  /** เส้นทางปลายทาง — ไม่ระบุ = ฟีเจอร์นี้ยังไม่เปิดใช้งาน (แสดงตามแบบแต่กดไม่ได้) */
  to?: string
}

function dashboard(role: Role): NavItem {
  return { key: 'dashboard', icon: 'grid', labelKey: 'nav.dashboard', to: homePathForRole(role) }
}

// เมนูของแต่ละบทบาท ตาม wireframe (เพิ่ม `to` เมื่อทำหน้านั้นเสร็จ)
export const NAV_ITEMS: Record<Role, NavItem[]> = {
  admin: [
    dashboard('admin'),
    { key: 'users', icon: 'users', labelKey: 'nav.users' },
    { key: 'terms', icon: 'calendar', labelKey: 'nav.terms' },
    { key: 'support', icon: 'wrench', labelKey: 'nav.support' },
    { key: 'impersonate', icon: 'switch', labelKey: 'nav.impersonate' },
    { key: 'audit', icon: 'clock', labelKey: 'nav.audit' },
  ],
  teacher: [dashboard('teacher'), { key: 'courses', icon: 'book', labelKey: 'nav.myCourses' }],
  student: [
    dashboard('student'),
    { key: 'courses', icon: 'book', labelKey: 'nav.myCourses' },
    { key: 'announcements', icon: 'megaphone', labelKey: 'nav.announcements' },
  ],
}

// แถบเมนูล่างบนมือถือรองรับได้ไม่เกิน 3 รายการ — เกินกว่านี้ใช้ปุ่มเมนูเปิดลิ้นชักแทน
const MAX_BOTTOM_NAV_ITEMS = 3

export function usesDrawer(role: Role): boolean {
  return NAV_ITEMS[role].length > MAX_BOTTOM_NAV_ITEMS
}
