import { useEffect, useMemo, useState, type ReactNode } from 'react'

import type { User } from '../types/auth'
import { AuthContext, type AuthContextValue, type AuthStatus } from './authContext'
import { loginWithPassword, logout, refreshSession, subscribeToSession } from './session'

type AuthState = { status: AuthStatus; user: User | null }

async function login(identifier: string, password: string): Promise<void> {
  // สถานะผู้ใช้อัปเดตผ่านสัญญาณจาก session.ts (ที่ฟังอยู่ใน useEffect ด้านล่าง)
  await loginWithPassword(identifier, password)
}

async function signOut(): Promise<void> {
  await logout()
}

// เก็บสถานะล็อกอินของทั้งแอป: เปิดเว็บ → กู้เซสชันจาก cookie → บอกทุกหน้าว่าใครล็อกอินอยู่
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading', user: null })

  useEffect(() => {
    let active = true

    // ฟังสัญญาณเมื่อเซสชันเปลี่ยน: login / refresh สำเร็จ = มีข้อมูลผู้ใช้ล่าสุด (รวมถึง role ที่อาจเปลี่ยน),
    // เซสชันหมด (refresh ได้ 401 หรือออกจากระบบ) = ต้องล็อกอินใหม่
    const unsubscribe = subscribeToSession((event) => {
      setState(
        event.type === 'refreshed'
          ? { status: 'authenticated', user: event.user }
          : { status: 'unauthenticated', user: null },
      )
    })

    // เปิดเว็บ: ขอ access token จาก refresh token ใน cookie (backend ตอบข้อมูลผู้ใช้กลับมาด้วย)
    // สำเร็จ/ได้ 401 → สถานะถูกตั้งโดยสัญญาณด้านบนแล้ว | เครือข่ายล่ม → ถือว่ายังไม่ล็อกอิน (cookie ยังอยู่ รีเฟรชแล้วลองใหม่ได้)
    // เรียกซ้ำใน React StrictMode ก็ปลอดภัย เพราะ refreshSession ใช้ผลของคำขอเดียวกัน
    refreshSession().catch(() => {
      if (active) setState({ status: 'unauthenticated', user: null })
    })

    return () => {
      active = false
      unsubscribe()
    }
  }, [])

  const value = useMemo<AuthContextValue>(() => ({ ...state, login, logout: signOut }), [state])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
