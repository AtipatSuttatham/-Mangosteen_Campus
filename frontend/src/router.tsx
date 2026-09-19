import { Navigate, type RouteObject } from 'react-router'

import { PublicOnly, RedirectToHome, RequireAuth, RequireRole } from './auth/guards'
import { AppShell } from './layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import VerifyEmailPage from './pages/VerifyEmailPage'

// เส้นทางทั้งหมดของแอป (แยกจาก main.tsx เพื่อให้ test ใช้ชุดเดียวกับของจริง)
export const appRoutes: RouteObject[] = [
  // หน้าสำหรับคนที่ยังไม่ล็อกอิน (ล็อกอินอยู่แล้วจะถูกพาไปหน้าแรกของบทบาท)
  {
    element: <PublicOnly />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },

  // หน้าที่เปิดจากลิงก์ในอีเมล: เปิดได้ทั้งตอนล็อกอินอยู่และไม่ได้ (ไม่ใส่ตัวกัน)
  { path: '/verify-email', element: <VerifyEmailPage /> },

  // หน้าที่ต้องล็อกอิน
  {
    element: <RequireAuth />,
    children: [
      { path: '/', element: <RedirectToHome /> },
      // หน้าหลังล็อกอินทั้งหมดอยู่ในโครงหน้าเดียวกัน (แถบเมนู + เนื้อหา)
      {
        element: <AppShell />,
        children: [
          // dashboard ของแต่ละบทบาท (จำกัดเฉพาะบทบาทนั้น)
          {
            element: <RequireRole roles={['admin']} />,
            children: [{ path: '/admin', element: <DashboardPage /> }],
          },
          {
            element: <RequireRole roles={['teacher']} />,
            children: [{ path: '/teacher', element: <DashboardPage /> }],
          },
          {
            element: <RequireRole roles={['student']} />,
            children: [{ path: '/student', element: <DashboardPage /> }],
          },
        ],
      },
    ],
  },

  // เส้นทางที่ไม่มีอยู่ → กลับหน้าแรก (ยังไม่ล็อกอินก็จะถูกส่งต่อไปหน้า login)
  { path: '*', element: <Navigate to="/" replace /> },
]
