import type { ReactNode } from 'react'

import { Icon, type IconName } from './Icon'

// โทนของวงกลมไอคอน: info = ม่วงอ่อน (รอทำต่อ), success = เขียว (สำเร็จ), warn = เหลือง (ลิงก์ใช้ไม่ได้/เตือน)
const TONES = {
  info: 'bg-plum-50 text-plum-800',
  success: 'bg-ok-50 text-ok-800',
  warn: 'bg-warn-50 text-warn-800',
} as const

type StatusCardProps = {
  tone: keyof typeof TONES
  icon: IconName
  /** หัวข้อของหน้า (h1) */
  title: string
  children?: ReactNode
}

// เนื้อหาหน้าสถานะ (ตรวจสอบอีเมล / ยืนยันแล้ว / ลิงก์ใช้ไม่ได้ ฯลฯ) ตาม wireframe:
// วงกลมไอคอน + หัวข้อ + ข้อความ + ปุ่ม — วางในโครงหน้า AuthLayout ไม่มีเส้นขอบการ์ด
export function StatusCard({ tone, icon, title, children }: StatusCardProps) {
  return (
    <div className="flex flex-col gap-3.5">
      <div className={`flex size-[46px] items-center justify-center rounded-full ${TONES[tone]}`}>
        <Icon name={icon} size={22} />
      </div>
      <h1 className="font-serif text-[22px] leading-[1.4] font-semibold text-ink">{title}</h1>
      {children}
    </div>
  )
}
