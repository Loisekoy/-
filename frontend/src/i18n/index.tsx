import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getLanguage, saveLanguage } from '../lib/storage'
import en from './en.json'
import zhTW from './zh-TW.json'

export type Language = 'zh-TW' | 'en'

const dictionaries = {
  'zh-TW': zhTW,
  en,
} as const

type Dictionary = typeof zhTW
type TranslationValue = string | string[] | Record<string, unknown>

interface I18nContextValue {
  language: Language
  setLanguage: (language: Language) => void
  t: (key: string) => string
  tList: (key: string) => string[]
}

const I18nContext = createContext<I18nContextValue | null>(null)

function lookup(dictionary: Dictionary, key: string): TranslationValue | undefined {
  return key.split('.').reduce<unknown>((current, part) => {
    if (typeof current !== 'object' || current === null || !(part in current)) return undefined
    return (current as Record<string, unknown>)[part]
  }, dictionary) as TranslationValue | undefined
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => getLanguage())

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const value = useMemo<I18nContextValue>(() => {
    const dictionary = dictionaries[language]
    return {
      language,
      setLanguage(nextLanguage) {
        setLanguageState(nextLanguage)
        saveLanguage(nextLanguage)
        document.documentElement.lang = nextLanguage
      },
      t(key) {
        const result = lookup(dictionary, key)
        return typeof result === 'string' ? result : key
      },
      tList(key) {
        const result = lookup(dictionary, key)
        return Array.isArray(result) ? result.filter((item): item is string => typeof item === 'string') : []
      },
    }
  }, [language])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext)
  if (!value) {
    throw new Error('useI18n must be used inside I18nProvider')
  }
  return value
}
