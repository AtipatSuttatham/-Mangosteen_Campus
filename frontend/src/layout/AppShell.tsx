import { Outlet } from 'react-router'

import { useAuth } from '../auth/useAuth'
import { CalyxOutline } from '../components/LogoMark'
import { BottomNav, MobileTopBar } from './MobileChrome'
import { Sidebar } from './Sidebar'

// โครงหน้าของทุกหน้าหลังล็อกอิน
// - จอกว้าง (>= 1024px): แถบเมนูซ้าย + เนื้อหา
// - มือถือ: แถบบน + เนื้อหา + แถบเมนูล่าง (ผู้ดูแลระบบใช้ลิ้นชักแทนแถบล่าง)
export function AppShell() {
  const { user } = useAuth()
  // อยู่ใต้ RequireAuth เสมอจึงมีผู้ใช้ — เช็กไว้เพื่อให้ชนิดข้อมูลถูกต้อง
  if (!user) return null

  return (
    <div className="flex min-h-screen">
      <Sidebar user={user} />

      <div className="flex min-w-0 flex-1 flex-col">
        <MobileTopBar user={user} />

        <main className="relative flex-1 overflow-hidden px-5 pt-6 pb-24 lg:px-14 lg:pt-10 lg:pb-10">
          {/* ลายตราดอกจางมุมขวาบน (ตกแต่ง ตาม wireframe) */}
          <CalyxOutline
            strokeWidth={0.9}
            className="pointer-events-none absolute -top-[70px] -right-[50px] size-[360px] text-plum-800 opacity-[0.06]"
          />
          <div className="relative">
            <Outlet />
          </div>
        </main>

        <BottomNav user={user} />
      </div>
    </div>
  )
}
