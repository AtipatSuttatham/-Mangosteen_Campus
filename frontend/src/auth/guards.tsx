import { Navigate, Outlet, useLocation, type Location } from 'react-router'

import { PageMessage } from '../components/PageMessage'
import type { Role } from '../types/auth'
import { useAuth } from './useAuth'
import { homePathForRole } from './roles'

// หน้าที่ผู้ใช้พยายามเข้าก่อนถูกพาไปหน้า login (เก็บไว้เพื่อพากลับหลังล็อกอิน)
type LoginRedirectState = { from?: Pick<Location, 'pathname' | 'search' | 'hash'> } | null

// เส้นทางที่ต้องล็อกอินก่อน: ยังไม่ล็อกอิน → ไปหน้า login (จำหน้าที่จะเข้าไว้)
export function RequireAuth() {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <PageMessage messageKey="common.loading" />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

// เส้นทางที่จำกัดเฉพาะบางบทบาท (ใช้ใต้ RequireAuth): ผิดบทบาท → พาไปหน้าแรกของบทบาทตัวเอง
// นี่เป็นแค่การจัดหน้าให้ใช้งานง่าย สิทธิ์จริงของข้อมูล backend ตรวจจากฐานข้อมูลทุกครั้ง
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth()

  if (user && !roles.includes(user.role)) {
    return <Navigate to={homePathForRole(user.role)} replace />
  }
  return <Outlet />
}

// หน้าสำหรับคนที่ยังไม่ล็อกอิน (เช่น login): ล็อกอินแล้วพาไปหน้าที่ตั้งใจไว้ หรือหน้าแรกของบทบาท
export function PublicOnly() {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <PageMessage messageKey="common.loading" />
  if (user) {
    const from = (location.state as LoginRedirectState)?.from
    return <Navigate to={from ?? homePathForRole(user.role)} replace />
  }
  return <Outlet />
}

// เข้า "/" → พาไปหน้าแรกของบทบาท (ใช้ใต้ RequireAuth จึงมีผู้ใช้เสมอ)
export function RedirectToHome() {
  const { user } = useAuth()

  return user ? <Navigate to={homePathForRole(user.role)} replace /> : null
}
