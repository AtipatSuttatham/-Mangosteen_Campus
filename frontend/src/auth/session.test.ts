import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/apiError'
import {
  deferred,
  errorResponse,
  jsonResponse,
  makeUser,
  mockFetch,
  rejection,
} from '../test/fetchMock'
import {
  getAccessToken,
  loginWithPassword,
  logout,
  refreshSession,
  setAccessToken,
  subscribeToSession,
  type SessionEvent,
} from './session'

const LOGIN = 'POST /api/auth/login/'
const REFRESH = 'POST /api/auth/refresh/'
const LOGOUT = 'POST /api/auth/logout/'

// เก็บสัญญาณที่ session.ts ส่งออกมาระหว่าง test
let events: SessionEvent[]
let unsubscribe: () => void

beforeEach(() => {
  events = []
  unsubscribe = subscribeToSession((event) => events.push(event))
})

afterEach(() => {
  unsubscribe()
})

describe('loginWithPassword', () => {
  it('ส่งรหัส/อีเมลกับรหัสผ่าน เก็บ access token ในหน่วยความจำ และแจ้งผู้ใช้ที่ล็อกอิน', async () => {
    const user = makeUser()
    const mock = mockFetch({ [LOGIN]: () => jsonResponse({ access: 'token-1', user }) })

    const session = await loginWithPassword('T0042', 'secret')

    expect(session.user).toEqual(user)
    expect(getAccessToken()).toBe('token-1')
    expect(mock.calls[0].body).toEqual({ identifier: 'T0042', password: 'secret' })
    // login ไม่ต้องแนบ token เดิม
    expect(mock.calls[0].headers.has('Authorization')).toBe(false)
    expect(events).toEqual([{ type: 'refreshed', user }])
  })

  it('เมื่อ login ไม่สำเร็จ โยน ApiError และไม่เปลี่ยนสถานะเซสชัน', async () => {
    mockFetch({ [LOGIN]: () => errorResponse(401, 'invalid_credentials') })

    const error = await rejection(loginWithPassword('T0042', 'wrong'))

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('invalid_credentials')
    expect(getAccessToken()).toBeNull()
    expect(events).toEqual([])
  })
})

describe('refreshSession', () => {
  it('ส่ง header X-Requested-With (backend บังคับ) เก็บ token ใหม่ และแจ้งผู้ใช้ล่าสุด', async () => {
    const user = makeUser({ role: 'student' })
    const mock = mockFetch({ [REFRESH]: () => jsonResponse({ access: 'token-2', user }) })

    const session = await refreshSession()

    expect(session?.access).toBe('token-2')
    expect(getAccessToken()).toBe('token-2')
    expect(mock.calls[0].headers.get('X-Requested-With')).toBe('fetch')
    expect(events).toEqual([{ type: 'refreshed', user }])
  })

  it('401 = ยังไม่ได้ล็อกอิน: คืน null ล้าง token และแจ้งว่าเซสชันหมด', async () => {
    setAccessToken('old-token')
    mockFetch({ [REFRESH]: () => errorResponse(401, 'invalid_refresh_token') })

    const session = await refreshSession()

    expect(session).toBeNull()
    expect(getAccessToken()).toBeNull()
    expect(events).toEqual([{ type: 'lost' }])
  })

  it('เครือข่ายล่ม: โยน error ต่อ ไม่ล้าง token และไม่ถือว่าเซสชันหมด', async () => {
    setAccessToken('old-token')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    const error = await rejection(refreshSession())

    expect(error.code).toBe('network_error')
    expect(getAccessToken()).toBe('old-token')
    expect(events).toEqual([])
  })

  it('คำขอที่ชนกันใช้ผลของ refresh ครั้งเดียว (refresh token ใช้ได้ครั้งเดียว)', async () => {
    const gate = deferred<Response>()
    const mock = mockFetch({ [REFRESH]: () => gate.promise })

    const first = refreshSession()
    const second = refreshSession()
    gate.resolve(jsonResponse({ access: 'token-3', user: makeUser() }))
    const [a, b] = await Promise.all([first, second])

    expect(mock.countOf(REFRESH)).toBe(1)
    expect(a?.access).toBe('token-3')
    expect(b?.access).toBe('token-3')
  })

  it('หลังคำขอก่อนหน้าเสร็จแล้ว การเรียกครั้งถัดไปยิงคำขอใหม่', async () => {
    const mock = mockFetch({ [REFRESH]: () => jsonResponse({ access: 't', user: makeUser() }) })

    await refreshSession()
    await refreshSession()

    expect(mock.countOf(REFRESH)).toBe(2)
  })

  it('ใช้ Web Locks ให้ทีละแท็บเมื่อเบราว์เซอร์รองรับ', async () => {
    const request = vi.fn((_name: string, callback: () => Promise<unknown>) => callback())
    vi.stubGlobal('navigator', { locks: { request } })
    mockFetch({ [REFRESH]: () => jsonResponse({ access: 't', user: makeUser() }) })

    await refreshSession()

    expect(request).toHaveBeenCalledWith('mangosteen-auth-refresh', expect.any(Function))
  })
})

describe('logout', () => {
  it('เรียก backend เพิกถอน token ล้างเซสชัน และคืน true', async () => {
    setAccessToken('token')
    const mock = mockFetch({ [LOGOUT]: () => new Response(null, { status: 204 }) })

    const revoked = await logout()

    expect(revoked).toBe(true)
    expect(mock.calls[0].headers.get('X-Requested-With')).toBe('fetch')
    expect(getAccessToken()).toBeNull()
    expect(events).toEqual([{ type: 'lost' }])
  })

  it('backend ตอบไม่สำเร็จ: ยังล้างเซสชันในหน้าเว็บ แต่คืน false', async () => {
    setAccessToken('token')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))

    const revoked = await logout()

    expect(revoked).toBe(false)
    expect(getAccessToken()).toBeNull()
    expect(events).toEqual([{ type: 'lost' }])
  })
})
