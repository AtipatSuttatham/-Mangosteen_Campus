import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/apiError'
import { deferred, errorResponse, jsonResponse, makeUser, mockFetch } from '../test/fetchMock'
import { AuthProvider } from './AuthProvider'
import { clearSession, storeSession } from './session'
import { useAuth } from './useAuth'

const REFRESH = 'POST /api/auth/refresh/'
const LOGIN = 'POST /api/auth/login/'
const LOGOUT = 'POST /api/auth/logout/'

// component ทดสอบ: แสดงสถานะที่ AuthProvider ให้ และมีปุ่มสั่ง login / logout
function Probe({ onLoginError }: { onLoginError?: (error: unknown) => void }) {
  const { status, user, login, logout } = useAuth()
  return (
    <div>
      <p data-testid="status">{status}</p>
      <p data-testid="user">{user ? `${user.email} (${user.role})` : 'none'}</p>
      <button onClick={() => void login('T0042', 'pw').catch((e) => onLoginError?.(e))}>login</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  )
}

function renderProbe(props: Parameters<typeof Probe>[0] = {}) {
  render(
    <AuthProvider>
      <Probe {...props} />
    </AuthProvider>,
  )
}

async function expectStatus(status: string) {
  await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent(status))
}

describe('AuthProvider', () => {
  it('เริ่มที่ loading แล้วกู้เซสชันจาก cookie สำเร็จ → authenticated พร้อมข้อมูลผู้ใช้', async () => {
    const gate = deferred<Response>()
    mockFetch({ [REFRESH]: () => gate.promise })

    renderProbe()
    expect(screen.getByTestId('status')).toHaveTextContent('loading')

    gate.resolve(jsonResponse({ access: 'a', user: makeUser({ role: 'student' }) }))
    await expectStatus('authenticated')
    expect(screen.getByTestId('user')).toHaveTextContent('teacher@example.com (student)')
  })

  it('ไม่มีเซสชัน (refresh ได้ 401) → unauthenticated', async () => {
    mockFetch({ [REFRESH]: () => errorResponse(401, 'invalid_refresh_token') })

    renderProbe()

    await expectStatus('unauthenticated')
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('เครือข่ายล่มตอนเปิดเว็บ → unauthenticated (ไม่ค้างที่ loading)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    renderProbe()

    await expectStatus('unauthenticated')
  })

  it('ใน React StrictMode ที่รันซ้ำ ก็ขอ refresh เพียงครั้งเดียว (ไม่ทำให้ token ชนกัน)', async () => {
    const mock = mockFetch({ [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser() }) })

    render(
      <StrictMode>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </StrictMode>,
    )

    await expectStatus('authenticated')
    expect(mock.countOf(REFRESH)).toBe(1)
  })

  it('login สำเร็จ → authenticated', async () => {
    mockFetch({
      [REFRESH]: () => errorResponse(401, 'invalid_refresh_token'),
      [LOGIN]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'admin' }) }),
    })
    renderProbe()
    await expectStatus('unauthenticated')

    fireEvent.click(screen.getByText('login'))

    await expectStatus('authenticated')
    expect(screen.getByTestId('user')).toHaveTextContent('(admin)')
  })

  it('login ไม่สำเร็จ → โยน ApiError (มี code) และยังคง unauthenticated', async () => {
    mockFetch({
      [REFRESH]: () => errorResponse(401, 'invalid_refresh_token'),
      [LOGIN]: () => errorResponse(401, 'invalid_credentials'),
    })
    const onLoginError = vi.fn()
    renderProbe({ onLoginError })
    await expectStatus('unauthenticated')

    fireEvent.click(screen.getByText('login'))

    await waitFor(() => expect(onLoginError).toHaveBeenCalled())
    const error = onLoginError.mock.calls[0][0]
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('invalid_credentials')
    expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated')
  })

  it('logout → unauthenticated แม้ backend ตอบไม่สำเร็จ', async () => {
    mockFetch({
      [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser() }),
      [LOGOUT]: () => errorResponse(500, 'server_error'),
    })
    renderProbe()
    await expectStatus('authenticated')

    fireEvent.click(screen.getByText('logout'))

    await expectStatus('unauthenticated')
  })

  it('เซสชันหมดกลางทาง (เช่น refresh ได้ 401 ระหว่างเรียก API) → unauthenticated', async () => {
    mockFetch({ [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser() }) })
    renderProbe()
    await expectStatus('authenticated')

    clearSession()

    await expectStatus('unauthenticated')
  })

  it('refresh ในภายหลังได้ข้อมูลผู้ใช้ใหม่ (เช่น role เปลี่ยน) → อัปเดตทันที', async () => {
    mockFetch({ [REFRESH]: () => jsonResponse({ access: 'a', user: makeUser({ role: 'teacher' }) }) })
    renderProbe()
    await expectStatus('authenticated')

    storeSession({ access: 'b', user: makeUser({ role: 'student' }) })

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('(student)'))
  })
})
