import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // พอร์ตประจำของโปรเจกต์นี้ (ไม่ใช้ 5173 มาตรฐาน เพราะมักชนกับโปรเจกต์อื่นบนเครื่อง)
    // strictPort: ถ้าพอร์ตนี้ถูกใช้อยู่ให้หยุดพร้อมแจ้ง แทนที่จะเลื่อนไปพอร์ตอื่นเงียบ ๆ
    port: 5180,
    strictPort: true,
    // ส่งทุก request ที่ขึ้นต้นด้วย /api ไปหา Django (dev) เพื่อให้เป็น origin เดียวกัน
    // จึงไม่ต้องตั้ง CORS และ cookie ของ refresh token ใช้งานได้ตรง ๆ
    // Django ของโปรเจกต์นี้รันที่พอร์ต 8010 (เปลี่ยนได้ด้วย API_PROXY_TARGET)
    proxy: {
      '/api': process.env.API_PROXY_TARGET ?? 'http://localhost:8010',
    },
  },
  test: {
    // จำลอง DOM ของเบราว์เซอร์ให้ test component ได้
    environment: 'jsdom',
    // ไฟล์ที่รันก่อนทุก test (เพิ่มตัวช่วยตรวจ DOM เช่น toBeInTheDocument)
    setupFiles: ['./src/test/setup.ts'],
  },
})
