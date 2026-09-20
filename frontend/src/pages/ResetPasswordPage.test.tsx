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
const CHECK = 'POST /api/auth/reset-password/check/'
const RESET = 'POST /api/auth/reset-password/'

const noSession = () => errorResponse(401, 'invalid_refresh_token')
const okCheck = () => jsonResponse({ email: 'manee@example.com' })

// เปิดหน้าตั้งรหัสจากลิงก์ที่ใช้ได้ แล้วรอจนฟอร์มขึ้น
async function openForm(extra: Record<string, () => Response | Promise<Response>> = {}) {
  const mock = mockFetch({ [REFRESH]: noSession, [CHECK]: okCheck, ...extra })
  const router = renderApp('/reset-password?token=abc-DEF_123')
  await screen.findByRole('heading', { name: 'ตั้งรหัสผ่านใหม่' })
  return { mock, router }
}

function fillPasswords(password: string, confirm = password) {
  fireEvent.change(screen.getByLabelText('รหัสผ่านใหม่'), { target: { value: password } })
  fireEvent.change(screen.getByLabelText('ยืนยันรหัสผ่านใหม่'), { target: { value: confirm } })
}

const submit = () => fireEvent.click(screen.getByRole('button', { name: 'ตั้งรหัสผ่าน' }))

// รายการกฎ: อ่านสถานะที่โปรแกรมอ่านหน้าจออ่าน (ข้อความ "ผ่านแล้ว/ยังไม่ผ่าน" ในแต่ละข้อ)
function ruleState(label: string): 'ผ่านแล้ว' | 'ยังไม่ผ่าน' {
  const item = screen.getByText(label).closest('li') as HTMLElement
  return item.textContent?.includes('ผ่านแล้ว') ? 'ผ่านแล้ว' : 'ยังไม่ผ่าน'
}

describe('หน้าตั้งรหัสผ่านใหม่ (เปิดจากลิงก์ในอีเมล)', () => {
  it('ตรวจลิงก์ตอนเปิดหน้า (โทเคนใน body) แล้วบอกว่าตั้งรหัสให้บัญชีไหน', async () => {
    const { mock } = await openForm()

    expect(screen.getByText('สำหรับบัญชี manee@example.com')).toBeInTheDocument()
    const call = mock.calls.find((c) => c.url === '/api/auth/reset-password/check/')
    expect(call?.method).toBe('POST')
    expect(call?.body).toEqual({ token: 'abc-DEF_123' })
    expect(screen.getByLabelText('รหัสผ่านใหม่')).toHaveAttribute('autocomplete', 'new-password')
    expect(screen.getByLabelText('ยืนยันรหัสผ่านใหม่')).toHaveAttribute('type', 'password')
  })

  it('ระหว่างตรวจลิงก์แสดงข้อความกำลังตรวจสอบ', async () => {
    const gate = deferred<Response>()
    mockFetch({ [REFRESH]: noSession, [CHECK]: () => gate.promise })
    renderApp('/reset-password?token=abc')

    expect(await screen.findByRole('status')).toHaveTextContent('กำลังตรวจสอบลิงก์')
    gate.resolve(okCheck())
    expect(await screen.findByRole('heading', { name: 'ตั้งรหัสผ่านใหม่' })).toBeInTheDocument()
  })

  it('ตรวจลิงก์ครั้งเดียวแม้ React รัน effect ซ้ำ (StrictMode)', async () => {
    const mock = mockFetch({ [REFRESH]: noSession, [CHECK]: okCheck })
    const router = createMemoryRouter(appRoutes, { initialEntries: ['/reset-password?token=abc'] })
    render(
      <StrictMode>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </StrictMode>,
    )

    await screen.findByRole('heading', { name: 'ตั้งรหัสผ่านใหม่' })
    expect(mock.countOf(CHECK)).toBe(1)
  })

  describe('รายการกฎของรหัสผ่าน (ติ๊กสดตอนพิมพ์)', () => {
    it('เริ่มต้นทุกข้อเป็นสีเทา (ยังไม่ผ่าน) ไม่แดงตั้งแต่ยังไม่พิมพ์', async () => {
      await openForm()

      expect(ruleState('อย่างน้อย 8 ตัวอักษร')).toBe('ยังไม่ผ่าน')
      expect(ruleState('ไม่เป็นตัวเลขล้วน')).toBe('ยังไม่ผ่าน')
      const item = screen.getByText('อย่างน้อย 8 ตัวอักษร').closest('li')
      expect(item).not.toHaveClass('text-error-800')
    })

    it('พิมพ์แล้วข้อที่ผ่านติ๊กทันที (ยาวพอ + ไม่ใช่เลขล้วน)', async () => {
      await openForm()

      fillPasswords('abcdefgh')

      expect(ruleState('อย่างน้อย 8 ตัวอักษร')).toBe('ผ่านแล้ว')
      expect(ruleState('ไม่เป็นตัวเลขล้วน')).toBe('ผ่านแล้ว')
    })

    it('ตัวเลขล้วนยาวพอ → ข้อความยาวผ่าน แต่ข้อไม่เป็นตัวเลขล้วนไม่ผ่าน (รวมเลขไทย)', async () => {
      await openForm()

      fillPasswords('12345678')
      expect(ruleState('อย่างน้อย 8 ตัวอักษร')).toBe('ผ่านแล้ว')
      expect(ruleState('ไม่เป็นตัวเลขล้วน')).toBe('ยังไม่ผ่าน')

      fillPasswords('๑๒๓๔๕๖๗๘')
      expect(ruleState('ไม่เป็นตัวเลขล้วน')).toBe('ยังไม่ผ่าน')
    })

    it('นับตัวอักษรแบบเดียวกับ backend: อีโมจิ 1 ตัว = 1 ตัวอักษร (ไม่ใช่ 2)', async () => {
      await openForm()

      // 4 อีโมจิ + 3 ตัวอักษร = 7 ตัวอักษร (ถ้านับแบบ UTF-16 จะได้ 11 และติ๊กผ่านผิด ๆ)
      fillPasswords('😀😀😀😀abc')
      expect(ruleState('อย่างน้อย 8 ตัวอักษร')).toBe('ยังไม่ผ่าน')

      fillPasswords('😀😀😀😀abcd')
      expect(ruleState('อย่างน้อย 8 ตัวอักษร')).toBe('ผ่านแล้ว')
    })

    it('กดส่งตอนยังไม่ผ่าน → ข้อที่ไม่ผ่านกลายเป็นสีแดง และไม่ส่งอะไรไป backend', async () => {
      const { mock } = await openForm({ [RESET]: () => jsonResponse({}) })
      fillPasswords('12345')

      submit()

      await waitFor(() =>
        expect(screen.getByText('อย่างน้อย 8 ตัวอักษร').closest('li')).toHaveClass('text-error-800'),
      )
      expect(screen.getByText('ไม่เป็นตัวเลขล้วน').closest('li')).toHaveClass('text-error-800')
      expect(mock.countOf(RESET)).toBe(0)
    })
  })

  it('ตั้งรหัสสำเร็จ → ส่งโทเคน+รหัสใหม่ แล้วไปหน้า login พร้อมข้อความสำเร็จ (ไม่ล็อกอินให้)', async () => {
    const { mock, router } = await openForm({ [RESET]: () => jsonResponse({}) })
    fillPasswords('Brand-New-Pw-88')

    submit()

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(mock.calls.find((c) => c.url === '/api/auth/reset-password/')?.body).toEqual({
      token: 'abc-DEF_123',
      password: 'Brand-New-Pw-88',
    })
    expect(await screen.findByRole('status')).toHaveTextContent('ตั้งรหัสผ่านใหม่แล้ว')
    expect(screen.getByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
    // ไม่มีรหัสผ่านค้างในหน้า
    expect(document.body.innerHTML).not.toContain('Brand-New-Pw-88')
  })

  it('คนที่ล็อกอินค้างอยู่ (เซสชันตายแล้ว) ตั้งรหัสเสร็จต้องได้เห็นหน้า login ไม่ถูกเด้งกลับ dashboard', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }),
      [CHECK]: okCheck,
      [RESET]: () => jsonResponse({}),
    })
    const router = renderApp('/reset-password?token=abc')
    await screen.findByRole('heading', { name: 'ตั้งรหัสผ่านใหม่' })
    fillPasswords('Brand-New-Pw-88')

    submit()

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(await screen.findByRole('heading', { name: 'เข้าสู่ระบบ' })).toBeInTheDocument()
  })

  it('ยืนยันรหัสผ่านไม่ตรง → บอกใต้ช่อง และไม่ส่งอะไรไป backend', async () => {
    const { mock } = await openForm({ [RESET]: () => jsonResponse({}) })
    fillPasswords('Brand-New-Pw-88', 'Different-Pw-99')

    submit()

    expect(await screen.findByText('รหัสผ่านสองช่องไม่ตรงกัน')).toBeInTheDocument()
    expect(screen.getByLabelText('ยืนยันรหัสผ่านใหม่')).toHaveAttribute('aria-invalid', 'true')
    expect(mock.countOf(RESET)).toBe(0)
  })

  it('backend ปฏิเสธเพราะรหัสคนใช้กัน → ข้อความไทยใต้ช่อง (ไม่อยู่ในรายการติ๊ก) และไม่แสดงข้อความดิบ', async () => {
    await openForm({
      [RESET]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { password: ['This password is too common.'] },
            error_codes: { password: ['password_too_common'] },
          },
          400,
        ),
    })
    fillPasswords('password1234')

    submit()

    expect(await screen.findByText('รหัสผ่านนี้คาดเดาง่ายเกินไป')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('This password')
    expect(screen.getByLabelText('รหัสผ่านใหม่')).toHaveAttribute('aria-invalid', 'true')
    // ยังอยู่หน้าเดิม ลองใหม่ด้วยลิงก์เดิมได้
    expect(screen.getByRole('button', { name: 'ตั้งรหัสผ่าน' })).toBeEnabled()
  })

  it('backend ปฏิเสธเพราะคล้ายชื่อหรืออีเมล → ข้อความไทยใต้ช่อง แล้วแก้รหัสแล้วข้อความหายไป', async () => {
    await openForm({
      [RESET]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { password: ['x'] },
            error_codes: { password: ['password_too_similar'] },
          },
          400,
        ),
    })
    fillPasswords('manee@example.cm')
    submit()
    expect(await screen.findByText('รหัสผ่านคล้ายชื่อหรืออีเมลของคุณเกินไป')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('รหัสผ่านใหม่'), { target: { value: 'Other-Pw-12345' } })

    expect(screen.queryByText('รหัสผ่านคล้ายชื่อหรืออีเมลของคุณเกินไป')).not.toBeInTheDocument()
  })

  it('backend ปฏิเสธข้อที่อยู่ในรายการติ๊ก (แม้หน้าเว็บนับว่าผ่าน) → ข้อนั้นเป็นสีแดง ไม่โชว์ติ๊กเขียวหลอก', async () => {
    await openForm({
      [RESET]: () =>
        jsonResponse(
          {
            code: 'validation_error',
            errors: { password: ['x'] },
            error_codes: { password: ['password_entirely_numeric'] },
          },
          400,
        ),
    })
    // จำลองว่า backend เห็นต่างจากหน้าเว็บ: หน้าเว็บนับว่ารหัสนี้ผ่านทุกข้อ แต่ backend ปฏิเสธข้อ "ไม่เป็นตัวเลขล้วน"
    fillPasswords('Looks-Fine-Pw-1')
    submit()

    await waitFor(() =>
      expect(screen.getByText('ไม่เป็นตัวเลขล้วน').closest('li')).toHaveClass('text-error-800'),
    )
    expect(ruleState('ไม่เป็นตัวเลขล้วน')).toBe('ยังไม่ผ่าน')
  })

  it.each(['token_invalid', 'token_expired'])(
    'ลิงก์ใช้ไม่ได้ตอนเปิดหน้า (%s) → การ์ด "ลิงก์นี้ใช้ไม่ได้แล้ว" พร้อมปุ่มขอลิงก์ใหม่ที่พาไปหน้าลืมรหัสผ่าน',
    async (code) => {
      mockFetch({ [REFRESH]: noSession, [CHECK]: () => errorResponse(400, code) })
      const router = renderApp('/reset-password?token=abc')

      expect(await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })).toBeInTheDocument()
      expect(screen.queryByLabelText('รหัสผ่านใหม่')).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('link', { name: 'ขอลิงก์ใหม่' }))
      await waitFor(() => expect(router.state.location.pathname).toBe('/forgot-password'))
    },
  )

  it('ไม่มีโทเคนใน URL → ถือว่าลิงก์ใช้ไม่ได้ โดยไม่เรียก backend', async () => {
    const mock = mockFetch({ [REFRESH]: noSession })
    renderApp('/reset-password')

    expect(await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })).toBeInTheDocument()
    expect(mock.countOf(CHECK)).toBe(0)
  })

  it('ลิงก์ถูกใช้/หมดอายุระหว่างที่กรอกฟอร์ม → เปลี่ยนเป็นการ์ดลิงก์ใช้ไม่ได้', async () => {
    await openForm({ [RESET]: () => errorResponse(400, 'token_expired') })
    fillPasswords('Brand-New-Pw-88')

    submit()

    expect(await screen.findByRole('heading', { name: 'ลิงก์นี้ใช้ไม่ได้แล้ว' })).toBeInTheDocument()
  })

  it('เครือข่ายล่มตอนตรวจลิงก์ → ให้ลองอีกครั้ง (ไม่บอกว่าลิงก์เสีย) แล้วกดลองซ้ำสำเร็จ', async () => {
    let attempt = 0
    mockFetch({
      [REFRESH]: noSession,
      [CHECK]: () => {
        attempt += 1
        if (attempt === 1) throw new TypeError('offline')
        return okCheck()
      },
    })
    renderApp('/reset-password?token=abc')

    expect(await screen.findByRole('heading', { name: 'เชื่อมต่อระบบไม่ได้' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'ลองอีกครั้ง' }))

    expect(await screen.findByRole('heading', { name: 'ตั้งรหัสผ่านใหม่' })).toBeInTheDocument()
  })

  it('เครือข่ายล่มตอนกดตั้งรหัส → กล่องแจ้งเตือนสีแดง และกรอกไว้เดิมให้ลองใหม่', async () => {
    await openForm({
      [RESET]: () => {
        throw new TypeError('offline')
      },
    })
    fillPasswords('Brand-New-Pw-88')

    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('เชื่อมต่อระบบไม่ได้')
    expect(screen.getByLabelText('รหัสผ่านใหม่')).toHaveValue('Brand-New-Pw-88')
  })

  it('ระหว่างรอ backend ปุ่มถูกปิดเพื่อกันกดซ้ำ', async () => {
    const gate = deferred<Response>()
    const { mock } = await openForm({ [RESET]: () => gate.promise })
    fillPasswords('Brand-New-Pw-88')

    submit()

    const button = await screen.findByRole('button', { name: 'กำลังบันทึก' })
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(mock.countOf(RESET)).toBe(1)
    gate.resolve(jsonResponse({}))
  })

  it('ข้อความเปลี่ยนตามภาษา (อังกฤษ)', async () => {
    await openForm()

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))

    expect(await screen.findByRole('heading', { name: 'Set a new password' })).toBeInTheDocument()
    expect(screen.getByText('For the account manee@example.com')).toBeInTheDocument()
    expect(screen.getByText('At least 8 characters')).toBeInTheDocument()
  })
})
