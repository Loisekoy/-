import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const outputDir = fileURLToPath(new URL('../docs/diagrams/', import.meta.url));

const esc = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

function startSvg(width, height, title, subtitle) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
  <title id="title">${esc(title)}</title>
  <desc id="desc">${esc(subtitle)}</desc>
  <defs>
    <style>
      text { font-family: "SF Pro Text", "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif; fill: #263442; }
      .page-title { font-size: 34px; font-weight: 700; letter-spacing: 0.4px; }
      .page-subtitle { font-size: 17px; fill: #64748b; }
      .entity-title { font-size: 22px; font-weight: 700; fill: #ffffff; letter-spacing: 0.6px; }
      .entity-subtitle { font-size: 14px; fill: #e2e8f0; }
      .field { font-size: 17px; }
      .field-muted { font-size: 16px; fill: #5c6b78; }
      .key { font-family: Menlo, Consolas, monospace; font-size: 14px; font-weight: 700; }
      .relation { fill: none; stroke: #526477; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; marker-end: url(#arrow); }
      .relation-label { font-size: 15px; font-weight: 700; fill: #334155; }
      .cardinality { font-family: Menlo, Consolas, monospace; font-size: 13px; font-weight: 700; fill: #475569; }
      .legend { font-size: 15px; fill: #5c6b78; }
      .callout-title { font-size: 17px; font-weight: 700; fill: #334155; }
      .callout-text { font-size: 15px; fill: #526477; }
    </style>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="7" flood-color="#1e293b" flood-opacity="0.10"/>
    </filter>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#526477"/>
    </marker>
  </defs>
  <rect width="${width}" height="${height}" fill="#f8fafc"/>
  <rect x="0" y="0" width="${width}" height="10" fill="#334155"/>
  <text x="80" y="68" class="page-title">${esc(title)}</text>
  <text x="80" y="102" class="page-subtitle">${esc(subtitle)}</text>
  <line x1="80" y1="125" x2="${width - 80}" y2="125" stroke="#cbd5e1" stroke-width="1.5"/>
`;
}

function endSvg(width, height, note = '關聯編號與 SRS 第 4.3 節一致') {
  return `
  <line x1="80" y1="${height - 58}" x2="${width - 80}" y2="${height - 58}" stroke="#cbd5e1" stroke-width="1.2"/>
  <text x="80" y="${height - 24}" class="legend">PK：Primary Key　 FK：Foreign Key　 UQ：Unique　 ?：可為 NULL　 箭頭方向：父表 → 子表</text>
  <text x="${width - 80}" y="${height - 24}" text-anchor="end" class="legend">${esc(note)}</text>
</svg>
`;
}

const tones = {
  core: { header: '#2f4358', border: '#5e7388', borderWidth: 2.2 },
  primary: { header: '#3f566c', border: '#8c9baa', borderWidth: 1.6 },
  junction: { header: '#465d72', border: '#899aaa', borderWidth: 1.8 },
  lookup: { header: '#53677b', border: '#9dacbb', borderWidth: 1.5 },
  event: { header: '#697887', border: '#9aa7b4', borderWidth: 1.5 },
};

function card({ x, y, w, h, title, subtitle, fields, tone = 'primary', dashed = false }) {
  const palette = tones[tone];
  const headerHeight = 88;
  const fieldTop = y + headerHeight + 46;
  const available = h - headerHeight - 62;
  const gap = fields.length > 1 ? Math.min(39, available / (fields.length - 1)) : 0;
  const rows = fields.map((field, index) => {
    const fy = fieldTop + index * gap;
    const key = field.key
      ? `<text x="${x + 30}" y="${fy}" class="key" fill="${field.key.includes('FK') ? '#64748b' : field.key === 'UQ' ? '#7c5c42' : '#334155'}">${esc(field.key)}</text>`
      : '';
    const textX = x + (field.key ? 105 : 30);
    return `${key}<text x="${textX}" y="${fy}" class="${field.muted ? 'field-muted' : 'field'}">${esc(field.text)}</text>`;
  }).join('\n    ');

  return `
  <g filter="url(#shadow)">
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="16" fill="#ffffff" stroke="${palette.border}" stroke-width="${palette.borderWidth}"${dashed ? ' stroke-dasharray="8 6"' : ''}/>
    <path d="M${x + 16} ${y} H${x + w - 16} Q${x + w} ${y} ${x + w} ${y + 16} V${y + headerHeight - 18} H${x} V${y + 16} Q${x} ${y} ${x + 16} ${y} Z" fill="${palette.header}"/>
    <text x="${x + 30}" y="${y + 36}" class="entity-title">${esc(title)}</text>
    <text x="${x + 30}" y="${y + 62}" class="entity-subtitle">${esc(subtitle)}</text>
    <line x1="${x + 20}" y1="${y + headerHeight + 1}" x2="${x + w - 20}" y2="${y + headerHeight + 1}" stroke="#e2e8f0"/>
    ${rows}
  </g>`;
}

function relation({ points, id, labelX, labelY, fromCard, toCard }) {
  const d = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point[0]} ${point[1]}`).join(' ');
  return `
  <path class="relation" d="${d}"/>
  <g>
    <rect x="${labelX - 30}" y="${labelY - 16}" width="60" height="31" rx="15.5" fill="#ffffff" stroke="#aab7c4"/>
    <text x="${labelX}" y="${labelY + 6}" text-anchor="middle" class="relation-label">${esc(id)}</text>
  </g>
  <text x="${fromCard.x}" y="${fromCard.y}" class="cardinality">${esc(fromCard.text)}</text>
  <text x="${toCard.x}" y="${toCard.y}" class="cardinality">${esc(toCard.text)}</text>`;
}

function callout(x, y, w, title, lines) {
  return `
  <g>
    <rect x="${x}" y="${y}" width="${w}" height="${56 + lines.length * 28}" rx="12" fill="#eef2f6" stroke="#cbd5e1"/>
    <text x="${x + 24}" y="${y + 34}" class="callout-title">${esc(title)}</text>
    ${lines.map((line, index) => `<text x="${x + 24}" y="${y + 68 + index * 28}" class="callout-text">${esc(line)}</text>`).join('\n    ')}
  </g>`;
}

function save(name, content) {
  writeFileSync(join(outputDir, name), content, 'utf8');
}

function accountsDiagram() {
  const width = 2100;
  const height = 1480;
  let svg = startSvg(width, height, '帳號、使用者偏好與登入保護 ERD', 'R01–R07｜Fitness Tracking Management System｜Schema v1.1');
  const rels = [
    relation({ points: [[500, 280], [760, 520]], id: 'R04', labelX: 620, labelY: 392, fromCard: { x: 510, y: 268, text: '1' }, toCard: { x: 720, y: 505, text: '0..N' } }),
    relation({ points: [[1220, 520], [1470, 280]], id: 'R01', labelX: 1340, labelY: 392, fromCard: { x: 1230, y: 505, text: '1' }, toCard: { x: 1430, y: 268, text: '1' } }),
    relation({ points: [[1680, 430], [1680, 500]], id: 'R02', labelX: 1740, labelY: 465, fromCard: { x: 1698, y: 424, text: '1' }, toCard: { x: 1698, y: 514, text: '0..N' } }),
    relation({ points: [[1220, 710], [1470, 900]], id: 'R03', labelX: 1350, labelY: 802, fromCard: { x: 1230, y: 727, text: '1' }, toCard: { x: 1425, y: 888, text: '0..1' } }),
    relation({ points: [[760, 710], [500, 1010]], id: 'R05', labelX: 625, labelY: 850, fromCard: { x: 720, y: 728, text: '1' }, toCard: { x: 506, y: 997, text: '0..N' } }),
    relation({ points: [[300, 790], [300, 910]], id: 'R06', labelX: 355, labelY: 850, fromCard: { x: 318, y: 805, text: '1' }, toCard: { x: 318, y: 900, text: '0..N' } }),
    relation({ points: [[990, 810], [990, 1020]], id: 'R07', labelX: 1045, labelY: 915, fromCard: { x: 1008, y: 828, text: '1' }, toCard: { x: 1008, y: 1010, text: '0..N' } }),
  ].join('\n');
  svg += rels;
  svg += card({ x: 100, y: 160, w: 400, h: 240, title: 'TRAINING_GOALS', subtitle: '訓練目標主檔', tone: 'lookup', fields: [
    { key: 'PK', text: 'training_goal_id' }, { key: 'UQ', text: 'goal_name' }, { text: 'description?', muted: true },
  ] });
  svg += card({ x: 100, y: 550, w: 400, h: 240, title: 'BODY_PARTS', subtitle: '身體部位主檔', tone: 'lookup', fields: [
    { key: 'PK', text: 'body_part_id' }, { key: 'UQ', text: 'body_part_name' }, { text: 'description?', muted: true },
  ] });
  svg += card({ x: 100, y: 910, w: 400, h: 280, title: 'USER_BODY_PARTS', subtitle: '使用者 × 身體部位關聯表', tone: 'junction', fields: [
    { key: 'PK/FK', text: 'user_id' }, { key: 'PK/FK', text: 'body_part_id' }, { text: 'priority' }, { key: 'UQ', text: '(user_id, priority)', muted: true },
  ] });
  svg += card({ x: 760, y: 430, w: 460, h: 380, title: 'USERS', subtitle: '核心使用者與訓練設定', tone: 'core', fields: [
    { key: 'PK', text: 'user_id' }, { key: 'FK', text: 'training_goal_id?' }, { text: 'name · gender? · age?' },
    { text: 'height_cm? · training_experience?' }, { text: 'training_days_per_week?' },
    { text: 'training_duration_minutes?' }, { text: 'profile_completed_at? · created_at', muted: true },
  ] });
  svg += card({ x: 1470, y: 140, w: 420, h: 290, title: 'USER_AUTH', subtitle: '登入憑證與帳號狀態', fields: [
    { key: 'PK', text: 'auth_id' }, { key: 'FK/UQ', text: 'user_id' }, { key: 'UQ', text: 'email' },
    { text: 'password_hash' }, { text: 'is_email_verified · is_active', muted: true }, { text: 'created_at', muted: true },
  ] });
  svg += card({ x: 1470, y: 500, w: 420, h: 260, title: 'USER_SESSIONS', subtitle: 'JWT jti 白名單與撤銷紀錄', fields: [
    { key: 'PK', text: 'user_session_id (UUID)' }, { key: 'FK', text: 'auth_id' },
    { text: 'created_at · expires_at' }, { text: 'revoked_at?', muted: true },
  ] });
  svg += card({ x: 1470, y: 830, w: 420, h: 210, title: 'ADMINS', subtitle: '管理員資格（以資料庫為準）', fields: [
    { key: 'PK/FK', text: 'user_id' }, { text: 'created_at', muted: true },
  ] });
  svg += card({ x: 760, y: 1020, w: 460, h: 280, title: 'BODY_RECORDS', subtitle: '每日體重歷史', tone: 'junction', fields: [
    { key: 'PK', text: 'body_record_id' }, { key: 'FK', text: 'user_id' }, { text: 'record_date · weight_kg' },
    { text: 'notes?', muted: true }, { key: 'UQ', text: '(user_id, record_date)', muted: true },
  ] });
  svg += card({ x: 1470, y: 1110, w: 420, h: 250, title: 'LOGIN_FAILURES', subtitle: '跨 PHP Worker 的登入限流事件', tone: 'event', dashed: true, fields: [
    { key: 'PK', text: 'login_failure_id' }, { text: 'ip_hash · failed_at' }, { text: '獨立事件表：無外鍵（No FK）', muted: true },
  ] });
  svg += endSvg(width, height, 'R01–R07 與 SRS／DDL 一致；LOGIN_FAILURES 無外鍵');
  save('erd_accounts_v1_2.svg', svg);
}

function exercisesDiagram() {
  const width = 2100;
  const height = 1080;
  let svg = startSvg(width, height, '動作身份與不可變版本 ERD', 'R08–R09｜穩定動作身份與歷史版本分離');
  svg += relation({ points: [[560, 430], [770, 430]], id: 'R08', labelX: 665, labelY: 430, fromCard: { x: 570, y: 415, text: '1' }, toCard: { x: 720, y: 415, text: '0..N' } });
  svg += relation({ points: [[1250, 430], [1460, 430]], id: 'R09', labelX: 1355, labelY: 430, fromCard: { x: 1260, y: 415, text: '1' }, toCard: { x: 1410, y: 415, text: '0..N' } });
  svg += card({ x: 100, y: 250, w: 460, h: 360, title: 'BODY_PARTS', subtitle: '身體部位主檔', tone: 'lookup', fields: [
    { key: 'PK', text: 'body_part_id' }, { key: 'UQ', text: 'body_part_name' }, { text: 'description?', muted: true },
  ] });
  svg += card({ x: 770, y: 230, w: 480, h: 400, title: 'EXERCISES', subtitle: '穩定動作身份', tone: 'core', fields: [
    { key: 'PK', text: 'exercise_id' }, { key: 'FK', text: 'body_part_id' },
    { text: 'is_active' }, { text: 'created_at', muted: true },
  ] });
  svg += card({ x: 1460, y: 170, w: 540, h: 520, title: 'EXERCISE_VERSIONS', subtitle: '不可變名稱、難度、說明與圖片版本', tone: 'junction', fields: [
    { key: 'PK', text: 'exercise_version_id' }, { key: 'FK', text: 'exercise_id' }, { text: 'version_no' },
    { text: 'exercise_name · difficulty_level' }, { text: 'equipment? · description' }, { text: 'image_url?' },
    { text: 'created_at', muted: true }, { key: 'UQ', text: '(exercise_id, version_no)', muted: true },
  ] });
  svg += callout(570, 760, 960, '歷史完整性設計', [
    'EXERCISES 只代表不變的動作身份；名稱、難度、器材、說明與圖片放在版本表。',
    '修改動作時新增 EXERCISE_VERSIONS；已被課表或場次引用的舊版本禁止 UPDATE／DELETE。',
  ]);
  svg += endSvg(width, height, 'R08–R09；版本表保留三年前的動作顯示內容');
  save('erd_exercises_v1_2.svg', svg);
}

function plansDiagram() {
  const width = 2100;
  const height = 1500;
  let svg = startSvg(width, height, '課表、規劃輸入快照與動作處方 ERD', 'R10–R18｜課表來源、規劃快照與每日動作');
  svg += relation({ points: [[430, 360], [540, 360]], id: 'R10', labelX: 485, labelY: 360, fromCard: { x: 440, y: 345, text: '1' }, toCard: { x: 500, y: 345, text: '0..N' } });
  svg += relation({ points: [[1000, 350], [1130, 350]], id: 'R12', labelX: 1065, labelY: 350, fromCard: { x: 1010, y: 335, text: '1' }, toCard: { x: 1095, y: 335, text: '1' } });
  svg += relation({ points: [[770, 220], [770, 170], [940, 170], [940, 220]], id: 'R11', labelX: 855, labelY: 170, fromCard: { x: 735, y: 208, text: '0..1' }, toCard: { x: 948, y: 208, text: '0..N' } });
  svg += relation({ points: [[1320, 750], [1320, 650]], id: 'R13', labelX: 1380, labelY: 700, fromCard: { x: 1338, y: 766, text: '1' }, toCard: { x: 1338, y: 642, text: '0..N' } });
  svg += relation({ points: [[1580, 650], [1580, 1070]], id: 'R14', labelX: 1640, labelY: 860, fromCard: { x: 1598, y: 668, text: '1' }, toCard: { x: 1598, y: 1060, text: '0..N' } });
  svg += relation({ points: [[1770, 865], [1680, 865], [1680, 1195], [1650, 1195]], id: 'R15', labelX: 1715, labelY: 1025, fromCard: { x: 1780, y: 850, text: '1' }, toCard: { x: 1658, y: 1180, text: '0..N' } });
  svg += relation({ points: [[770, 550], [770, 720]], id: 'R16', labelX: 825, labelY: 635, fromCard: { x: 788, y: 568, text: '1' }, toCard: { x: 788, y: 710, text: '0..N' } });
  svg += relation({ points: [[770, 980], [770, 1080]], id: 'R17', labelX: 825, labelY: 1030, fromCard: { x: 788, y: 997, text: '1' }, toCard: { x: 788, y: 1070, text: '0..N' } });
  svg += relation({ points: [[440, 1235], [540, 1235]], id: 'R18', labelX: 490, labelY: 1235, fromCard: { x: 450, y: 1220, text: '1' }, toCard: { x: 500, y: 1220, text: '0..N' } });
  svg += card({ x: 70, y: 250, w: 360, h: 220, title: 'USERS', subtitle: '課表擁有者', tone: 'lookup', fields: [{ key: 'PK', text: 'user_id' }] });
  svg += card({ x: 540, y: 220, w: 460, h: 330, title: 'WORKOUT_PLANS', subtitle: '可封存、可複製的課表主檔', tone: 'core', fields: [
    { key: 'PK', text: 'workout_plan_id' }, { key: 'FK', text: 'user_id' }, { key: 'FK', text: 'copied_from_plan_id?' },
    { text: 'plan_name · published_at' }, { text: 'archived_at? · created_at', muted: true },
  ] });
  svg += card({ x: 1130, y: 170, w: 520, h: 480, title: 'PLANNING_PROFILES', subtitle: '產生課表當下的使用者輸入快照', tone: 'junction', fields: [
    { key: 'PK/FK', text: 'workout_plan_id' }, { key: 'FK', text: 'training_goal_id' },
    { text: 'age_snapshot · height_cm_snapshot' }, { text: 'weight_kg_snapshot · weight_record_date' },
    { text: 'experience_snapshot' }, { text: 'training_days_per_week · duration_minutes' },
    { text: 'algorithm_version · captured_at', muted: true },
  ] });
  svg += card({ x: 1130, y: 750, w: 380, h: 220, title: 'TRAINING_GOALS', subtitle: '規劃時目標來源', tone: 'lookup', fields: [{ key: 'PK', text: 'training_goal_id' }, { key: 'UQ', text: 'goal_name' }] });
  svg += card({ x: 1720, y: 750, w: 320, h: 230, title: 'BODY_PARTS', subtitle: '規劃偏好部位來源', tone: 'lookup', fields: [{ key: 'PK', text: 'body_part_id' }, { key: 'UQ', text: 'body_part_name' }] });
  svg += card({ x: 1130, y: 1070, w: 520, h: 280, title: 'PLANNING_PROFILE_BODY_PARTS', subtitle: '課表產生當下的重點部位快照', tone: 'junction', fields: [
    { key: 'PK/FK', text: 'workout_plan_id' }, { key: 'PK/FK', text: 'body_part_id' },
    { text: 'priority' }, { key: 'UQ', text: '(workout_plan_id, priority)', muted: true },
  ] });
  svg += card({ x: 540, y: 720, w: 460, h: 260, title: 'PLAN_DAYS', subtitle: '課表中的訓練日', fields: [
    { key: 'PK', text: 'plan_day_id' }, { key: 'FK', text: 'workout_plan_id' },
    { text: 'day_number · day_title' }, { key: 'UQ', text: '(workout_plan_id, day_number)', muted: true },
  ] });
  svg += card({ x: 540, y: 1080, w: 460, h: 330, title: 'PLAN_EXERCISES', subtitle: '每日動作與目標處方', tone: 'junction', fields: [
    { key: 'PK', text: 'plan_exercise_id' }, { key: 'FK', text: 'plan_day_id' }, { key: 'FK', text: 'exercise_version_id' },
    { text: 'exercise_order · target_sets · target_reps' }, { text: 'rest_seconds · target_weight_kg?' },
    { key: 'UQ', text: '(plan_day_id, exercise_order)', muted: true },
  ] });
  svg += card({ x: 70, y: 1100, w: 370, h: 270, title: 'EXERCISE_VERSIONS', subtitle: '課表引用固定動作版本', tone: 'lookup', fields: [
    { key: 'PK', text: 'exercise_version_id' }, { key: 'FK', text: 'exercise_id' }, { text: 'version_no · exercise_name' },
  ] });
  svg += endSvg(width, height, 'R10–R18；規劃快照與課表動作均保留產生當下資訊');
  save('erd_plans_v1_2.svg', svg);
}

function workoutsDiagram() {
  const width = 2100;
  const height = 1500;
  let svg = startSvg(width, height, '運動場次、來源快照與實際組數 ERD', 'R19–R25｜開始運動、場次快照、逐組寫入與歷史保留');
  svg += relation({ points: [[430, 340], [600, 340]], id: 'R19', labelX: 515, labelY: 340, fromCard: { x: 440, y: 325, text: '1' }, toCard: { x: 560, y: 325, text: '0..N' } });
  svg += relation({ points: [[1080, 340], [1240, 340]], id: 'R20', labelX: 1160, labelY: 340, fromCard: { x: 1090, y: 325, text: '1' }, toCard: { x: 1200, y: 325, text: '1' } });
  svg += relation({ points: [[1920, 340], [1700, 340]], id: 'R21', labelX: 1810, labelY: 340, fromCard: { x: 1880, y: 325, text: '1' }, toCard: { x: 1710, y: 325, text: '0..N' } });
  svg += relation({ points: [[840, 540], [840, 700]], id: 'R22', labelX: 895, labelY: 620, fromCard: { x: 858, y: 558, text: '1' }, toCard: { x: 858, y: 690, text: '1..N' } });
  svg += relation({ points: [[460, 900], [690, 900]], id: 'R23', labelX: 575, labelY: 900, fromCard: { x: 470, y: 885, text: '1' }, toCard: { x: 650, y: 885, text: '0..N' } });
  svg += relation({ points: [[1680, 900], [1190, 900]], id: 'R24', labelX: 1435, labelY: 900, fromCard: { x: 1640, y: 885, text: '1' }, toCard: { x: 1200, y: 885, text: '0..N' } });
  svg += relation({ points: [[940, 1080], [940, 1180]], id: 'R25', labelX: 995, labelY: 1130, fromCard: { x: 958, y: 1098, text: '1' }, toCard: { x: 958, y: 1170, text: '0..N' } });
  svg += card({ x: 70, y: 240, w: 360, h: 220, title: 'USERS', subtitle: '訓練場次擁有者', tone: 'lookup', fields: [{ key: 'PK', text: 'user_id' }] });
  svg += card({ x: 600, y: 190, w: 480, h: 350, title: 'WORKOUT_SESSIONS', subtitle: '一次實際訓練的生命週期', tone: 'core', fields: [
    { key: 'PK', text: 'workout_session_id' }, { key: 'FK', text: 'user_id' },
    { text: 'status · started_at · ended_at?' }, { text: 'notes?', muted: true },
    { key: 'UQ', text: '每位使用者僅一筆 in_progress', muted: true },
  ] });
  svg += card({ x: 1240, y: 220, w: 460, h: 260, title: 'WORKOUT_SESSION_PLANS', subtitle: '場次來源課表日', tone: 'junction', fields: [
    { key: 'PK/FK', text: 'workout_session_id' }, { key: 'FK', text: 'plan_day_id' },
  ] });
  svg += card({ x: 1780, y: 240, w: 300, h: 220, title: 'PLAN_DAYS', subtitle: '來源課表日', tone: 'lookup', fields: [{ key: 'PK', text: 'plan_day_id' }] });
  svg += card({ x: 70, y: 780, w: 390, h: 250, title: 'PLAN_EXERCISES', subtitle: '來源課表動作', tone: 'lookup', fields: [
    { key: 'PK', text: 'plan_exercise_id' }, { key: 'FK', text: 'exercise_version_id' },
  ] });
  svg += card({ x: 690, y: 700, w: 500, h: 380, title: 'WORKOUT_SESSION_EXERCISES', subtitle: '開始運動時建立的場次動作快照', tone: 'junction', fields: [
    { key: 'PK', text: 'workout_session_exercise_id' }, { key: 'FK', text: 'workout_session_id' },
    { key: 'FK', text: 'plan_exercise_id' }, { key: 'FK', text: 'exercise_version_id' },
    { text: 'exercise_order · target_sets · target_reps' }, { text: 'rest_seconds · target_weight_kg?' },
    { text: 'created_at', muted: true },
  ] });
  svg += card({ x: 1680, y: 780, w: 400, h: 250, title: 'EXERCISE_VERSIONS', subtitle: '場次固定引用的動作版本', tone: 'lookup', fields: [
    { key: 'PK', text: 'exercise_version_id' }, { key: 'FK', text: 'exercise_id' },
  ] });
  svg += card({ x: 690, y: 1180, w: 500, h: 250, title: 'WORKOUT_SETS', subtitle: '每完成一組立即寫入', tone: 'core', fields: [
    { key: 'PK', text: 'workout_set_id' }, { key: 'FK', text: 'workout_session_exercise_id' },
    { text: 'set_number · weight_kg · reps' }, { key: 'UQ', text: '(session_exercise_id, set_number)', muted: true },
  ] });
  svg += callout(1320, 1160, 700, '歷史不受後續修改影響', [
    '場次引用固定 exercise_version_id，並保存當場目標處方。',
    '完成場次至少一組；來源課表刪改不會改寫既有歷史。',
  ]);
  svg += endSvg(width, height, 'R19–R25；場次快照與逐組紀錄形成完整歷史鏈');
  save('erd_workouts_v1_2.svg', svg);
}

accountsDiagram();
exercisesDiagram();
plansDiagram();
workoutsDiagram();

console.log('Generated ERD v1.2 SVG files in', outputDir);
