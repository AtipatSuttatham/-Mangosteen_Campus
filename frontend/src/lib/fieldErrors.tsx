import type { TFunction } from 'i18next'
import type { ReactNode } from 'react'

// แปลรหัสกฎที่ไม่ผ่านของช่องหนึ่ง (จาก ApiError.errorCodes) เป็นข้อความใต้ช่อง — ไม่มีรหัส = ไม่มีข้อผิดพลาด (undefined)
// รหัสที่ไม่รู้จักใช้ข้อความทั่วไป และไม่แสดงข้อความดิบจาก backend (ตามสัญญาที่ docs/api-auth.md)
export function fieldErrorNode(t: TFunction, codes: string[] | undefined): ReactNode {
  if (!codes || codes.length === 0) return undefined
  const messages = [...new Set(codes)].map((code) =>
    t(`fieldErrors.${code}`, { defaultValue: t('fieldErrors.unknown') }),
  )
  // หลายกฎในช่องเดียว (เช่นรหัสผ่านผิดหลายข้อ) แสดงบรรทัดละข้อ
  return messages.map((message) => (
    <span key={message} className="block">
      {message}
    </span>
  ))
}
