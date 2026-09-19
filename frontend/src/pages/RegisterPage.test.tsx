import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { deferred, errorResponse, jsonResponse, makeUser, mockFetch } from '../test/fetchMock'
import { renderApp } from '../test/renderApp'

const REFRESH = 'POST /api/auth/refresh/'
const REGISTER = 'POST /api/auth/register/'
const RESEND = 'POST /api/auth/resend-verification/'

// ยังไม่มีเซสชัน: เปิดเว็บแล้ว refresh ได้ 401 จึงเห็นหน้าสำหรับคนที่ยังไม่ล็อกอิน
const noSession = () => errorResponse(401, 'invalid_refresh_token')

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

// กรอกฟอร์มสมัครให้ครบ (ระบุเฉพาะช่องที่ต่างจากค่าปกติ) แล้วกดสมัคร
async function fillAndSubmit(overrides: Partial<Record<string, string>> = {}) {
  await screen.findByRole('heading', { name: 'สมัครสมาชิก' })
  const values = {
    ชื่อ: 'มานี',
    นามสกุล: 'ใจดี',
    อีเมล: 'manee@example.com',
    รหัสผ่าน: 'Str0ng-pass-123',
    ยืนยันรหัสผ่าน: 'Str0ng-pass-123',
    ...overrides,
  }
  for (const [label, value] of Object.entries(values)) fill(label, value as string)
  fireEvent.click(screen.getByRole('button', { name: 'สมัครสมาชิก' }))
}

describe('หน้าสมัครสมาชิก', () => {
  it('แสดงฟอร์มครบทุกช่องตาม wireframe พร้อมคำแนะนำรหัสผ่าน และชนิดช่องที่ถูกต้อง', async () => {
    mockFetch({ [REFRESH]: noSession })
    renderApp('/register')

    expect(await screen.findByRole('heading', { name: 'สมัครสมาชิก' })).toBeInTheDocument()
    expect(screen.getByText('บัญชีที่สมัครเองจะเป็นผู้เรียน')).toBeInTheDocument()
    expect(screen.getByLabelText('ชื่อ')).toHaveAttribute('autocomplete', 'given-name')
    expect(screen.getByLabelText('นามสกุล')).toHaveAttribute('autocomplete', 'family-name')
    expect(screen.getByLabelText('อีเมล')).toHaveAttribute('type', 'email')
    const password = screen.getByLabelText('รหัสผ่าน')
    expect(password).toHaveAttribute('type', 'password')
    expect(password).toHaveAttribute('autocomplete', 'new-password')
    // คำแนะนำผูกกับช่องด้วย aria-describedby (โปรแกรมอ่านหน้าจออ่านให้เมื่อโฟกัสช่อง)
    const hint = screen.getByText('อย่างน้อย 8 ตัวอักษร และไม่ใช่รหัสที่คาดเดาง่าย')
    expect(password.getAttribute('aria-describedby')).toContain(hint.id)
    expect(screen.getByLabelText('ยืนยันรหัสผ่าน')).toHaveAttribute('type', 'password')
  })

  it('สมัครสำเร็จ → ส่งเฉพาะข้อมูลที่ backend ต้องการ (ตัดช่องว่าง ไม่ส่งช่องยืนยันรหัส) แล้วแสดงหน้าตรวจสอบอีเมล', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [REGISTER]: () => jsonResponse({}, 202) })
    renderApp('/register')

    await fillAndSubmit({ ชื่อ: '  มานี ', อีเมล: ' manee@example.com ' })

    expect(await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })).toBeInTheDocument()
    expect(mock.calls.find((c) => c.url === '/api/auth/register/')?.body).toEqual({
      email: 'manee@example.com',
      password: 'Str0ng-pass-123',
      first_name: 'มานี',
      last_name: 'ใจดี',
    })
    // บอกว่าส่งไปที่อีเมลไหน + อายุลิงก์ 24 ชั่วโมง
    expect(screen.getByText('manee@example.com')).toBeInTheDocument()
    expect(screen.getByText(/ลิงก์ใช้ได้ 24 ชั่วโมง/)).toBeInTheDocument()
    // ฟอร์มหายไป รหัสผ่านไม่ค้างอยู่ในหน้า
    expect(screen.queryByLabelText('รหัสผ่าน')).not.toBeInTheDocument()
    expect(document.body.innerHTML).not.toContain('Str0ng-pass-123')
  })

  it('ไม่ล็อกอินให้หลังสมัคร (ยังอยู่หน้าสมัคร ไม่เรียก refresh เพิ่ม/ไม่ไปหน้าแรก)', async () => {
    mockFetch({ [REFRESH]: noSession, [REGISTER]: () => jsonResponse({}, 202) })
    const router = renderApp('/register')

    await fillAndSubmit()

    await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })
    expect(router.state.location.pathname).toBe('/register')
  })

  it('ยืนยันรหัสผ่านไม่ตรง → บอกใต้ช่อง และไม่ส่งอะไรไป backend', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [REGISTER]: () => jsonResponse({}, 202) })
    renderApp('/register')

    await fillAndSubmit({ ยืนยันรหัสผ่าน: 'Different-pass-456' })

    expect(await screen.findByText('รหัสผ่านสองช่องไม่ตรงกัน')).toBeInTheDocument()
    expect(screen.getByLabelText('ยืนยันรหัสผ่าน')).toHaveAttribute('aria-invalid', 'true')
    expect(mock.countOf(REGISTER)).toBe(0)
  })

  it('อีเมลนี้มีบัญชีแล้ว (409 email_taken) → บอกใต้ช่องอีเมลพร้อมลิงก์ไปเข้าสู่ระบบ', async () => {
    mockFetch({ [REFRESH]: noSession, [REGISTER]: () => errorResponse(409, 'email_taken') })
    const router = renderApp('/register')

    await fillAndSubmit()

    const email = await screen.findByLabelText('อีเมล')
    await waitFor(() => expect(email).toHaveAttribute('aria-invalid', 'true'))
    expect(screen.getByText(/อีเมลนี้มีบัญชีอยู่แล้ว/)).toBeInTheDocument()
    // ลิงก์ในข้อความผิดพลาด (ตัวแรก) พาไปหน้า login
    const error = document.getElementById(email.getAttribute('aria-describedby') ?? '')
    const loginLink = error?.querySelector('a') as HTMLAnchorElement
    fireEvent.click(loginLink)
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('รหัสผ่านไม่ผ่านกฎ → แสดงข้อความไทยทีละกฎจาก error_codes และไม่แสดงข้อความดิบภาษาอังกฤษของ backend', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { password: ['This password is too short.', 'This password is too common.'] },
            error_codes: { password: ['password_too_short', 'password_too_common'] },
          },
          400,
        ),
    })
    renderApp('/register')

    await fillAndSubmit({ รหัสผ่าน: '12345', ยืนยันรหัสผ่าน: '12345' })

    expect(await screen.findByText('รหัสผ่านสั้นเกินไป ต้องมีอย่างน้อย 8 ตัวอักษร')).toBeInTheDocument()
    expect(screen.getByText('รหัสผ่านนี้คาดเดาง่ายเกินไป')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('This password')
    expect(screen.getByLabelText('รหัสผ่าน')).toHaveAttribute('aria-invalid', 'true')
  })

  it('ข้อผิดพลาดหลายช่องพร้อมกัน (ชื่อ + รหัสผ่าน) แสดงครบในรอบเดียว', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { first_name: ['x'], password: ['y'] },
            error_codes: { first_name: ['blank'], password: ['password_entirely_numeric'] },
          },
          400,
        ),
    })
    renderApp('/register')

    await fillAndSubmit()

    expect(await screen.findAllByText('กรุณากรอกช่องนี้')).toHaveLength(1)
    expect(screen.getByText('รหัสผ่านต้องไม่เป็นตัวเลขล้วน')).toBeInTheDocument()
  })

  it('รหัสกฎที่ไม่รู้จักแสดงข้อความทั่วไป ไม่แสดงรหัสดิบ', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { email: ['x'] },
            error_codes: { email: ['some_new_rule'] },
          },
          400,
        ),
    })
    renderApp('/register')

    await fillAndSubmit()

    expect(await screen.findByText('ข้อมูลไม่ถูกต้อง')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('some_new_rule')
  })

  it('เครือข่ายล่ม → กล่องแจ้งเตือนสีแดง และกรอกข้อมูลเดิมไว้ให้ลองใหม่ได้', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () => {
        throw new TypeError('offline')
      },
    })
    renderApp('/register')

    await fillAndSubmit()

    expect(await screen.findByRole('alert')).toHaveTextContent('เชื่อมต่อระบบไม่ได้')
    expect(screen.getByLabelText('อีเมล')).toHaveValue('manee@example.com')
    expect(screen.getByRole('button', { name: 'สมัครสมาชิก' })).toBeEnabled()
  })

  it('code ที่ไม่รู้จัก (500) แสดงข้อความทั่วไป ไม่แสดงข้อความดิบจาก backend', async () => {
    mockFetch({ [REFRESH]: noSession, [REGISTER]: () => errorResponse(500, 'something_new') })
    renderApp('/register')

    await fillAndSubmit()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('เกิดข้อผิดพลาดที่ไม่คาดคิด')
    expect(alert).not.toHaveTextContent('something_new')
  })

  it('ระหว่างรอ backend ปุ่มถูกปิดเพื่อกันกดซ้ำ', async () => {
    const gate = deferred<Response>()
    const mock = mockFetch({ [REFRESH]: noSession, [REGISTER]: () => gate.promise })
    renderApp('/register')

    await fillAndSubmit()

    const button = await screen.findByRole('button', { name: 'กำลังสมัคร' })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(mock.countOf(REGISTER)).toBe(1)
    gate.resolve(jsonResponse({}, 202))
  })

  it('ข้อความเปลี่ยนตามภาษา (อังกฤษ) รวมข้อความผิดพลาดของช่อง', async () => {
    mockFetch({ [REFRESH]: noSession, [REGISTER]: () => errorResponse(409, 'email_taken') })
    renderApp('/register')
    await screen.findByRole('heading', { name: 'สมัครสมาชิก' })

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))
    expect(await screen.findByRole('heading', { name: 'Sign up' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'Manee' } })
    fireEvent.change(screen.getByLabelText('Last name'), { target: { value: 'Jaidee' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'manee@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Str0ng-pass-123' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'Str0ng-pass-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign up' }))

    expect(await screen.findByText(/An account with this email already exists/)).toBeInTheDocument()
  })

  it('ลิงก์ "เข้าสู่ระบบ" ท้ายฟอร์มพากลับหน้า login', async () => {
    mockFetch({ [REFRESH]: noSession })
    const router = renderApp('/register')
    await screen.findByRole('heading', { name: 'สมัครสมาชิก' })

    fireEvent.click(screen.getByRole('link', { name: 'เข้าสู่ระบบ' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('ล็อกอินอยู่แล้วเปิดหน้าสมัคร → ไปหน้าแรกของบทบาทเลย', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }),
    })
    const router = renderApp('/register')

    await waitFor(() => expect(router.state.location.pathname).toBe('/student'))
  })
})

describe('หน้า "ตรวจสอบอีเมลของคุณ" หลังสมัคร: ปุ่มส่งอีกครั้ง', () => {
  async function registerFirst() {
    await fillAndSubmit()
    await screen.findByRole('heading', { name: 'ตรวจสอบอีเมลของคุณ' })
  }

  it('กดส่งอีกครั้ง → ขอลิงก์ใหม่ให้อีเมลที่สมัคร แล้วนับถอยหลัง 60 วินาที ห้ามกดซ้ำ', async () => {
    const mock = mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () => jsonResponse({}, 202),
      [RESEND]: () => jsonResponse({}, 202),
    })
    renderApp('/register')
    await registerFirst()

    fireEvent.click(screen.getByRole('button', { name: 'ส่งอีกครั้ง' }))

    expect(await screen.findByText(/เราส่งลิงก์ใหม่ให้แล้ว/)).toBeInTheDocument()
    expect(mock.calls.find((c) => c.url === '/api/auth/resend-verification/')?.body).toEqual({
      email: 'manee@example.com',
    })
    const waiting = screen.getByRole('button', { name: /ส่งอีกครั้งได้ใน 60 วินาที/ })
    expect(waiting).toBeDisabled()
    fireEvent.click(waiting)
    expect(mock.countOf(RESEND)).toBe(1)
  })

  it('ส่งไม่สำเร็จ → บอกผู้ใช้ และไม่นับถอยหลัง (กดลองใหม่ได้)', async () => {
    mockFetch({
      [REFRESH]: noSession,
      [REGISTER]: () => jsonResponse({}, 202),
      [RESEND]: () => errorResponse(500, 'something_new'),
    })
    renderApp('/register')
    await registerFirst()

    fireEvent.click(screen.getByRole('button', { name: 'ส่งอีกครั้ง' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('เกิดข้อผิดพลาดที่ไม่คาดคิด')
    expect(screen.getByRole('button', { name: 'ส่งอีกครั้ง' })).toBeEnabled()
  })
})
