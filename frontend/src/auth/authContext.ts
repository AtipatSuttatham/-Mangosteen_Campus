import { createContext } from 'react'

import type { User } from '../types/auth'

// loading = กำลังกู้เซสชันตอนเปิดเว็บ (ยังไม่รู้ว่าล็อกอินอยู่ไหม)
export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export type AuthContextValue = {
  status: AuthStatus
  /** ผู้ใช้ที่ล็อกอินอยู่ (null ถ้ายังไม่ล็อกอินหรือกำลังโหลด) */
  user: User | null
  /** เข้าสู่ระบบ — ล้มเหลวจะโยน ApiError (ใช้ error.code แปลข้อความ) */
  login: (identifier: string, password: string) => Promise<void>
  /** ออกจากระบบ — ล้างสถานะในหน้าเว็บเสมอ */
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
