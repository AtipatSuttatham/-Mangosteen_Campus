import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

// ฟอนต์แบบ self-host (ไม่โหลดจาก Google) — เลือกเฉพาะน้ำหนักที่ดีไซน์ใช้
import '@fontsource/ibm-plex-sans-thai/400.css'
import '@fontsource/ibm-plex-sans-thai/500.css'
import '@fontsource/ibm-plex-sans-thai/600.css'
import '@fontsource/taviraj/500.css'
import '@fontsource/taviraj/600.css'
import '@fontsource/taviraj/700.css'

import './index.css'
// เริ่มระบบหลายภาษา (ต้อง import ก่อน render)
import './i18n'
import { AuthProvider } from './auth/AuthProvider'
import { appRoutes } from './router'

// ตัวจัดการ cache และการเรียก API ของทั้งแอป
const queryClient = new QueryClient()
// ระบบเปลี่ยนหน้าแบบใช้ URL จริงของเบราว์เซอร์
const router = createBrowserRouter(appRoutes)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* สถานะล็อกอินต้องอยู่นอก router เพื่อให้ตัวกันหน้าทุกตัวอ่านได้ */}
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
