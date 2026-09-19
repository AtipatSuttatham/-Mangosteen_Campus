import type { Role } from '../types/auth'

export type DashboardConfig = {
  /** กุญแจแปลบรรทัดใต้คำทักทาย */
  subtitleKey: string
  /** ตัวเลขสำคัญ 3 ตัว (เรียงตามแบบ) — highlight = ตัวเลขสีม่วงเน้น */
  figures: Array<{ labelKey: string; highlight?: boolean }>
  /** หัวข้อรายการหลัก (คอลัมน์ซ้าย กว้างกว่า) */
  primaryTitleKey: string
  /** รายการรอง (คอลัมน์ขวา): shortcuts = ทางลัดไปเมนูอื่น, list = รายการข้อมูล */
  secondary: { titleKey: string; kind: 'shortcuts' | 'list' }
}

// เนื้อหา dashboard ของแต่ละบทบาท ตาม wireframe (ตัวเลข/รายการจริงจะเติมเมื่อมี API ของฟีเจอร์นั้น)
export const DASHBOARD: Record<Role, DashboardConfig> = {
  admin: {
    subtitleKey: 'dashboard.admin.subtitle',
    figures: [
      { labelKey: 'dashboard.admin.figures.teachers' },
      { labelKey: 'dashboard.admin.figures.students' },
      { labelKey: 'dashboard.admin.figures.courses', highlight: true },
    ],
    primaryTitleKey: 'dashboard.admin.primary',
    secondary: { titleKey: 'dashboard.admin.secondary', kind: 'shortcuts' },
  },
  teacher: {
    subtitleKey: 'dashboard.teacher.subtitle',
    figures: [
      { labelKey: 'dashboard.teacher.figures.courses' },
      { labelKey: 'dashboard.teacher.figures.students' },
      { labelKey: 'dashboard.teacher.figures.toGrade', highlight: true },
    ],
    primaryTitleKey: 'dashboard.teacher.primary',
    secondary: { titleKey: 'dashboard.teacher.secondary', kind: 'list' },
  },
  student: {
    subtitleKey: 'dashboard.student.subtitle',
    figures: [
      { labelKey: 'dashboard.student.figures.courses' },
      { labelKey: 'dashboard.student.figures.dueThisWeek', highlight: true },
      { labelKey: 'dashboard.student.figures.unreadAnnouncements' },
    ],
    primaryTitleKey: 'dashboard.student.primary',
    secondary: { titleKey: 'dashboard.student.secondary', kind: 'list' },
  },
}

// ทางลัดของผู้ดูแลระบบ (เลือกจากเมนูใน navConfig ตามลำดับในแบบ)
export const ADMIN_SHORTCUT_KEYS = ['users', 'support', 'impersonate', 'audit']
