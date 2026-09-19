// ต่อชื่อ class เฉพาะส่วนที่มีค่า (ใช้กับเงื่อนไข เช่น cx('a', active && 'b'))
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
