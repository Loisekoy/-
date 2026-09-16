import { ArrowRight, BarChart3, CalendarCheck2, Dumbbell } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getUserId } from '../lib/storage'

export default function HomePage() {
  const hasProfile = Boolean(getUserId())

  return (
    <main className="home-page">
      <section className="home-hero">
        <div className="home-hero__copy">
          <h1>開始建立我的健身計畫</h1>
          <p>
            根據你的目標、訓練經驗與想加強的部位，產生每週課表，並用每一組真實紀錄看見進步。
          </p>
          <div className="home-hero__actions">
            <Link className="button button--primary button--large" to={hasProfile ? '/plan' : '/onboarding'}>
              {hasProfile ? '繼續我的計畫' : '開始建立我的健身計畫'}
              <ArrowRight size={20} aria-hidden="true" />
            </Link>
            {hasProfile ? (
              <Link className="button button--secondary button--large" to="/onboarding">
                建立新資料
              </Link>
            ) : (
              <Link className="button button--secondary button--large" to="/database">
                查看資料庫系統
              </Link>
            )}
          </div>
          <p className="home-hero__privacy">
            不需要登入或密碼。資料識別碼只保存在你的瀏覽器；請勿輸入敏感個資。
          </p>
        </div>
        <div className="home-hero__system" aria-label="系統流程摘要">
          <div className="system-line">
            <span className="system-line__number">01</span>
            <Dumbbell size={26} aria-hidden="true" />
            <div><strong>建立資料</strong><span>目標、經驗與重點部位</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">02</span>
            <CalendarCheck2 size={26} aria-hidden="true" />
            <div><strong>取得課表</strong><span>規則式推薦，不使用 AI API</span></div>
          </div>
          <div className="system-line">
            <span className="system-line__number">03</span>
            <BarChart3 size={26} aria-hidden="true" />
            <div><strong>記錄進步</strong><span>Weight、Reps 與 Training Volume</span></div>
          </div>
        </div>
      </section>
    </main>
  )
}
