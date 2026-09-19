import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { deferred, errorResponse, jsonResponse, makeUser, mockFetch } from '../test/fetchMock'
import { renderApp } from '../test/renderApp'

const REFRESH = 'POST /api/auth/refresh/'
const LOGIN = 'POST /api/auth/login/'
const LOGOUT = 'POST /api/auth/logout/'

// ยังไม่มีเซสชัน: เปิดเว็บแล้ว refresh ได้ 401 จึงแสดงหน้า login
const noSession = () => errorResponse(401, 'invalid_refresh_token')

async function fillAndSubmit(identifier: string, password: string) {
  await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })
  fireEvent.change(screen.getByLabelText('รหัสหรืออีเมล'), { target: { value: identifier } })
  fireEvent.change(screen.getByLabelText('รหัสผ่าน'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'เข้าสู่ระบบ' }))
}

describe('หน้า login (ทั้งสายกับ AuthProvider และเส้นทางจริง)', () => {
  it('แสดงหน้า login เมื่อยังไม่มีเซสชัน', async () => {
    mockFetch({ [REFRESH]: noSession })

    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('login สำเร็จ → ส่งรหัส/อีเมลกับรหัสผ่านให้ backend แล้วไปหน้าแรกของบทบาท', async () => {
    const mock = mockFetch({
      [REFRESH]: noSession,
      [LOGIN]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'teacher' }) }),
    })
    const router = renderApp('/login')

    await fillAndSubmit('T0042', 'secret')

    await waitFor(() => expect(router.state.location.pathname).toBe('/teacher'))
    expect(await screen.findByText('สวัสดี, สมชาย')).toBeInTheDocument()
    expect(mock.calls.find((c) => c.url === '/api/auth/login/')?.body).toEqual({
      identifier: 'T0042',
      password: 'secret',
    })
  })

  it('กลับไปหน้าที่ตั้งใจจะเข้าก่อนถูกส่งมา login', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [LOGIN]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }),
    })
    const router = renderApp('/student')

    await fillAndSubmit('650612001', 'secret')

    await waitFor(() => expect(router.state.location.pathname).toBe('/student'))
  })

  it('หน้าที่ตั้งใจไว้ไม่ตรงบทบาท → ลงที่หน้าแรกของบทบาทตัวเอง', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [LOGIN]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'teacher' }) }),
    })
    const router = renderApp('/admin')

    await fillAndSubmit('T0042', 'secret')

    await waitFor(() => expect(router.state.location.pathname).toBe('/teacher'))
  })

  it.each([
    ['invalid_credentials', 401, /ข้อมูลเข้าสู่ระบบไม่ถูกต้อง/],
    ['email_not_verified', 403, /ยังไม่ได้ยืนยันอีเมล/],
    ['validation_error', 400, /กรอกรหัสหรืออีเมล และรหัสผ่านให้ครบ/],
  ])('แปลข้อความ error จาก code %s เป็นภาษาไทย', async (code, status, message) => {
    mockFetch({ [REFRESH]: noSession, [LOGIN]: () => errorResponse(status, code) })
    const router = renderApp('/login')

    await fillAndSubmit('T0042', 'wrong')

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(router.state.location.pathname).toBe('/login')
  })

  it('เครือข่ายล่มตอน login → แสดงข้อความเชื่อมต่อไม่ได้', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [LOGIN]: () => {
        throw new TypeError('offline')
      },
    })
    renderApp('/login')

    await fillAndSubmit('T0042', 'secret')

    expect(await screen.findByRole('alert')).toHaveTextContent('เชื่อมต่อระบบไม่ได้')
  })

  it('code ที่ไม่รู้จักแสดงข้อความทั่วไป ไม่แสดงข้อความดิบจาก backend', async () => {
    mockFetch({ [REFRESH]: noSession, [LOGIN]: () => errorResponse(500, 'something_new') })
    renderApp('/login')

    await fillAndSubmit('T0042', 'secret')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('เกิดข้อผิดพลาดที่ไม่คาดคิด')
    expect(alert).not.toHaveTextContent('something_new')
  })

  it('ระหว่างรอ backend ปุ่มถูกปิดเพื่อกันกดซ้ำ', async () => {
    const gate = deferred<Response>()
    mockFetch({ [REFRESH]: noSession, [LOGIN]: () => gate.promise })
    renderApp('/login')

    await fillAndSubmit('T0042', 'secret')

    const button = await screen.findByRole('button', { name: 'กำลังเข้าสู่ระบบ' })
    expect(button).toBeDisabled()
    gate.resolve(jsonResponse({ access: 'a', user: makeUser() }))
  })

  it('มีเซสชันอยู่แล้ว (cookie) เปิดหน้า login → ข้ามไปหน้าแรกของบทบาทเลย', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }),
    })
    const router = renderApp('/login')

    await waitFor(() => expect(router.state.location.pathname).toBe('/student'))
  })

  it('ออกจากระบบ → กลับหน้า login', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'teacher' }) }),
      [LOGOUT]: () => new Response(null, { status: 204 }),
    })
    const router = renderApp('/teacher')

    fireEvent.click(await screen.findByRole('button', { name: 'ออกจากระบบ' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('สลับเป็นภาษาอังกฤษได้ และข้อความ error เปลี่ยนตามภาษา', async () => {
    mockFetch({ [REFRESH]: noSession, [LOGIN]: () => errorResponse(401, 'invalid_credentials') })
    renderApp('/login')
    await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('ID or email'), { target: { value: 'T0042' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('sign-in details are incorrect')
  })
})
