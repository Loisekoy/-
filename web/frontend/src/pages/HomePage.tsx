import { ArrowRight, BarChart3, BrainCircuit, Database, Dumbbell, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { getUserId } from '../lib/storage'

export default function HomePage() {
  const { t, tList } = useI18n()
  const hasProfile = Boolean(getUserId())
  const steps = tList('home.steps')

  return (
    <main className="home-page">
      <section className="home-hero">
        <div className="home-hero__copy">
          <p className="eyebrow">Fitness Tracking Management System</p>
          <h1>{t('home.title')}</h1>
          <p>{t('home.subtitle')}</p>
          <div className="home-hero__actions">
            <Link className="button button--primary button--large" to={hasProfile ? '/plan' : '/onboarding'}>
              {hasProfile ? t('home.primaryExisting') : t('home.primaryNew')}
              <ArrowRight size={20} aria-hidden="true" />
            </Link>
            <Link className="button button--secondary button--large" to={hasProfile ? '/onboarding' : '/database'}>
              {hasProfile ? t('home.secondaryExisting') : t('home.secondaryNew')}
            </Link>
          </div>
          <p className="home-hero__privacy">{t('home.privacy')}</p>
        </div>

        <div className="home-hero__system" aria-label="系統流程摘要">
          <div className="system-line">
            <span className="system-line__number">01</span>
            <UserRound size={26} aria-hidden="true" />
            <div><strong>{steps[0]}</strong><span>Name / Age / Height / Weight</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">02</span>
            <Dumbbell size={26} aria-hidden="true" />
            <div><strong>{steps[1]} + {steps[2]}</strong><span>M:N user_body_parts</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">03</span>
            <Database size={26} aria-hidden="true" />
            <div><strong>Database 找候選 Exercise</strong><span>body part / difficulty / equipment</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">04</span>
            <BrainCircuit size={26} aria-hidden="true" />
            <div><strong>{steps[3]}</strong><span>LLM JSON → Backend validation</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">05</span>
            <BarChart3 size={26} aria-hidden="true" />
            <div><strong>{steps[4]}</strong><span>Workout sets / volume / history</span></div>
          </div>
        </div>
      </section>
    </main>
  )
}
