import { beforeEach, describe, expect, it } from 'vitest'
import { clearUserId, getLanguage, getUserId, saveLanguage, saveUserId } from './storage'

describe('anonymous profile pointer', () => {
  beforeEach(() => localStorage.clear())

  it('stores and retrieves a versioned user id', () => {
    saveUserId('27ac5f03-2605-4e74-aad6-7678cb9d8c94')

    expect(getUserId()).toBe('27ac5f03-2605-4e74-aad6-7678cb9d8c94')
  })

  it('ignores malformed or unsupported stored data', () => {
    localStorage.setItem('fitness-tracker:user:v1', '{broken json')
    expect(getUserId()).toBeNull()

    localStorage.setItem(
      'fitness-tracker:user:v1',
      JSON.stringify({ version: 2, userId: 'old-id' }),
    )
    expect(getUserId()).toBeNull()
  })

  it('removes the local pointer without needing authentication', () => {
    saveUserId('temporary-id')
    clearUserId()

    expect(getUserId()).toBeNull()
  })

  it('stores the language preference separately from profile data', () => {
    expect(getLanguage()).toBe('zh-TW')
    saveLanguage('en')
    expect(getLanguage()).toBe('en')
  })
})
