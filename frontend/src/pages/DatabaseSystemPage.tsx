import { Database, KeyRound, Network, Table2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { apiRequest } from '../api/client'
import type { DatabaseOverview, DatabaseQueryExample } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { getUserId } from '../lib/storage'

function QueryResultTable({ example }: { example: DatabaseQueryExample }) {
  const columns = useMemo(() => (
    example.rows.length ? Object.keys(example.rows[0]) : []
  ), [example.rows])

  return (
    <article className="sql-example">
      <div>
        <h3>{example.title}</h3>
        <pre><code>{example.sql}</code></pre>
      </div>
      {example.rows.length ? (
        <div className="sql-result-table" role="table" aria-label={`${example.title} 查詢結果`}>
          <div role="row">
            {columns.map((column) => <strong role="columnheader" key={column}>{column}</strong>)}
          </div>
          {example.rows.map((row, index) => (
            <div role="row" key={`${example.title}-${index}`}>
              {columns.map((column) => <span role="cell" key={column}>{row[column] ?? '—'}</span>)}
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-query-result">目前沒有訓練紀錄資料；完成一次 Workout 後，這裡會出現 Aggregate 統計結果。</p>
      )}
    </article>
  )
}

export default function DatabaseSystemPage() {
  const userId = getUserId()
  const [overview, setOverview] = useState<DatabaseOverview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const suffix = userId ? `?user_id=${userId}` : ''
    apiRequest<DatabaseOverview>(`/database/overview${suffix}`)
      .then(setOverview)
      .catch((reason: Error) => setError(reason.message))
  }, [userId])

  if (!overview && !error) return <LoadingScreen label="正在載入 Database System" />
  if (!overview) return <main className="page"><ErrorNotice message={error} /></main>

  const totalRows = overview.tables.reduce((total, table) => total + table.row_count, 0)
  const junctionTableNames = new Set(['user_body_parts', 'plan_exercises', 'session_plan_days'])
  const primaryTables = overview.tables.filter((table) => !junctionTableNames.has(table.table_name))
  const junctionTables = overview.tables.filter((table) => junctionTableNames.has(table.table_name))

  return (
    <main className="page database-page">
      <header className="page-heading">
        <div>
          <h1>Database System</h1>
          <p>展示資料表、Primary Key、Foreign Key、Relationships、Normalization 與 SQL 查詢結果。</p>
        </div>
      </header>

      <section className="database-hero">
        <div>
          <span><Database size={20} />Cloud PostgreSQL</span>
          <strong>{overview.tables.length}</strong>
          <small>資料表</small>
        </div>
        <div>
          <span><Table2 size={20} />Live Data</span>
          <strong>{totalRows}</strong>
          <small>目前總筆數</small>
        </div>
        <div>
          <span><Network size={20} />Relationships</span>
          <strong>{overview.relationships.length}</strong>
          <small>Foreign Keys</small>
        </div>
        <div>
          <span><KeyRound size={20} />3NF</span>
          <strong>1NF→3NF</strong>
          <small>正規化設計</small>
        </div>
      </section>

      <section className="database-section">
        <div className="section-heading">
          <h2>ER Relationship Map</h2>
          <p>核心 entity 與 junction table 關係。</p>
        </div>
        <div className="er-map" aria-label="ER relationship map">
          {primaryTables.map((table) => <span key={table.table_name}>{table.table_name}</span>)}
          {junctionTables.map((table) => <span className="is-junction" key={table.table_name}>{table.table_name}</span>)}
        </div>
        <div className="relationship-list">
          {overview.relationships.map((relationship) => (
            <div key={`${relationship.from_table}-${relationship.from_column}`}>
              <strong>{relationship.from_table}.{relationship.from_column}</strong>
              <span>→ {relationship.to_table}.{relationship.to_column}</span>
              <small>{relationship.relationship_type}・ON DELETE {relationship.on_delete ?? 'NO ACTION'}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="database-section">
        <div className="section-heading">
          <h2>Database Tables</h2>
          <p>每張表的 row count、欄位、PK/FK 都直接由後端目前資料庫讀取。</p>
        </div>
        <div className="schema-grid">
          {overview.tables.map((table) => (
            <article className="schema-card" key={table.table_name}>
              <header>
                <h3>{table.table_name}</h3>
                <span>{table.row_count} rows</span>
              </header>
              <div className="column-list">
                {table.columns.map((column) => (
                  <div key={`${table.table_name}-${column.column_name}`}>
                    <strong>{column.column_name}</strong>
                    <span>{column.data_type}</span>
                    <small>
                      {column.is_primary_key ? 'PK ' : ''}
                      {column.foreign_key ? `FK → ${column.foreign_key}` : ''}
                      {!column.is_nullable ? ' NOT NULL' : ''}
                    </small>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="database-section">
        <div className="section-heading">
          <h2>SQL Query Demonstration</h2>
          <p>包含 JOIN、GROUP BY 與 Aggregate Functions，結果會跟資料庫同步更新。</p>
        </div>
        <div className="sql-examples">
          {overview.query_examples.map((example) => (
            <QueryResultTable example={example} key={example.title} />
          ))}
        </div>
      </section>

      <section className="database-section">
        <div className="section-heading">
          <h2>3NF Normalization</h2>
          <p>避免重複資料與 update anomaly。</p>
        </div>
        <div className="normalization-list">
          {overview.normalization_notes.map((note) => <p key={note}>{note}</p>)}
        </div>
      </section>
    </main>
  )
}
