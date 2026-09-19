import { sendRequest } from '../lib/httpCore'

// เรียก API สมัคร / ยืนยันอีเมล / ลืมรหัสผ่าน (สัญญาที่ docs/api-auth.md)
// ทุกตัวเป็นคำขอที่ไม่ต้องล็อกอินและไม่แตะสถานะล็อกอิน ไม่ล็อกอินให้ และไม่ต้องมี access token
// สำเร็จ: คืนเนื้อหา JSON | ไม่สำเร็จ: โยน ApiError (ใช้ error.code แปลข้อความ)

export type RegisterInput = {
  email: string
  password: string
  first_name: string
  last_name: string
}

// สมัครเองด้วยอีเมล (ได้ผู้เรียนที่ยังไม่ยืนยันอีเมล) — 202 เมื่อรับเรื่องแล้ว, 409 email_taken ถ้ามีบัญชีแล้ว
export function registerAccount(input: RegisterInput): Promise<void> {
  return sendRequest<void>('/api/auth/register/', { method: 'POST', body: input })
}

// ยืนยันอีเมลด้วยโทเคนจากลิงก์ (ใช้ POST เพราะโปรแกรมสแกนอีเมลเปิดลิงก์ GET ล่วงหน้าได้)
export function verifyEmail(token: string): Promise<void> {
  return sendRequest<void>('/api/auth/verify-email/', { method: 'POST', body: { token } })
}

// ขอลิงก์ยืนยันอีเมลใหม่ — backend ตอบ 202 เหมือนกันทุกกรณี (ไม่บอกว่ามีอีเมลนี้หรือไม่)
export function resendVerification(email: string): Promise<void> {
  return sendRequest<void>('/api/auth/resend-verification/', { method: 'POST', body: { email } })
}

// ขอลิงก์ตั้งรหัสผ่านใหม่ — backend ตอบ 202 เหมือนกันทุกกรณี
export function requestPasswordReset(email: string): Promise<void> {
  return sendRequest<void>('/api/auth/forgot-password/', { method: 'POST', body: { email } })
}

// ตรวจลิงก์ตั้งรหัสผ่านโดยไม่ใช้โทเคนทิ้ง แล้วคืนอีเมลของบัญชีที่จะตั้งรหัสให้
export async function checkResetToken(token: string): Promise<string> {
  const result = await sendRequest<{ email: string }>('/api/auth/reset-password/check/', {
    method: 'POST',
    body: { token },
  })
  return result.email
}

// ตั้งรหัสผ่านใหม่ด้วยโทเคนจากลิงก์ (ไม่ล็อกอินให้ และเซสชันเดิมทั้งหมดของบัญชีนั้นใช้ไม่ได้)
export function resetPassword(token: string, password: string): Promise<void> {
  return sendRequest<void>('/api/auth/reset-password/', {
    method: 'POST',
    body: { token, password },
  })
}
