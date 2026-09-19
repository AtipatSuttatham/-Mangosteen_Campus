import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LanguageToggle } from './LanguageToggle'

describe('LanguageToggle', () => {
  it('เริ่มที่ภาษาไทย (TH ถูกเลือก)', () => {
    render(<LanguageToggle />)

    expect(screen.getByRole('button', { name: 'TH' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('กด EN → เปลี่ยนภาษา และตั้ง lang ของหน้าเว็บให้ตรง', () => {
    render(<LanguageToggle />)

    fireEvent.click(screen.getByRole('button', { name: 'EN' }))

    expect(screen.getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'true')
    expect(document.documentElement.lang).toBe('en')
  })
})
