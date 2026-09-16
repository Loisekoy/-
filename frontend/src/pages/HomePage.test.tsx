import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../i18n'
import HomePage from './HomePage'

describe('public home page', () => {
  beforeEach(() => localStorage.clear())

  it('offers direct onboarding and contains no authentication actions', () => {
    render(
      <I18nProvider>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </I18nProvider>,
    )

    expect(
      screen.getByRole('heading', { name: '健身訓練，從適合你的計畫開始。' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /開始建立我的健身計畫/ })).toHaveAttribute(
      'href',
      '/onboarding',
    )
    expect(screen.queryByText(/login|register|sign in|sign up/i)).not.toBeInTheDocument()
  })
})
