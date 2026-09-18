import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // ส่งทุก request ที่ขึ้นต้นด้วย /api ไปหา Django (dev) เพื่อให้เป็น origin เดียวกัน
    // จึงไม่ต้องตั้ง CORS และ cookie ของ refresh token ใช้งานได้ตรง ๆ
    // ที่อยู่ของ Django เปลี่ยนได้ด้วย API_PROXY_TARGET (เช่นเมื่อพอร์ต 8000 ถูกโปรเจกต์อื่นใช้อยู่)
    proxy: {
      '/api': process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
  test: {
    // จำลอง DOM ของเบราว์เซอร์ให้ test component ได้
    environment: 'jsdom',
    // ไฟล์ที่รันก่อนทุก test (เพิ่มตัวช่วยตรวจ DOM เช่น toBeInTheDocument)
    setupFiles: ['./src/test/setup.ts'],
  },
})
