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

  it('ปุ่มแสดง/ซ่อนรหัสผ่านสลับชนิดช่องกรอกและบอกสถานะให้โปรแกรมอ่านหน้าจอ', async () => {
    mockFetch({ [REFRESH]: noSession })
    renderApp('/login')
    await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })
    const field = screen.getByLabelText('รหัสผ่าน')
    expect(field).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByRole('button', { name: 'แสดงรหัสผ่าน' }))

    expect(field).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'ซ่อนรหัสผ่าน' })).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: 'ซ่อนรหัสผ่าน' }))
    expect(field).toHaveAttribute('type', 'password')
  })

  it('ลิงก์ลืมรหัสผ่านอยู่ใต้ช่องรหัสผ่าน (ยังปิดไว้จนกว่าจะมีหน้าปลายทาง)', async () => {
    mockFetch({ [REFRESH]: noSession })
    renderApp('/login')
    const passwordField = await screen.findByLabelText('รหัสผ่าน')

    const forgot = screen.getByRole('button', { name: 'ลืมรหัสผ่าน' })

    expect(forgot).toBeDisabled()
    // ลืมรหัสผ่านต้องตามหลังช่องรหัสผ่านใน DOM (อยู่ใต้ช่อง ตามที่ผู้ใช้กำหนด)
    expect(passwordField.compareDocumentPosition(forgot) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('ลิงก์สมัครสมาชิกพาไปหน้าสมัคร', async () => {
    mockFetch({ [REFRESH]: noSession })
    const router = renderApp('/login')

    fireEvent.click(await screen.findByRole('link', { name: 'สมัครสมาชิกด้วยอีเมล' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/register'))
    expect(await screen.findByRole('heading', { name: 'สมัครสมาชิก' })).toBeInTheDocument()
  })

  describe('ยังไม่ยืนยันอีเมล: ปุ่มส่งลิงก์ยืนยันอีกครั้ง', () => {
    const RESEND = 'POST /api/auth/resend-verification/'

    async function loginUnverified(identifier: string) {
      await fillAndSubmit(identifier, 'secret')
      await screen.findByRole('alert')
    }

    it('กรอกเป็นอีเมล → มีปุ่ม กดแล้วส่งอีเมลนั้นไปขอลิงก์ใหม่ และแสดงผลกับตัวนับถอยหลัง', async () => {
      const mock = mockFetch({
        [REFRESH]: noSession,
        [LOGIN]: () => errorResponse(403, 'email_not_verified'),
        [RESEND]: () => jsonResponse({}, 202),
      })
      renderApp('/login')
      await loginUnverified('manee@example.com')

      fireEvent.click(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันอีกครั้ง' }))

      expect(await screen.findByText('ถ้าอีเมลนี้ยังไม่ได้ยืนยัน เราส่งลิงก์ให้แล้ว')).toBeInTheDocument()
      expect(mock.calls.find((c) => c.url === '/api/auth/resend-verification/')?.body).toEqual({
        email: 'manee@example.com',
      })
      // ห้ามกดซ้ำระหว่างรอ 60 วินาที (backend บังคับอยู่แล้ว หน้าเว็บช่วยไม่ให้กดแล้วเงียบ)
      const waiting = screen.getByRole('button', { name: /ส่งลิงก์ยืนยันอีกครั้งได้ใน 60 วินาที/ })
      expect(waiting).toBeDisabled()
      fireEvent.click(waiting)
      expect(mock.countOf(RESEND)).toBe(1)
    })

    it('กรอกเป็นรหัสนักศึกษา/พนักงาน → ไม่มีปุ่ม (ระบบไม่รู้อีเมลจึงส่งไม่ได้)', async () => {
      mockFetch({
        [REFRESH]: noSession,
        [LOGIN]: () => errorResponse(403, 'email_not_verified'),
      })
      renderApp('/login')

      await loginUnverified('6501001')

      expect(screen.queryByRole('button', { name: 'ส่งลิงก์ยืนยันอีกครั้ง' })).not.toBeInTheDocument()
    })

    it('error อื่นที่ไม่ใช่ยังไม่ยืนยันอีเมล ไม่มีปุ่มนี้', async () => {
      mockFetch({ [REFRESH]: noSession, [LOGIN]: () => errorResponse(401, 'invalid_credentials') })
      renderApp('/login')

      await loginUnverified('manee@example.com')

      expect(screen.queryByRole('button', { name: 'ส่งลิงก์ยืนยันอีกครั้ง' })).not.toBeInTheDocument()
    })

    it('ส่งไม่สำเร็จ (เครือข่ายล่ม) → บอกผู้ใช้ และกดลองใหม่ได้ทันที', async () => {
      mockFetch({
        [REFRESH]: noSession,
        [LOGIN]: () => errorResponse(403, 'email_not_verified'),
        [RESEND]: () => {
          throw new TypeError('offline')
        },
      })
      renderApp('/login')
      await loginUnverified('manee@example.com')

      fireEvent.click(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันอีกครั้ง' }))

      expect(await screen.findByText('เชื่อมต่อระบบไม่ได้')).toBeInTheDocument()
      // ไม่นับถอยหลังเมื่อส่งไม่สำเร็จ
      expect(screen.getByRole('button', { name: 'ส่งลิงก์ยืนยันอีกครั้ง' })).toBeEnabled()
    })
  })

  it('ยังไม่ยืนยันอีเมลใช้กล่องเตือนสีเหลือง ส่วน error อื่นใช้กล่องสีแดง', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [LOGIN]: () => errorResponse(403, 'email_not_verified'),
    })
    renderApp('/login')
    await fillAndSubmit('a@example.com', 'secret')
    expect(await screen.findByRole('alert')).toHaveClass('bg-warn-50')

    mockFetch({ [REFRESH]: noSession, [LOGIN]: () => errorResponse(401, 'invalid_credentials') })
    fireEvent.click(screen.getByRole('button', { name: 'เข้าสู่ระบบ' }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveClass('bg-error-50'))
  })

  it('จำภาษาที่เลือกไว้ในเบราว์เซอร์สำหรับครั้งหน้า', async () => {
    mockFetch({ [REFRESH]: noSession })
    renderApp('/login')
    await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))

    await screen.findByRole('heading', { name: 'Sign in' })
    expect(localStorage.getItem('mangosteen.language')).toBe('en')
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
