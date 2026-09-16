import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import HomePage from './HomePage'

describe('public home page', () => {
  beforeEach(() => localStorage.clear())

  it('offers direct onboarding and contains no authentication actions', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { name: '開始建立我的健身計畫' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /開始建立我的健身計畫/ })).toHaveAttribute(
      'href',
      '/onboarding',
    )
    expect(screen.queryByText(/login|register|sign in|sign up/i)).not.toBeInTheDocument()
  })
})
