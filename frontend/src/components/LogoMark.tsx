// กลีบเดียวของตราดอก (วาดในกรอบ 48x48 ตรงกับ wireframe)
const PETAL = 'M24 6 C29 13 29 20 24 25 C19 20 19 13 24 6 Z'
// หมุนกลีบทุก 60 องศาให้ครบ 6 กลีบรอบจุดกึ่งกลาง
const ANGLES = [0, 60, 120, 180, 240, 300]

type LogoMarkProps = {
  /** ขนาดเป็นพิกเซล */
  size?: number
  /** ใช้กำหนดสีผ่าน text-* (ตราใช้สี currentColor) */
  className?: string
}

// ตราดอก 6 กลีบ (กลีบเลี้ยงมังคุด) — โลโก้ของระบบ เป็นภาพประดับจึงซ่อนจาก screen reader
export function LogoMark({ size = 26, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      {ANGLES.map((angle) => (
        <path key={angle} d={PETAL} transform={`rotate(${angle} 24 24)`} />
      ))}
      <circle cx="24" cy="24" r="3.4" />
    </svg>
  )
}

// ตราดอกแบบเส้น (ไม่มีสีเติม) ใช้เป็นลายใหญ่ประดับพื้นหลัง — ขนาดและตำแหน่งกำหนดผ่าน className
export function CalyxOutline({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="0.35"
      aria-hidden="true"
      className={className}
    >
      {ANGLES.map((angle) => (
        <path key={angle} d={PETAL} transform={`rotate(${angle} 24 24)`} />
      ))}
      <circle cx="24" cy="24" r="3.4" />
    </svg>
  )
}
