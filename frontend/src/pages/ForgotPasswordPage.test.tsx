import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { deferred, errorResponse, jsonResponse, makeUser, mockFetch } from '../test/fetchMock'
import { renderApp } from '../test/renderApp'

const REFRESH = 'POST /api/auth/refresh/'
const FORGOT = 'POST /api/auth/forgot-password/'

const noSession = () => errorResponse(401, 'invalid_refresh_token')

async function fillAndSubmit(email = 'manee@example.com') {
  await screen.findByRole('heading', { name: 'ลืมรหัสผ่าน' })
  fireEvent.change(screen.getByLabelText('อีเมล'), { target: { value: email } })
  fireEvent.click(screen.getByRole('button', { name: 'ส่งลิงก์ตั้งรหัสผ่าน' }))
}

describe('หน้าลืมรหัสผ่าน', () => {
  it('แสดงฟอร์มกรอกอีเมลตาม wireframe พร้อมลิงก์กลับไปเข้าสู่ระบบ', async () => {
    mockFetch({ [REFRESH]: noSession })
    renderApp('/forgot-password')

    expect(await screen.findByRole('heading', { name: 'ลืมรหัสผ่าน' })).toBeInTheDocument()
    expect(screen.getByLabelText('อีเมล')).toHaveAttribute('type', 'email')
    expect(screen.getByRole('link', { name: 'กลับไปเข้าสู่ระบบ' })).toHaveAttribute('href', '/login')
  })

  it('ส่งสำเร็จ → ส่งอีเมล (ตัดช่องว่าง) ไป backend แล้วแสดงข้อความที่ไม่ยืนยันว่ามีบัญชี', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [FORGOT]: () => jsonResponse({}, 202) })
    renderApp('/forgot-password')

    await fillAndSubmit('  manee@example.com ')

    expect(await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })).toBeInTheDocument()
    expect(mock.calls.find((c) => c.url === '/api/auth/forgot-password/')?.body).toEqual({
      email: 'manee@example.com',
    })
    // "ถ้ามีบัญชี…" ไม่บอกว่ามีหรือไม่ + อายุลิงก์ 1 ชั่วโมง + แนะนำเรื่องยังไม่ยืนยันอีเมล
    expect(screen.getByText(/ถ้ามีบัญชีที่ใช้อีเมล/)).toBeInTheDocument()
    expect(screen.getByText('manee@example.com')).toBeInTheDocument()
    expect(screen.getByText(/ลิงก์ใช้ได้ 1 ชั่วโมง/)).toBeInTheDocument()
    expect(screen.getByText(/ยังไม่ได้ยืนยันอีเมล ให้ยืนยันอีเมลก่อน/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'กลับไปเข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('ตอบข้อความเดิมไม่ว่า backend จะส่งอีเมลจริงหรือไม่ (ไม่มีอะไรต่างให้เห็น)', async () => {
    mockFetch({ [REFRESH]: noSession, [FORGOT]: () => jsonResponse({}, 202) })
    renderApp('/forgot-password')

    await fillAndSubmit('nobody@example.com')

    expect(await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/ไม่พบ|ไม่มีบัญชี|ไม่มีอีเมล/)
  })

  it('กดส่งอีกครั้ง → ขอลิงก์ใหม่ให้อีเมลเดิม แล้วนับถอยหลัง 60 วินาที ห้ามกดซ้ำ', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [FORGOT]: () => jsonResponse({}, 202) })
    renderApp('/forgot-password')
    await fillAndSubmit()
    await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })

    fireEvent.click(screen.getByRole('button', { name: 'ส่งอีกครั้ง' }))

    expect(await screen.findByText(/ลิงก์ฉบับก่อนหน้าใช้ไม่ได้/)).toBeInTheDocument()
    const waiting = screen.getByRole('button', { name: /ส่งอีกครั้งได้ใน 60 วินาที/ })
    expect(waiting).toBeDisabled()
    fireEvent.click(waiting)
    expect(mock.countOf(FORGOT)).toBe(2)
  })

  it('อีเมลผิดรูปแบบที่ backend ปฏิเสธ (400) → แสดงกล่องแจ้งเตือน ไม่แสดงข้อความดิบ', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [FORGOT]: () =>
        jsonResponse({ code: 'validation_error', errors: { email: ['Enter a valid email address.'] } }, 400),
    })
    renderApp('/forgot-password')

    await fillAndSubmit('a@b.c')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('กรอกข้อมูลไม่ครบ')
    expect(document.body.textContent).not.toContain('Enter a valid email')
    expect(screen.getByRole('button', { name: 'ส่งลิงก์ตั้งรหัสผ่าน' })).toBeEnabled()
  })

  it('เครือข่ายล่ม → แจ้งผู้ใช้ และยังกรอกอีเมลเดิมไว้ให้ลองใหม่', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [FORGOT]: () => {
        throw new TypeError('offline')
      },
    })
    renderApp('/forgot-password')

    await fillAndSubmit()

    expect(await screen.findByRole('alert')).toHaveTextContent('เชื่อมต่อระบบไม่ได้')
    expect(screen.getByLabelText('อีเมล')).toHaveValue('manee@example.com')
  })

  it('ระหว่างรอ backend ปุ่มถูกปิดเพื่อกันกดซ้ำ', async () => {
    const gate = deferred<Response>()
    const mock = mockFetch({ [REFRESH]: noSession, [FORGOT]: () => gate.promise })
    renderApp('/forgot-password')

    await fillAndSubmit()

    const button = await screen.findByRole('button', { name: 'กำลังส่ง' })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(mock.countOf(FORGOT)).toBe(1)
    gate.resolve(jsonResponse({}, 202))
  })

  it('ล็อกอินอยู่แล้วเปิดหน้านี้ → ไปหน้าแรกของบทบาทเลย', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'teacher' }) }),
    })
    const router = renderApp('/forgot-password')

    await waitFor(() => expect(router.state.location.pathname).toBe('/teacher'))
  })

  it('ข้อความเปลี่ยนตามภาษา (อังกฤษ)', async () => {
    mockFetch({ [REFRESH]: noSession, [FORGOT]: () => jsonResponse({}, 202) })
    renderApp('/forgot-password')
    await screen.findByRole('heading', { name: 'ลืมรหัสผ่าน' })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(await screen.findByRole('heading', { name: 'Forgot password' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'manee@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send the reset link' }))

    expect(await screen.findByRole('heading', { name: 'Check your email' })).toBeInTheDocument()
    expect(screen.getByText(/The link works for 1 hour/)).toBeInTheDocument()
  })
})
