import { describe, expect, it } from 'vitest'

import { characterCount, meetsPasswordRules, PASSWORD_RULES } from './passwordRules'

describe('กฎรหัสผ่านที่ตรวจในหน้าเว็บ', () => {
  it('นับตัวอักษรเป็นอักขระ ไม่ใช่หน่วย UTF-16 (ตรงกับ backend)', () => {
    expect(characterCount('abc')).toBe(3)
    expect(characterCount('😀')).toBe(1)
    expect(characterCount('ก็')).toBe(2)
    expect(characterCount('')).toBe(0)
  })

  it.each([
    ['1234567', false],
    ['12345678', false],
    ['๑๒๓๔๕๖๗๘', false],
    ['abcdefgh', true],
    ['abc12345', true],
    ['1234567a', true],
    ['pass word 1', true],
    ['', false],
    ['สวัสดีครับผม', true],
  ])('meetsPasswordRules(%j) = %s', (password, expected) => {
    expect(meetsPasswordRules(password)).toBe(expected)
  })

  it('ขอบเขตความยาว: 7 ตัวไม่ผ่าน 8 ตัวผ่าน', () => {
    expect(meetsPasswordRules('abcdefg')).toBe(false)
    expect(meetsPasswordRules('abcdefgh')).toBe(true)
  })

  it('ผูกกับรหัสกฎของ backend สองข้อที่ตรวจเองได้', () => {
    expect(PASSWORD_RULES.map((rule) => rule.backendCode)).toEqual([
      'password_too_short',
      'password_entirely_numeric',
    ])
  })
})
