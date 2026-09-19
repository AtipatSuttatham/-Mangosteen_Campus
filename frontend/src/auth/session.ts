import { ApiError } from '../lib/apiError'
import { sendRequest } from '../lib/httpCore'
import type { Session, User } from '../types/auth'

// ---------- access token: เก็บในหน่วยความจำเท่านั้น ----------
// ไม่ใช้ localStorage / sessionStorage / cookie ที่โค้ดอ่านได้ เพื่อกัน XSS ขโมย token
// (refresh token อยู่ใน httpOnly cookie ที่โค้ดหน้าเว็บอ่านไม่ได้เลย)
let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

// ---------- สัญญาณเมื่อเซสชันเปลี่ยน (AuthProvider ฟังอยู่) ----------
export type SessionEvent = { type: 'refreshed'; user: User } | { type: 'lost' }

const listeners = new Set<(event: SessionEvent) => void>()

// สมัครรับสัญญาณ คืนฟังก์ชันสำหรับยกเลิก
export function subscribeToSession(listener: (event: SessionEvent) => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function emit(event: SessionEvent): void {
  listeners.forEach((listener) => listener(event))
}

// เก็บเซสชันใหม่ (หลัง login หรือ refresh สำเร็จ) และแจ้งผู้ที่ฟังอยู่
export function storeSession(session: Session): void {
  accessToken = session.access
  emit({ type: 'refreshed', user: session.user })
}

// ล้างเซสชัน (ออกจากระบบ หรือ refresh token ใช้ไม่ได้แล้ว) และแจ้งผู้ที่ฟังอยู่
export function clearSession(): void {
  accessToken = null
  emit({ type: 'lost' })
}

// header ที่ backend บังคับสำหรับคำขอที่ใช้ cookie (refresh / logout) — เหตุผลดู docs/api-auth.md
const COOKIE_REQUEST_HEADERS = { 'X-Requested-With': 'fetch' }

// ---------- เข้าสู่ระบบ / ออกจากระบบ ----------
// ช่องเดียวรับทั้งรหัสนักศึกษา/พนักงานและอีเมล (backend แยกด้วยอักขระ @)
export async function loginWithPassword(identifier: string, password: string): Promise<Session> {
  const session = await sendRequest<Session>('/api/auth/login/', {
    method: 'POST',
    body: { identifier, password },
  })
  storeSession(session)
  return session
}

// ออกจากระบบ: ล้างเซสชันในหน้าเว็บเสมอ แม้ backend ตอบไม่สำเร็จ
// คืน true ถ้า backend เพิกถอน refresh token ให้แล้ว, false ถ้าไม่สำเร็จ (เช่นเครือข่ายล่ม → cookie ยังอยู่จนหมดอายุ)
export async function logout(): Promise<boolean> {
  let revoked = true
  try {
    await sendRequest<void>('/api/auth/logout/', {
      method: 'POST',
      headers: COOKIE_REQUEST_HEADERS,
    })
  } catch {
    revoked = false
  } finally {
    clearSession()
  }
  return revoked
}

// ---------- ขอ access token ใหม่ ----------
async function requestRefresh(): Promise<Session | null> {
  try {
    const session = await sendRequest<Session>('/api/auth/refresh/', {
      method: 'POST',
      headers: COOKIE_REQUEST_HEADERS,
    })
    storeSession(session)
    return session
  } catch (error) {
    // 401 = ไม่มี/หมดอายุ/ถูกเพิกถอน refresh token → ยังไม่ได้ล็อกอิน (ไม่ใช่ข้อผิดพลาด)
    if (error instanceof ApiError && error.status === 401) {
      clearSession()
      return null
    }
    // ปัญหาอื่น (เช่นเครือข่ายล่ม) ไม่ล้างเซสชัน — ส่งต่อให้ผู้เรียกตัดสินใจ
    throw error
  }
}

// refresh token ใช้ได้ครั้งเดียว (ใบเก่าถูกเพิกถอนทุกครั้งที่แลก) จึงต้องมีคำขอ refresh ทีละ 1 คำขอเท่านั้น
// ไม่งั้นสองคำขอที่ชนกันจะใช้ใบเดียวกัน คำขอที่สองพังและผู้ใช้ถูกเด้งออก
// - ในแท็บเดียวกัน: คำขอที่เข้ามาระหว่างรอ ใช้ผลของคำขอเดียวกัน
// - ข้ามแท็บ: ใช้ Web Locks ให้ทีละแท็บ (แท็บที่มาทีหลังจะอ่าน cookie ใบใหม่ที่แท็บแรกเพิ่งได้)
let refreshInFlight: Promise<Session | null> | null = null

export function refreshSession(): Promise<Session | null> {
  if (!refreshInFlight) {
    const locks = typeof navigator === 'undefined' ? undefined : navigator.locks
    const run = locks
      ? locks.request('mangosteen-auth-refresh', requestRefresh)
      : requestRefresh()
    refreshInFlight = run.finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}
