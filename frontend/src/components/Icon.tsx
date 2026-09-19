import type { ReactNode } from 'react'

// ชุดไอคอนเส้นที่ wireframe ใช้ (กรอบ 24x24 เส้นหนา 1.6 ปลายมน) — ไม่เพิ่มไลบรารีไอคอน
export type IconName =
  | 'grid'
  | 'users'
  | 'calendar'
  | 'wrench'
  | 'switch'
  | 'clock'
  | 'book'
  | 'megaphone'
  | 'bell'
  | 'logout'
  | 'menu'
  | 'close'

const SHAPES: Record<IconName, ReactNode> = {
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 20c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5" />
      <circle cx="17.5" cy="8.5" r="2.4" />
      <path d="M15.8 14.8c2.6.3 4.5 2.3 4.7 5.2" />
    </>
  ),
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </>
  ),
  wrench: <path d="M14.7 6.3a4 4 0 0 0-5.4 4.6L4 16.2V20h3.8l5.3-5.3a4 4 0 0 0 4.6-5.4l-2.6 2.6-2-2z" />,
  switch: (
    <>
      <path d="M4 7h13l-3-3" />
      <path d="M20 17H7l3 3" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  book: (
    <>
      <path d="M4 5.5A2 2 0 0 1 6 4h5v16H6a2 2 0 0 1-2-2z" />
      <path d="M20 5.5A2 2 0 0 0 18 4h-5v16h5a2 2 0 0 0 2-2z" />
    </>
  ),
  megaphone: (
    <>
      <path d="M3 10v4a1 1 0 0 0 1 1h2l5 4V5l-5 4H4a1 1 0 0 0-1 1z" />
      <path d="M17 8.5a4.5 4.5 0 0 1 0 7" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z" />
      <path d="M10 20.5a2 2 0 0 0 4 0" />
    </>
  ),
  logout: (
    <>
      <path d="M9 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H9" />
      <path d="M15 16l4-4-4-4" />
      <path d="M19 12H9" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
}

type IconProps = {
  name: IconName
  size?: number
  className?: string
}

// ไอคอนประดับ (ข้อความอยู่ข้างเคียงเสมอ) จึงซ่อนจาก screen reader — สีตาม text-* ของที่ครอบ
export function Icon({ name, size = 18, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {SHAPES[name]}
    </svg>
  )
}
