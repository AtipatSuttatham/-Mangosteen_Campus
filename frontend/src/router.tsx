import { Navigate, type RouteObject } from 'react-router'

import { PublicOnly, RedirectToHome, RequireAuth, RequireRole } from './auth/guards'
import LoginPage from './pages/LoginPage'
import RoleHomePage from './pages/RoleHomePage'

// เส้นทางทั้งหมดของแอป (แยกจาก main.tsx เพื่อให้ test ใช้ชุดเดียวกับของจริง)
export const appRoutes: RouteObject[] = [
  // หน้าสำหรับคนที่ยังไม่ล็อกอิน
  { element: <PublicOnly />, children: [{ path: '/login', element: <LoginPage /> }] },

  // หน้าที่ต้องล็อกอิน
  {
    element: <RequireAuth />,
    children: [
      { path: '/', element: <RedirectToHome /> },
      // หน้าแรกของแต่ละบทบาท (จำกัดเฉพาะบทบาทนั้น)
      {
        element: <RequireRole roles={['admin']} />,
        children: [{ path: '/admin', element: <RoleHomePage /> }],
      },
      {
        element: <RequireRole roles={['teacher']} />,
        children: [{ path: '/teacher', element: <RoleHomePage /> }],
      },
      {
        element: <RequireRole roles={['student']} />,
        children: [{ path: '/student', element: <RoleHomePage /> }],
      },
    ],
  },

  // เส้นทางที่ไม่มีอยู่ → กลับหน้าแรก (ยังไม่ล็อกอินก็จะถูกส่งต่อไปหน้า login)
  { path: '*', element: <Navigate to="/" replace /> },
]
