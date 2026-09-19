import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { describe, expect, it } from 'vitest'

import { AuthProvider } from '../auth/AuthProvider'
import { appRoutes } from '../router'
import { deferred, errorResponse, jsonResponse, makeUser, mockFetch } from '../test/fetchMock'
import { renderApp } from '../test/renderApp'

const REFRESH = 'POST /api/auth/refresh/'
const VERIFY = 'POST /api/auth/verify-email/'
const RESEND = 'POST /api/auth/resend-verification/'

const noSession = () => errorResponse(401, 'invalid_refresh_token')

describe('หน้ายืนยันอีเมล (เปิดจากลิงก์ในอีเมล)', () => {
  it('ยืนยันสำเร็จ → ส่งโทเคนใน body (ไม่ใช่ URL) แล้วแสดง "ยืนยันอีเมลแล้ว" พร้อมปุ่มเข้าสู่ระบบ', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [VERIFY]: () => jsonResponse({ email_verified: true }) })
    const router = renderApp('/verify-email?token=abc-DEF_123')

    expect(await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })).toBeInTheDocument()
    const call = mock.calls.find((c) => c.url === '/api/auth/verify-email/')
    expect(call?.method).toBe('POST')
    expect(call?.body).toEqual({ token: 'abc-DEF_123' })
    // ไม่ล็อกอินให้ — ปุ่มพาไปหน้า login
    fireEvent.click(screen.getByRole('link', { name: 'เข้าสู่ระบบ' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('ระหว่างรอผลแสดงข้อความกำลังยืนยัน', async () => {
    const gate = deferred<Response>()
    mockFetch({ [REFRESH]: noSession, [VERIFY]: () => gate.promise })
    renderApp('/verify-email?token=abc')

    expect(await screen.findByRole('status')).toHaveTextContent('กำลังยืนยันอีเมล')
    gate.resolve(jsonResponse({ email_verified: true }))
    expect(await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })).toBeInTheDocument()
  })

  it('เรียกยืนยันครั้งเดียวแม้ React รัน effect ซ้ำ (StrictMode) — ไม่งั้นโทเคนถูกใช้ไปแล้วคำขอที่สองจะได้ "ใช้ไม่ได้"', async () => {
    // โทเคนใช้ได้ครั้งเดียว: คำขอแรกสำเร็จ คำขอที่สองต้องไม่เกิดขึ้น
    let calls = 0
    const mock = mockFetch({
      [REFRESH]: noSession,
      [VERIFY]: () => {
        calls += 1
        return calls === 1 ? jsonResponse({ email_verified: true }) : errorResponse(400, 'token_invalid')
      },
    })
    const router = createMemoryRouter(appRoutes, { initialEntries: ['/verify-email?token=abc'] })
    render(
      <StrictMode>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </StrictMode>,
    )

    expect(await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })).toBeInTheDocument()
    expect(mock.countOf(VERIFY)).toBe(1)
  })

  it.each(['token_invalid', 'token_expired'])(
    'ลิงก์ใช้ไม่ได้ (%s) → แสดง "ลิงก์นี้ใช้ไม่ได้แล้ว" พร้อมช่องกรอกอีเมลขอลิงก์ใหม่',
    async (code) => {
      mockFetch({ [REFRESH]: noSession, [VERIFY]: () => errorResponse(400, code) })
      renderApp('/verify-email?token=abc')

      expect(await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })).toBeInTheDocument()
      expect(screen.getByLabelText('อีเมล')).toHaveAttribute('type', 'email')
      expect(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันใหม่' })).toBeEnabled()
      // คนที่ยืนยันไปแล้วมีทางไปเข้าสู่ระบบ
      expect(screen.getByRole('link', { name: 'เข้าสู่ระบบ' })).toHaveAttribute('href', '/login')
    },
  )

  it('ไม่มีโทเคนใน URL → ถือว่าลิงก์ใช้ไม่ได้ โดยไม่เรียก backend', async () => {
    const mock = mockFetch({ [REFRESH]: noSession })
    renderApp('/verify-email')

    expect(await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })).toBeInTheDocument()
    expect(mock.countOf(VERIFY)).toBe(0)
  })

  it('ขอลิงก์ใหม่จากหน้าลิงก์ใช้ไม่ได้ → ส่งอีเมลที่กรอก แล้วแสดงผลแบบไม่บอกว่ามีบัญชีหรือไม่ และนับถอยหลัง', async () => {
    const mock = mockFetch({
      [REFRESH]: noSession,
      [VERIFY]: () => errorResponse(400, 'token_expired'),
      [RESEND]: () => jsonResponse({}, 202),
    })
    renderApp('/verify-email?token=abc')
    await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })

    fireEvent.change(screen.getByLabelText('อีเมล'), { target: { value: ' manee@example.com ' } })
    fireEvent.click(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันใหม่' }))

    expect(
      await screen.findByText('ถ้าอีเมลนี้สมัครไว้และยังไม่ได้ยืนยัน เราส่งลิงก์ใหม่ให้แล้ว'),
    ).toBeInTheDocument()
    expect(mock.calls.find((c) => c.url === '/api/auth/resend-verification/')?.body).toEqual({
      email: 'manee@example.com',
    })
    expect(screen.getByRole('button', { name: /ส่งได้อีกครั้งใน 60 วินาที/ })).toBeDisabled()
  })

  it('ขอลิงก์ใหม่ไม่สำเร็จ → แจ้งผู้ใช้ และกดลองใหม่ได้', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [VERIFY]: () => errorResponse(400, 'token_invalid'),
      [RESEND]: () => errorResponse(400, 'validation_error'),
    })
    renderApp('/verify-email?token=abc')
    await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })

    fireEvent.change(screen.getByLabelText('อีเมล'), { target: { value: 'manee@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันใหม่' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('กรอกข้อมูลไม่ครบ')
    expect(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันใหม่' })).toBeEnabled()
  })

  it('เครือข่ายล่มตอนยืนยัน → บอกให้ลองอีกครั้ง (ไม่บอกว่าลิงก์เสีย) แล้วกดลองซ้ำสำเร็จ', async () => {
    let attempt = 0
    const mock = mockFetch({
      [REFRESH]: noSession,
      [VERIFY]: () => {
        attempt += 1
        if (attempt === 1) throw new TypeError('offline')
        return jsonResponse({ email_verified: true })
      },
    })
    renderApp('/verify-email?token=abc')

    expect(await screen.findByRole('heading', { name: 'เชื่อมต่อระบบไม่ได้' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'ลองอีกครั้ง' }))

    expect(await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })).toBeInTheDocument()
    expect(mock.countOf(VERIFY)).toBe(2)
  })

  it('error ที่ไม่รู้จักจาก backend (500) → ให้ลองอีกครั้ง ไม่แสดงข้อความดิบ', async () => {
    mockFetch({ [REFRESH]: noSession, [VERIFY]: () => errorResponse(500, 'something_new') })
    renderApp('/verify-email?token=abc')

    expect(await screen.findByRole('button', { name: 'ลองอีกครั้ง' })).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('something_new')
  })

  it('เปิดได้ทั้งที่ล็อกอินอยู่ (ไม่ถูกพาไปหน้าแรก)', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }),
      [VERIFY]: () => jsonResponse({ email_verified: true }),
    })
    const router = renderApp('/verify-email?token=abc')

    expect(await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/verify-email')
  })

  it('ข้อความเปลี่ยนตามภาษา (อังกฤษ)', async () => {
    mockFetch({ [REFRESH]: noSession, [VERIFY]: () => jsonResponse({ email_verified: true }) })
    renderApp('/verify-email?token=abc')
    await screen.findByRole('heading', { name: 'ยืนยันอีเมลแล้ว' })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))

    expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeInTheDocument()
  })
})
