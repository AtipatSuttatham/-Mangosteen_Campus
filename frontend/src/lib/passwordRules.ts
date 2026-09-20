// กฎของรหัสผ่านที่หน้าเว็บตรวจเองได้ทันทีตอนพิมพ์ (ใช้กับหน้าตั้งรหัสผ่านใหม่)
// ตรงกับตัวตรวจฝั่ง backend (AUTH_PASSWORD_VALIDATORS) เฉพาะสองข้อที่ไม่ต้องใช้ข้อมูลฝั่งเซิร์ฟเวอร์
// backend ยังเป็นผู้ตัดสินจริงเสมอ — กฎอื่น (รหัสที่คนใช้กัน / คล้ายชื่อหรืออีเมล) ตรวจเฉพาะที่ backend

// จำนวนตัวอักษรขั้นต่ำ (ตรงกับ MinimumLengthValidator)
export const MIN_PASSWORD_LENGTH = 8

// ตัวเลขล้วน (ตรงกับ NumericPasswordValidator: นับเลขทุกภาษา เช่นเลขไทยด้วย)
const ONLY_DIGITS = /^\p{Nd}+$/u

// นับเป็น "ตัวอักษร" แบบเดียวกับ backend (Python นับทีละอักขระ) ไม่ใช่ .length ของ JavaScript ที่นับเป็นหน่วย UTF-16
// (อีโมจิหนึ่งตัวจึงนับ 2 ถ้าใช้ .length) — กันหน้าเว็บกับ backend เห็นไม่ตรงกัน
export function characterCount(value: string): number {
  return [...value].length
}

export type PasswordRule = {
  /** กุญแจข้อความของกฎนี้ในไฟล์แปลภาษา */
  labelKey: 'reset.ruleLength' | 'reset.ruleNotNumeric'
  /** รหัสกฎของ backend ที่ตรงกัน (ไว้ทำเครื่องหมายว่าไม่ผ่านเมื่อ backend ปฏิเสธ) */
  backendCode: string
  met: (password: string) => boolean
}

export const PASSWORD_RULES: readonly PasswordRule[] = [
  {
    labelKey: 'reset.ruleLength',
    backendCode: 'password_too_short',
    met: (password) => characterCount(password) >= MIN_PASSWORD_LENGTH,
  },
  {
    labelKey: 'reset.ruleNotNumeric',
    backendCode: 'password_entirely_numeric',
    // ช่องว่างเปล่ายังไม่นับว่าผ่าน (ไม่ให้ติ๊กเขียวก่อนพิมพ์อะไร)
    met: (password) => password.length > 0 && !ONLY_DIGITS.test(password),
  },
]

// รหัสผ่านผ่านทุกกฎที่ตรวจได้ในหน้าเว็บหรือยัง (ผ่านแล้วค่อยส่งให้ backend ตัดสิน)
export function meetsPasswordRules(password: string): boolean {
  return PASSWORD_RULES.every((rule) => rule.met(password))
}
