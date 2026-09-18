import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import i18n from './i18n'

// render App พร้อม provider เหมือนตอนใช้งานจริง (ปิดการลองซ้ำเพื่อให้ผลออกทันที)
function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App', () => {
  beforeEach(async () => {
    // ทุก test เริ่มที่ภาษาไทยเสมอ
    await i18n.changeLanguage('th')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('แสดงข้อความภาษาไทยเป็นค่าเริ่มต้น และบอกว่าต่อ backend ได้', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }))))

    renderApp()

    expect(screen.getByText('ระบบเรียนออนไลน์สำหรับรายวิชาของคุณ')).toBeInTheDocument()
    expect(await screen.findByText('เชื่อมต่อระบบหลังบ้านได้แล้ว')).toBeInTheDocument()
  })

  it('สลับเป็นภาษาอังกฤษได้เมื่อกดปุ่ม EN', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }))))

    renderApp()
    fireEvent.click(screen.getByRole('button', { name: 'EN' }))

    expect(await screen.findByText('The online learning system for your courses')).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('แจ้งว่าเชื่อมต่อ backend ไม่ได้เมื่อ API ตอบ error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))

    renderApp()

    expect(await screen.findByText('ยังเชื่อมต่อระบบหลังบ้านไม่ได้')).toBeInTheDocument()
  })
})
