import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from './apiError'
import { RESEND_COOLDOWN_SECONDS, useResend } from './useResend'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// เดินเวลาทีละ 1 วินาที: ตัวนับตั้งตัวจับเวลารอบใหม่หลังแต่ละครั้งที่หน้าจอวาดใหม่ (ในเบราว์เซอร์จริงก็เป็นแบบนี้)
// จึงต้องปล่อยให้ React วาดระหว่างวินาทีด้วย ไม่ข้ามรวดเดียว
function tick(seconds: number) {
  for (let i = 0; i < seconds; i += 1) {
    act(() => {
      vi.advanceTimersByTime(1000)
    })
  }
}

describe('useResend (ปุ่มส่งลิงก์อีกครั้ง)', () => {
  it('ส่งสำเร็จ → สถานะ sent และนับถอยหลัง 60 วินาที จนกดได้อีกครั้ง', async () => {
    const send = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useResend(send))

    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    expect(send).toHaveBeenCalledWith('a@example.com')
    expect(result.current.status).toBe('sent')
    expect(result.current.secondsLeft).toBe(RESEND_COOLDOWN_SECONDS)

    tick(30)
    expect(result.current.secondsLeft).toBe(30)

    tick(30)
    expect(result.current.secondsLeft).toBe(0)
  })

  it('ระหว่างนับถอยหลัง trigger ซ้ำไม่ส่งอะไรไป และพอครบเวลากดได้อีก', async () => {
    const send = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useResend(send))
    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    await act(async () => {
      await result.current.trigger('a@example.com')
    })
    expect(send).toHaveBeenCalledTimes(1)

    tick(RESEND_COOLDOWN_SECONDS)
    await act(async () => {
      await result.current.trigger('a@example.com')
    })
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('ส่งไม่สำเร็จ → สถานะ error พร้อม code และไม่นับถอยหลัง (ลองใหม่ได้ทันที)', async () => {
    const send = vi.fn().mockRejectedValue(new ApiError(500, 'something_new'))
    const { result } = renderHook(() => useResend(send))

    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    expect(result.current.status).toBe('error')
    expect(result.current.errorCode).toBe('something_new')
    expect(result.current.secondsLeft).toBe(0)
  })

  it('error ที่ไม่ใช่ ApiError (บั๊ก/เครือข่ายแบบอื่น) ได้ code = unknown_error', async () => {
    const send = vi.fn().mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useResend(send))

    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    expect(result.current.errorCode).toBe('unknown_error')
  })

  it('ระหว่างกำลังส่ง (ยังไม่ตอบ) กดซ้ำไม่ทำให้ส่งซ้อน', async () => {
    let finish!: () => void
    const send = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve
        }),
    )
    const { result } = renderHook(() => useResend(send))

    let first!: Promise<void>
    act(() => {
      first = result.current.trigger('a@example.com')
    })
    expect(result.current.status).toBe('sending')
    await act(async () => {
      await result.current.trigger('a@example.com')
    })
    expect(send).toHaveBeenCalledTimes(1)

    await act(async () => {
      finish()
      await first
    })
    expect(result.current.status).toBe('sent')
  })

  it('ส่งสำเร็จหลังเคย error → ล้าง code ของ error เดิม', async () => {
    const send = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, 'something_new'))
      .mockResolvedValueOnce(undefined)
    const { result } = renderHook(() => useResend(send))
    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    await act(async () => {
      await result.current.trigger('a@example.com')
    })

    expect(result.current.status).toBe('sent')
    expect(result.current.errorCode).toBeNull()
  })
})
