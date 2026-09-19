import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { setAccessToken, subscribeToSession, type SessionEvent } from '../auth/session'
import {
  deferred,
  errorResponse,
  jsonResponse,
  makeUser,
  mockFetch,
  rejection,
} from '../test/fetchMock'
import { ApiError } from './apiError'
import { apiFetch } from './apiClient'

const ME = 'GET /api/auth/me/'
const REFRESH = 'POST /api/auth/refresh/'

let events: SessionEvent[]
let unsubscribe: () => void

beforeEach(() => {
  events = []
  unsubscribe = subscribeToSession((event) => events.push(event))
})

afterEach(() => {
  unsubscribe()
})

// backend ที่ตอบ 200 เฉพาะเมื่อได้ token ที่ถูกต้อง มิฉะนั้นตอบ 401 เหมือน token หมดอายุ
function protectedRoute(validToken: string) {
  return ({ headers }: { headers: Headers }) =>
    headers.get('Authorization') === `Bearer ${validToken}`
      ? jsonResponse({ id: 1 })
      : errorResponse(401, 'token_not_valid')
}

describe('apiFetch', () => {
  it('แนบ access token ที่เก็บไว้ในหน่วยความจำ', async () => {
    setAccessToken('good')
    const mock = mockFetch({ [ME]: protectedRoute('good') })

    await expect(apiFetch('/api/auth/me/')).resolves.toEqual({ id: 1 })

    expect(mock.calls[0].headers.get('Authorization')).toBe('Bearer good')
  })

  it('token หมดอายุ (401): ขอ token ใหม่แล้วลองซ้ำอัตโนมัติ ผู้ใช้ไม่ต้องรู้ตัว', async () => {
    setAccessToken('expired')
    const mock = mockFetch({
      [ME]: protectedRoute('fresh'),
      [REFRESH]: () => jsonResponse({ access: 'fresh', user: makeUser() }),
    })

    const result = await apiFetch('/api/auth/me/')

    expect(result).toEqual({ id: 1 })
    expect(mock.calls.map((c) => `${c.method} ${c.url}`)).toEqual([ME, REFRESH, ME])
    // คำขอที่ลองซ้ำใช้ token ใหม่
    expect(mock.calls[2].headers.get('Authorization')).toBe('Bearer fresh')
  })

  it('เซสชันหมดจริง (refresh ได้ 401): โยน 401 เดิม และแจ้งว่าเซสชันหมด', async () => {
    setAccessToken('expired')
    mockFetch({
      [ME]: protectedRoute('never'),
      [REFRESH]: () => errorResponse(401, 'invalid_refresh_token'),
    })

    const error = await rejection(apiFetch('/api/auth/me/'))

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(401)
    expect(events).toEqual([{ type: 'lost' }])
  })

  it('หลาย 401 พร้อมกัน ขอ token ใหม่เพียงครั้งเดียว', async () => {
    setAccessToken('expired')
    const gate = deferred<Response>()
    const mock = mockFetch({
      [ME]: protectedRoute('fresh'),
      [REFRESH]: () => gate.promise,
    })

    const requests = [apiFetch('/api/auth/me/'), apiFetch('/api/auth/me/'), apiFetch('/api/auth/me/')]
    // รอให้ทั้ง 3 คำขอได้ 401 และเข้าคิวรอ refresh ก่อน แล้วค่อยปล่อยผล
    await new Promise((resolve) => setTimeout(resolve, 0))
    gate.resolve(jsonResponse({ access: 'fresh', user: makeUser() }))
    const results = await Promise.all(requests)

    expect(results).toEqual([{ id: 1 }, { id: 1 }, { id: 1 }])
    expect(mock.countOf(REFRESH)).toBe(1)
  })

  it('ลองซ้ำครั้งเดียว: ถ้ายัง 401 หลังได้ token ใหม่ ให้โยน error ไม่วนซ้ำ', async () => {
    setAccessToken('expired')
    const mock = mockFetch({
      [ME]: () => errorResponse(401, 'token_not_valid'),
      [REFRESH]: () => jsonResponse({ access: 'fresh', user: makeUser() }),
    })

    const error = await rejection(apiFetch('/api/auth/me/'))

    expect(error.status).toBe(401)
    expect(mock.countOf(ME)).toBe(2)
    expect(mock.countOf(REFRESH)).toBe(1)
  })

  it('error อื่นที่ไม่ใช่ 401 ไม่ถูกลองซ้ำและไม่ขอ token ใหม่', async () => {
    setAccessToken('good')
    const mock = mockFetch({ [ME]: () => errorResponse(403, 'permission_denied') })

    const error = await rejection(apiFetch('/api/auth/me/'))

    expect(error.code).toBe('permission_denied')
    expect(mock.countOf(REFRESH)).toBe(0)
  })

  it('ขอ token ใหม่ไม่ได้เพราะเครือข่ายล่ม: โยน network_error และไม่ถือว่าเซสชันหมด', async () => {
    setAccessToken('expired')
    let refreshCalls = 0
    mockFetch({
      [ME]: () => errorResponse(401, 'token_not_valid'),
      [REFRESH]: () => {
        refreshCalls += 1
        throw new TypeError('offline')
      },
    })

    const error = await rejection(apiFetch('/api/auth/me/'))

    expect(refreshCalls).toBe(1)
    expect(error.code).toBe('network_error')
    expect(events).toEqual([])
  })
})
