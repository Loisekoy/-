const state = {
    token: window.__FITTRACK_QA_TOKEN__ || null,
    me: null,
    reference: null,
    route: '',
    plans: [],
    selectedPlanId: null,
    selectedDayIndex: 0,
    exerciseFilters: { q: '', body_part_id: '', difficulty_level: '' },
    adminTab: 'users',
    adminSelectedTable: 'users',
    planEditing: false,
    activeWorkoutExerciseIndex: 0,
};

let restTimerId = null;
let restTimerRemaining = 0;

const main = document.querySelector('#main-content');
const header = document.querySelector('#site-header');
const toastRegion = document.querySelector('#toast-region');

const escapeHtml = (value = '') => String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

const formatNumber = (value, digits = 0) => new Intl.NumberFormat('zh-TW', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
}).format(Number(value || 0));

const formatDate = (value) => {
    if (!value) return '-';
    const normalized = String(value).includes('T') ? value : `${value}T00:00:00`;
    return new Intl.DateTimeFormat('zh-TW', { dateStyle: 'medium' }).format(new Date(normalized));
};

const formatDateTime = (value) => {
    if (!value) return '-';
    return new Intl.DateTimeFormat('zh-TW', {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(new Date(value));
};

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    toast.textContent = message;
    toastRegion.append(toast);
    window.setTimeout(() => toast.remove(), 3600);
}

async function api(path, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }
    const response = await fetch(`/api${path}`, { ...options, headers });
    let data = null;
    if (response.status !== 204) {
        data = await response.json().catch(() => ({
            code: 'INVALID_RESPONSE',
            message: '伺服器回應格式不正確。',
        }));
    }
    if (!response.ok) {
        if (response.status === 401 && state.token) {
            clearSession();
            renderHeader();
            navigate('login');
        }
        throw new Error(data?.message || '要求失敗，請稍後再試。');
    }
    return data;
}

function setSession(result) {
    state.token = result.access_token;
}

function clearSession() {
    state.token = null;
    state.me = null;
    state.reference = null;
    state.plans = [];
}

function navigate(route) {
    const next = `#${route}`;
    if (location.hash === next) {
        renderRoute();
        return;
    }
    location.hash = next;
}

function currentRoute() {
    return location.hash.replace(/^#/, '') || (state.token ? 'dashboard' : 'home');
}

function renderHeader() {
    const route = currentRoute();
    if (!state.token) {
        header.innerHTML = `
            <div class="header-inner">
                <button class="brand button-quiet" data-action="navigate" data-route="home" aria-label="回到首頁">
                    <span class="brand-mark">F</span>
                    <span class="brand-copy"><strong>FitTrack Pro</strong><small>Fitness Tracking Management System</small></span>
                </button>
                <div class="header-actions">
                    <button class="button button-quiet" data-action="navigate" data-route="login">登入</button>
                    <button class="button button-primary" data-action="navigate" data-route="register">免費註冊</button>
                </div>
            </div>`;
        return;
    }

    const items = [
        ['plans', '▦', '我的課表'],
        ['workout', '▶', '開始訓練'],
        ['history', '◷', '歷史紀錄'],
        ['dashboard', '▥', 'Dashboard'],
        ['exercises', '⌕', '動作庫'],
        ['profile', '○', '編輯資料'],
    ];
    header.innerHTML = `
        <div class="header-inner">
            <button class="brand button-quiet" data-action="navigate" data-route="dashboard" aria-label="回到 Dashboard">
                <span class="brand-mark">F</span>
                <span class="brand-copy"><strong>FitTrack Pro</strong><small>Build a stronger you.</small></span>
            </button>
            <nav class="main-nav" aria-label="主要導覽">
                ${items.map(([itemRoute, icon, label]) => `
                    <button class="nav-link ${route === itemRoute ? 'is-active' : ''}" data-action="navigate" data-route="${itemRoute}">
                        <span aria-hidden="true">${icon}</span><span>${label}</span>
                    </button>`).join('')}
            </nav>
            <div class="header-actions">
                ${state.me?.is_admin ? '<button class="button button-small" data-action="navigate" data-route="admin">管理</button>' : ''}
                <span class="user-chip">${escapeHtml(state.me?.name || '')}</span>
                <button class="icon-button" data-action="logout" title="登出" aria-label="登出">×</button>
            </div>
        </div>`;
}

function loading() {
    main.innerHTML = `
        <div class="loading-screen">
            <span class="loading-mark" aria-hidden="true"></span>
            <p>正在讀取資料...</p>
        </div>`;
}

function renderLanding() {
    main.innerHTML = `
        <section class="hero">
            <img class="hero-media" src="/assets/hero-fitness-v2.png" alt="健身者進行槓鈴深蹲訓練">
            <div class="hero-content">
                <div class="hero-copy">
                    <h1>Train.<br>Track.<br><span>Progress.</span></h1>
                    <p>從個人目標產生課表，訓練時逐組存檔，再用實際資料看見自己的進步。</p>
                    <div class="hero-actions">
                        <button class="button button-primary" data-action="navigate" data-route="register">建立我的訓練計畫</button>
                        <button class="button" data-action="navigate" data-route="login">已有帳號，直接登入</button>
                    </div>
                </div>
            </div>
            <div class="hero-proof" aria-label="系統特色">
                <div class="hero-proof-item"><strong>15 TABLES</strong><span>正規化 PostgreSQL 資料模型</span></div>
                <div class="hero-proof-item"><strong>SET BY SET</strong><span>每完成一組立即寫入資料庫</span></div>
                <div class="hero-proof-item"><strong>RULES V1</strong><span>可重現的規則式課表產生</span></div>
            </div>
        </section>`;
}

function renderAuth(mode) {
    const register = mode === 'register';
    main.innerHTML = `
        <section class="auth-layout">
            <div class="auth-panel">
                <div class="auth-form-wrap">
                    <h1 class="page-title zh">${register ? '建立帳號' : '歡迎回來'}</h1>
                    <p class="page-subtitle">${register ? '開始建立屬於你的課表與訓練紀錄。' : '登入後繼續今天的訓練。'}</p>
                    <form id="auth-form" class="form-grid" style="margin-top:32px" data-mode="${mode}">
                        ${register ? `
                            <div class="field">
                                <label for="auth-name">姓名</label>
                                <input id="auth-name" name="name" autocomplete="name" maxlength="100" required>
                            </div>` : ''}
                        <div class="field">
                            <label for="auth-email">Email</label>
                            <input id="auth-email" name="email" type="email" autocomplete="email" maxlength="255" required value="${register ? '' : 'demo@fittrack.local'}">
                        </div>
                        <div class="field">
                            <label for="auth-password">密碼</label>
                            <input id="auth-password" name="password" type="password" autocomplete="${register ? 'new-password' : 'current-password'}" minlength="10" maxlength="72" required value="${register ? '' : 'Demo12345'}">
                        </div>
                        <button class="button button-primary" type="submit">${register ? '註冊並開始設定' : '登入系統'}</button>
                    </form>
                    <p class="auth-switch">
                        ${register ? '已經有帳號？' : '還沒有帳號？'}
                        <button class="text-link" data-action="navigate" data-route="${register ? 'login' : 'register'}">${register ? '登入' : '免費註冊'}</button>
                    </p>
                    <div class="demo-note">
                        示範會員：demo@fittrack.local / Demo12345<br>
                        管理員：admin@fittrack.local / Admin12345
                    </div>
                </div>
            </div>
            <div class="auth-visual">
                <img src="/assets/hero-fitness-v2.png" alt="健身者進行槓鈴深蹲訓練">
                <div class="auth-visual-copy">
                    <strong>Your data.<br>Your progress.</strong>
                    <span>Database-first fitness tracking</span>
                </div>
            </div>
        </section>`;
}

function statsStrip(items) {
    return `<div class="stats-strip">${items.map((item) => `
        <div class="stat">
            <span class="stat-label">${escapeHtml(item.label)}</span>
            <span class="stat-value">${escapeHtml(item.value)}<span class="stat-unit">${escapeHtml(item.unit || '')}</span></span>
        </div>`).join('')}</div>`;
}

async function renderDashboard() {
    loading();
    const data = await api('/dashboard');
    const volumes = data.volume_by_week || [];
    const maxVolume = Math.max(1, ...volumes.map((item) => Number(item.volume)));
    const weights = data.weight_history || [];
    const weightValues = weights.map((item) => Number(item.weight));
    const minWeight = Math.min(...(weightValues.length ? weightValues : [0]));
    const maxWeight = Math.max(...(weightValues.length ? weightValues : [1]));
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header">
                <div><h1 class="page-title">Dashboard</h1><p class="page-subtitle">掌握訓練進度，持續成為更好的自己。</p></div>
                <button class="button" data-action="navigate" data-route="workout">▶ 開始訓練</button>
            </div>
            ${statsStrip([
                { label: '完成訓練', value: formatNumber(data.session_count), unit: '次' },
                { label: '完成工作組', value: formatNumber(data.set_count), unit: '組' },
                { label: 'Training Volume', value: formatNumber(data.total_volume), unit: 'kg' },
                { label: '最新體重', value: data.latest_weight ? formatNumber(data.latest_weight, 1) : '--', unit: 'kg' },
            ])}
            <div class="dashboard-grid">
                <section class="data-section">
                    <h2 class="section-heading">Training Volume</h2>
                    <p class="section-copy">完成訓練的每週總量</p>
                    ${volumes.length ? `
                        <div class="chart" aria-label="每週訓練量長條圖">
                            ${volumes.map((item) => `
                                <div class="chart-column" title="${escapeHtml(item.week)}：${formatNumber(item.volume)} kg">
                                    <div class="chart-bar" style="height:${Math.max(4, Number(item.volume) / maxVolume * 220)}px"></div>
                                    <span class="chart-label">${escapeHtml(item.week)}</span>
                                </div>`).join('')}
                        </div>` : '<div class="empty-state">完成第一次訓練後，這裡會出現每週訓練量。</div>'}
                </section>
                <section class="data-section">
                    <h2 class="section-heading">Body Weight History</h2>
                    <p class="section-copy">最近體重紀錄</p>
                    ${weights.length ? `
                        <div class="weight-chart">
                            ${weights.slice(-8).map((item) => {
                                const width = maxWeight === minWeight ? 68 : 25 + ((Number(item.weight) - minWeight) / (maxWeight - minWeight)) * 70;
                                return `<div class="weight-row"><span>${formatDate(item.date)}</span><div class="weight-track"><span style="width:${width}%"></span></div><strong>${formatNumber(item.weight, 1)} kg</strong></div>`;
                            }).join('')}
                        </div>` : '<div class="empty-state">在編輯資料頁新增體重後，就能觀察變化。</div>'}
                </section>
            </div>
            <div class="lower-grid">
                <div class="highlight-metric"><span class="stat-label">最常訓練部位</span><strong>${escapeHtml(data.favorite_body_part || '尚無資料')}</strong></div>
                <div class="highlight-metric"><span class="stat-label">最常使用 Exercise</span><strong>${escapeHtml(data.favorite_exercise || '尚無資料')}</strong></div>
                <div class="recent-list">
                    <h2 class="section-heading zh">最近訓練紀錄</h2>
                    ${historyTable(data.recent_workouts || [], true)}
                </div>
            </div>
        </div>`;
}

function historyTable(items, compact = false) {
    if (!items.length) return '<div class="empty-state">目前沒有已完成的訓練紀錄。</div>';
    return `<table class="data-table responsive">
        <thead><tr><th>日期</th><th>課表</th><th>狀態</th><th>工作組</th><th>總量</th>${compact ? '' : '<th>操作</th>'}</tr></thead>
        <tbody>${items.map((item) => `
            <tr>
                <td data-label="日期">${formatDateTime(item.started_at)}</td>
                <td data-label="課表"><span class="exercise-name">${escapeHtml(item.day_title || item.plan_name || '自由訓練')}</span></td>
                <td data-label="狀態"><span class="status status-${escapeHtml(item.status)}">${item.status === 'completed' ? '已完成' : '已取消'}</span></td>
                <td data-label="工作組">${formatNumber(item.set_count)} 組</td>
                <td data-label="總量">${formatNumber(item.total_volume)} kg</td>
                ${compact ? '' : `<td data-label="操作"><button class="button button-small button-danger" data-action="delete-workout" data-session-id="${item.workout_session_id}">刪除</button></td>`}
            </tr>`).join('')}</tbody>
    </table>`;
}

async function renderPlans() {
    loading();
    const [result, exerciseResult] = await Promise.all([api('/plans'), api('/exercises')]);
    state.plans = result.items || [];
    if (!state.selectedPlanId && state.plans.length) {
        state.selectedPlanId = Number(state.plans[0].workout_plan_id);
    }
    const selected = state.plans.find((plan) => Number(plan.workout_plan_id) === Number(state.selectedPlanId)) || state.plans[0];
    const day = selected?.days?.[state.selectedDayIndex] || selected?.days?.[0];
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header">
                <div><h1 class="page-title zh">我的訓練課表</h1><p class="page-subtitle">依照目標、程度、偏好部位與可用時間產生課表。</p></div>
                <form id="generate-plan-form" class="plan-create-form">
                    <input name="plan_name" maxlength="120" placeholder="新課表名稱（可留白）" aria-label="新課表名稱">
                    <button class="button button-primary" type="submit">新增規劃</button>
                </form>
            </div>
            ${state.plans.length > 1 ? `
                <div class="toolbar" style="grid-template-columns:minmax(240px,420px)">
                    <select id="plan-select" aria-label="選擇課表">
                        ${state.plans.map((plan) => `<option value="${plan.workout_plan_id}" ${Number(plan.workout_plan_id) === Number(selected?.workout_plan_id) ? 'selected' : ''}>${escapeHtml(plan.plan_name)} - ${formatDate(plan.created_at)}</option>`).join('')}
                    </select>
                </div>` : ''}
            ${selected ? `
                <div class="plan-layout">
                    <aside class="day-list" aria-label="課表訓練日">
                        ${selected.days.map((item, index) => `
                            <button class="day-tab ${index === state.selectedDayIndex ? 'is-active' : ''}" data-action="select-day" data-index="${index}">
                                <strong>Day ${item.day_number}</strong>
                                <span>${escapeHtml(item.day_title.replace(/^第 \d+ 天：/, ''))}</span>
                            </button>`).join('')}
                    </aside>
                    <section class="plan-detail">
                        <div class="plan-title-row">
                            ${state.planEditing
                                ? `<input id="plan-name-editor" class="plan-name-editor" maxlength="120" value="${escapeHtml(selected.plan_name)}" aria-label="課表名稱">`
                                : `<h2 class="section-heading zh">${escapeHtml(selected.plan_name)}</h2>`}
                            <div class="form-actions" style="margin-top:0">
                                ${state.planEditing
                                    ? `<button class="button" data-action="cancel-plan-edit">取消</button><button class="button button-primary" data-action="save-plan" data-plan-id="${selected.workout_plan_id}">儲存課表</button>`
                                    : `<button class="button" data-action="edit-plan">編輯課表</button><button class="button button-danger" data-action="delete-plan" data-plan-id="${selected.workout_plan_id}">刪除</button>`}
                            </div>
                        </div>
                        <div class="plan-meta">
                            <span>${escapeHtml(selected.experience_snapshot)}</span>
                            <span>${escapeHtml(selected.goal_name)}</span>
                            <span>${escapeHtml(selected.duration_minutes)} 分鐘</span>
                            <span>${selected.days.length} 天計畫</span>
                        </div>
                        ${day ? `
                            <div class="plan-day-header">
                                <div><h3 class="section-heading zh">${escapeHtml(day.day_title)}</h3><p class="section-copy">依序完成下列動作，重量請依當天狀態調整。</p></div>
                                <button class="button button-primary" data-action="start-workout" data-day-id="${day.plan_day_id}">▶ 開始 Day ${day.day_number} 訓練</button>
                            </div>
                            <div class="plan-table-scroll"><table class="data-table responsive plan-exercise-table">
                                <thead><tr><th>#</th><th>示意圖</th><th>動作名稱</th><th>主要部位</th><th>器材</th><th>目標</th><th>休息</th></tr></thead>
                                <tbody>${day.exercises.map((exercise) => `
                                    <tr class="plan-exercise-editor" data-plan-exercise-id="${exercise.plan_exercise_id}">
                                        <td data-label="#">${exercise.exercise_order}</td>
                                        <td data-label="示意圖"><div class="plan-exercise-media">${exercise.image_url ? `<img src="${escapeHtml(exercise.image_url)}" alt="${escapeHtml(exercise.exercise_name)} 動作示範" loading="lazy">` : '<span>FIT</span>'}</div></td>
                                        <td data-label="動作名稱">${state.planEditing
                                            ? `<select class="plan-exercise-select" aria-label="第 ${exercise.exercise_order} 個動作">${(exerciseResult.items || []).map((option) => `<option value="${option.exercise_id}" ${Number(option.exercise_id) === Number(exercise.exercise_id) ? 'selected' : ''}>${escapeHtml(option.exercise_name)} · ${escapeHtml(option.body_part_name)}</option>`).join('')}</select>`
                                            : `<span class="exercise-name">${escapeHtml(exercise.exercise_name)}</span>`}</td>
                                        <td data-label="主要部位">${escapeHtml(exercise.body_part_name)}</td>
                                        <td data-label="器材">${escapeHtml(exercise.equipment || 'Bodyweight')}</td>
                                        <td data-label="目標">${state.planEditing
                                            ? `<div class="plan-number-pair"><input class="plan-sets" type="number" min="1" max="10" value="${exercise.target_sets}" aria-label="目標組數"><span>×</span><input class="plan-reps" type="number" min="1" max="50" value="${exercise.target_reps}" aria-label="目標次數"></div>`
                                            : `${exercise.target_sets} × ${exercise.target_reps}`}</td>
                                        <td data-label="休息">${state.planEditing
                                            ? `<div class="plan-rest-input"><input class="plan-rest" type="number" min="0" max="300" step="5" value="${exercise.rest_seconds}" aria-label="休息秒數"><span>秒</span></div>`
                                            : `${exercise.rest_seconds} 秒`}</td>
                                    </tr>`).join('')}</tbody>
                            </table></div>` : ''}
                    </section>
                </div>` : `
                <div class="empty-state">
                    尚未建立課表。先在「編輯資料」完成基本資料、訓練設定與偏好部位，再產生第一份課表。
                </div>`}
        </div>`;
}

async function renderWorkout() {
    loading();
    const session = await api('/workout-sessions/current');
    if (!session) {
        main.innerHTML = `
            <div class="workout-shell">
                <div class="page-header"><div><h1 class="page-title zh">開始訓練</h1><p class="page-subtitle">目前沒有進行中的訓練。</p></div></div>
                <div class="empty-state">請先到「我的課表」選擇今天要做的訓練日。</div>
                <div class="form-actions"><button class="button button-primary" data-action="navigate" data-route="plans">前往我的課表</button></div>
            </div>`;
        return;
    }
    renderWorkoutSession(session);
}

function renderWorkoutSession(session) {
    const savedKeys = new Set((session.sets || []).map((set) => `${set.exercise_id}-${set.set_number}`));
    const savedCount = savedKeys.size;
    const targetCount = (session.exercises || []).reduce((sum, exercise) => sum + Number(exercise.target_sets), 0);
    const progress = targetCount ? Math.min(100, savedCount / targetCount * 100) : 0;
    const exercises = session.exercises || [];
    state.activeWorkoutExerciseIndex = Math.max(0, Math.min(state.activeWorkoutExerciseIndex, exercises.length - 1));
    const exercise = exercises[state.activeWorkoutExerciseIndex];
    const exerciseSets = (session.sets || []).filter((set) => Number(set.exercise_id) === Number(exercise?.exercise_id));
    main.innerHTML = `
        <div class="workout-shell">
            <div class="workout-topline">
                <div>
                    <h1 class="page-title zh">${escapeHtml(session.day_title || '進行中訓練')}</h1>
                    <p class="page-subtitle">${escapeHtml(session.plan_name || '')} · 開始於 ${formatDateTime(session.started_at)}</p>
                </div>
                <button class="icon-button" data-action="navigate" data-route="dashboard" title="離開訓練頁" aria-label="離開訓練頁">×</button>
            </div>
            <div class="workout-progress"><span>${savedCount} / ${targetCount} 組</span><div class="progress-track"><span style="width:${progress}%"></span></div><span>${Math.round(progress)}%</span></div>
            <div class="workout-stepper" aria-label="訓練動作進度">
                ${exercises.map((item, index) => {
                    const complete = (session.sets || []).filter((set) => Number(set.exercise_id) === Number(item.exercise_id)).length >= Number(item.target_sets);
                    return `<button class="workout-step ${index === state.activeWorkoutExerciseIndex ? 'is-active' : ''} ${complete ? 'is-complete' : ''}" data-action="select-workout-exercise" data-index="${index}"><span>${index + 1}</span>${escapeHtml(item.exercise_name)}</button>`;
                }).join('')}
            </div>
            ${exercise ? `
                    <section class="workout-exercise is-focused">
                        <div class="workout-media">
                            ${exercise.image_url ? `<img src="${escapeHtml(exercise.image_url)}" alt="${escapeHtml(exercise.exercise_name)} 動作示範">` : '<div class="exercise-placeholder">FIT</div>'}
                        </div>
                        <div>
                            <span class="stat-label">${escapeHtml(exercise.body_part_name)} · ${escapeHtml(exercise.equipment || 'Bodyweight')}</span>
                            <h2>${escapeHtml(exercise.exercise_name)}</h2>
                            <p class="page-subtitle">目標 ${exercise.target_sets} × ${exercise.target_reps} · 休息 ${exercise.rest_seconds} 秒</p>
                            <details style="margin-top:14px"><summary class="text-link">查看動作步驟</summary><p class="exercise-description" style="display:block;min-height:0;-webkit-line-clamp:initial">${escapeHtml(exercise.description)}</p></details>
                            <div class="set-table">
                                <div class="set-row set-row-head"><span>Set</span><span>Weight (kg)</span><span>Reps</span><span>狀態</span></div>
                                ${Array.from({ length: Number(exercise.target_sets) }, (_, index) => {
                                    const setNumber = index + 1;
                                    const saved = exerciseSets.find((set) => Number(set.set_number) === setNumber);
                                    return `<div class="set-row">
                                        <strong>${setNumber}</strong>
                                        <input class="set-input" id="weight-${exercise.exercise_id}-${setNumber}" type="number" inputmode="decimal" min="0" max="999.99" step="0.5" value="${saved ? escapeHtml(saved.weight_kg) : '0'}" aria-label="第 ${setNumber} 組重量">
                                        <input class="set-input" id="reps-${exercise.exercise_id}-${setNumber}" type="number" inputmode="numeric" min="1" max="999" value="${saved ? escapeHtml(saved.reps) : exercise.target_reps}" aria-label="第 ${setNumber} 組次數">
                                        ${saved
                                            ? `<div class="set-actions"><button class="icon-button compact" data-action="update-set" data-set-id="${saved.workout_set_id}" data-exercise-id="${exercise.exercise_id}" data-set-number="${setNumber}" title="更新此組" aria-label="更新此組">↻</button><button class="icon-button compact danger" data-action="delete-set" data-set-id="${saved.workout_set_id}" title="刪除此組" aria-label="刪除此組">×</button></div>`
                                            : `<button class="button button-small" data-action="save-set" data-session-id="${session.workout_session_id}" data-exercise-id="${exercise.exercise_id}" data-set-number="${setNumber}" data-rest-seconds="${exercise.rest_seconds}">儲存此組</button>`}
                                    </div>`;
                                }).join('')}
                            </div>
                        </div>
                    </section>
                    <div class="workout-navigation">
                        <button class="button" data-action="select-workout-exercise" data-index="${state.activeWorkoutExerciseIndex - 1}" ${state.activeWorkoutExerciseIndex === 0 ? 'disabled' : ''}>← 上一個</button>
                        <span>動作 ${state.activeWorkoutExerciseIndex + 1} / ${exercises.length}</span>
                        <button class="button" data-action="select-workout-exercise" data-index="${state.activeWorkoutExerciseIndex + 1}" ${state.activeWorkoutExerciseIndex === exercises.length - 1 ? 'disabled' : ''}>下一個 →</button>
                    </div>` : '<div class="empty-state">這個訓練日沒有可用動作。</div>'}
            <aside class="rest-timer" id="rest-timer" aria-live="polite">
                <div><span class="stat-label">REST TIMER</span><strong id="rest-countdown">${restTimerRemaining > 0 ? `${Math.floor(restTimerRemaining / 60)}:${String(restTimerRemaining % 60).padStart(2, '0')}` : '等待完成一組'}</strong></div>
                <button class="button button-small" data-action="stop-rest-timer" ${restTimerRemaining <= 0 ? 'disabled' : ''}>略過休息</button>
            </aside>
            <div class="field workout-notes"><label for="workout-notes">本次訓練備註</label><textarea id="workout-notes" maxlength="1000" placeholder="記錄今天的狀態、疼痛或重量調整">${escapeHtml(session.notes || '')}</textarea></div>
            <div class="workout-actions">
                <button class="button button-danger" data-action="finish-workout" data-status="cancel" data-session-id="${session.workout_session_id}">取消本次訓練</button>
                <button class="button button-primary" data-action="finish-workout" data-status="complete" data-session-id="${session.workout_session_id}" ${savedCount === 0 ? 'disabled' : ''}>完成訓練</button>
            </div>
        </div>`;
}

function startRestTimer(seconds) {
    window.clearInterval(restTimerId);
    restTimerRemaining = Math.max(0, Number(seconds));
    updateRestTimerDisplay();
    if (restTimerRemaining <= 0) return;
    restTimerId = window.setInterval(() => {
        restTimerRemaining -= 1;
        updateRestTimerDisplay();
        if (restTimerRemaining <= 0) {
            window.clearInterval(restTimerId);
            restTimerId = null;
            showToast('休息完成，可以開始下一組。');
        }
    }, 1000);
}

function updateRestTimerDisplay() {
    const display = document.querySelector('#rest-countdown');
    if (display) {
        display.textContent = restTimerRemaining > 0
            ? `${Math.floor(restTimerRemaining / 60)}:${String(restTimerRemaining % 60).padStart(2, '0')}`
            : '休息完成';
    }
    const stop = document.querySelector('[data-action="stop-rest-timer"]');
    if (stop) stop.disabled = restTimerRemaining <= 0;
}

async function renderExercises() {
    loading();
    const params = new URLSearchParams(Object.entries(state.exerciseFilters).filter(([, value]) => value));
    const result = await api(`/exercises?${params.toString()}`);
    const items = result.items || [];
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">動作資料庫</h1><p class="page-subtitle">搜尋動作、器材、難度與中文步驟，GIF 來自你提供的本機資料集。</p></div><span class="stat-label">${items.length} 個動作</span></div>
            <form id="exercise-filter-form" class="toolbar">
                <input name="q" type="search" placeholder="搜尋動作或器材" value="${escapeHtml(state.exerciseFilters.q)}">
                <select name="body_part_id"><option value="">全部部位</option>${state.reference.body_parts.map((part) => `<option value="${part.body_part_id}" ${String(part.body_part_id) === String(state.exerciseFilters.body_part_id) ? 'selected' : ''}>${escapeHtml(part.body_part_name)}</option>`).join('')}</select>
                <select name="difficulty_level"><option value="">全部難度</option>${['Beginner', 'Intermediate', 'Advanced'].map((level) => `<option ${level === state.exerciseFilters.difficulty_level ? 'selected' : ''}>${level}</option>`).join('')}</select>
            </form>
            ${items.length ? `<div class="exercise-grid">${items.map((exercise) => `
                <article class="exercise-card">
                    <div class="exercise-card-media">${exercise.image_url ? `<img src="${escapeHtml(exercise.image_url)}" alt="${escapeHtml(exercise.exercise_name)} 動作示範" loading="lazy">` : '<span class="exercise-placeholder">FIT</span>'}</div>
                    <div class="exercise-card-body">
                        <h3>${escapeHtml(exercise.exercise_name)}</h3>
                        <div class="exercise-meta"><span>${escapeHtml(exercise.body_part_name)}</span><span>${escapeHtml(exercise.difficulty_level)}</span><span>${escapeHtml(exercise.equipment || 'Bodyweight')}</span></div>
                        <p class="exercise-description">${escapeHtml(exercise.description)}</p>
                    </div>
                </article>`).join('')}</div>` : '<div class="empty-state">沒有符合條件的動作。</div>'}
        </div>`;
}

async function renderHistory() {
    loading();
    const result = await api('/workout-sessions');
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">訓練歷史</h1><p class="page-subtitle">已完成與已取消的訓練都會保留，Dashboard 只統計已完成項目。</p></div></div>
            <section class="data-section" style="margin-top:32px">${historyTable(result.items || [])}</section>
        </div>`;
}

async function renderProfile() {
    loading();
    state.me = await api('/me');
    renderHeader();
    const selectedPartIds = new Set((state.me.preferred_body_parts || []).map((part) => Number(part.body_part_id)));
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">編輯資料</h1><p class="page-subtitle">這些設定會決定規則式課表的天數、動作候選與組次。</p></div></div>
            ${state.me.profile_complete ? '' : '<div class="info-band">請完成以下三個區塊，才能產生你的第一份課表。</div>'}
            <div class="profile-grid">
                <section class="settings-section">
                    <h2 class="section-heading zh">基本資料</h2>
                    <form id="profile-form" class="form-grid two-columns" style="margin-top:20px">
                        <div class="field"><label for="profile-name">姓名</label><input id="profile-name" name="name" value="${escapeHtml(state.me.name)}" required></div>
                        <div class="field"><label for="profile-gender">性別</label><select id="profile-gender" name="gender"><option value="">未提供</option>${['Female', 'Male', 'Other'].map((value) => `<option ${state.me.gender === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div>
                        <div class="field"><label for="profile-age">年齡</label><input id="profile-age" name="age" type="number" min="13" max="100" value="${escapeHtml(state.me.age || '')}" required></div>
                        <div class="field"><label for="profile-height">身高 cm</label><input id="profile-height" name="height_cm" type="number" min="100" max="250" step="0.1" value="${escapeHtml(state.me.height_cm || '')}" required></div>
                        <div class="field"><label for="profile-experience">訓練程度</label><select id="profile-experience" name="training_experience" required><option value="">請選擇</option>${['Beginner', 'Intermediate', 'Advanced'].map((value) => `<option ${state.me.training_experience === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div>
                        <div class="field"><label for="profile-weight">目前體重 kg</label><input id="profile-weight" name="weight_kg" type="number" min="20" max="500" step="0.1" value="${escapeHtml(state.me.current_weight_kg || '')}" required></div>
                        <div class="form-actions" style="grid-column:1/-1"><button class="button button-primary" type="submit">儲存基本資料</button></div>
                    </form>
                </section>
                <section class="settings-section">
                    <h2 class="section-heading zh">訓練設定</h2>
                    <form id="training-settings-form" class="form-grid" style="margin-top:20px">
                        <div class="field"><label for="goal">訓練目標</label><select id="goal" name="training_goal_id" required><option value="">請選擇</option>${state.reference.training_goals.map((goal) => `<option value="${goal.training_goal_id}" ${Number(goal.training_goal_id) === Number(state.me.training_goal_id) ? 'selected' : ''}>${escapeHtml(goal.goal_name)}</option>`).join('')}</select></div>
                        <div class="field"><label for="days">每週訓練天數</label><select id="days" name="training_days_per_week" required>${[2, 3, 4, 5, 6].map((value) => `<option value="${value}" ${Number(state.me.training_days_per_week) === value ? 'selected' : ''}>${value} 天</option>`).join('')}</select></div>
                        <div class="field"><label for="duration">每次訓練時間</label><select id="duration" name="training_duration_minutes" required>${[30, 60, 90].map((value) => `<option value="${value}" ${Number(state.me.training_duration_minutes) === value ? 'selected' : ''}>${value} 分鐘</option>`).join('')}</select></div>
                        <div class="form-actions"><button class="button button-primary" type="submit">儲存訓練設定</button></div>
                    </form>
                </section>
                <section class="settings-section full">
                    <h2 class="section-heading zh">想加強的部位</h2>
                    <p class="section-copy">選取順序會作為排課優先順序。</p>
                    <form id="body-parts-form">
                        <div class="choice-grid">
                            ${state.reference.body_parts.map((part) => `<label class="choice"><input type="checkbox" name="body_part_ids" value="${part.body_part_id}" ${selectedPartIds.has(Number(part.body_part_id)) ? 'checked' : ''}><span>${escapeHtml(part.body_part_name)}</span></label>`).join('')}
                        </div>
                        <div class="form-actions"><button class="button button-primary" type="submit">儲存偏好部位</button></div>
                    </form>
                </section>
                <section class="settings-section full">
                    <h2 class="section-heading zh">體重紀錄</h2>
                    <form id="body-record-form" class="form-grid two-columns" style="margin-top:20px;max-width:680px">
                        <div class="field"><label for="record-date">日期</label><input id="record-date" name="record_date" type="date" max="${new Date().toISOString().slice(0, 10)}" required></div>
                        <div class="field"><label for="record-weight">體重 kg</label><input id="record-weight" name="weight_kg" type="number" min="20" max="500" step="0.1" required></div>
                        <div class="field" style="grid-column:1/-1"><label for="record-notes">備註</label><input id="record-notes" name="notes" maxlength="1000"></div>
                        <div class="form-actions" style="grid-column:1/-1"><button class="button" type="submit">新增體重紀錄</button></div>
                    </form>
                    <div id="body-record-list"></div>
                </section>
                <section class="settings-section full">
                    <h2 class="section-heading zh">帳號安全</h2>
                    <div class="profile-grid" style="margin-top:20px">
                        <form id="password-form" class="form-grid">
                            <div class="field"><label for="current-password">目前密碼</label><input id="current-password" name="current_password" type="password" autocomplete="current-password" required></div>
                            <div class="field"><label for="new-password">新密碼</label><input id="new-password" name="new_password" type="password" minlength="10" maxlength="72" autocomplete="new-password" required></div>
                            <div class="form-actions"><button class="button" type="submit">變更密碼並登出</button></div>
                        </form>
                        <form id="deactivate-form" class="form-grid">
                            <div class="field"><label for="deactivate-password">輸入目前密碼確認停用</label><input id="deactivate-password" name="current_password" type="password" autocomplete="current-password" required></div>
                            <div class="form-actions"><button class="button button-danger" type="submit">停用自己的帳號</button></div>
                        </form>
                    </div>
                </section>
            </div>
        </div>`;
    renderBodyRecordList();
}

async function renderBodyRecordList() {
    const container = document.querySelector('#body-record-list');
    if (!container) return;
    const result = await api('/body-records');
    const items = result.items || [];
    container.innerHTML = items.length ? `
        <table class="data-table responsive">
            <thead><tr><th>日期</th><th>體重</th><th>備註</th><th>操作</th></tr></thead>
            <tbody>${items.map((item) => `<tr><td data-label="日期">${formatDate(item.record_date)}</td><td data-label="體重">${formatNumber(item.weight_kg, 1)} kg</td><td data-label="備註">${escapeHtml(item.notes || '-')}</td><td data-label="操作"><div class="form-actions" style="margin-top:0"><button class="button button-small" data-action="edit-body-record" data-record-id="${item.body_record_id}" data-date="${escapeHtml(item.record_date)}" data-weight="${escapeHtml(item.weight_kg)}" data-notes="${escapeHtml(item.notes || '')}">編輯</button><button class="button button-small button-danger" data-action="delete-body-record" data-record-id="${item.body_record_id}">刪除</button></div></td></tr>`).join('')}</tbody>
        </table>` : '<div class="empty-state">尚無體重紀錄。</div>';
}

async function renderAdmin() {
    if (!state.me?.is_admin) {
        navigate('dashboard');
        return;
    }
    loading();
    const [stats, users, exercises, databaseOverview] = await Promise.all([
        api('/admin/statistics'),
        api('/admin/users'),
        api('/admin/exercises'),
        state.adminTab === 'database' ? api('/admin/database/overview') : Promise.resolve(null),
    ]);
    let databaseTable = null;
    if (databaseOverview) {
        if (!databaseOverview.tables.some((table) => table.table_name === state.adminSelectedTable)) {
            state.adminSelectedTable = databaseOverview.tables[0]?.table_name || 'users';
        }
        databaseTable = await api(`/admin/database/tables/${state.adminSelectedTable}`);
    }
    const content = state.adminTab === 'database'
        ? renderDatabaseSystem(databaseOverview, databaseTable)
        : state.adminTab === 'exercises'
        ? `<form id="admin-exercise-form" class="form-grid two-columns" style="margin-top:24px;padding-bottom:24px;border-bottom:1px solid var(--line)">
                <div class="field"><label>動作名稱</label><input name="exercise_name" required maxlength="120"></div>
                <div class="field"><label>主要部位</label><select name="body_part_id" required>${state.reference.body_parts.map((part) => `<option value="${part.body_part_id}">${escapeHtml(part.body_part_name)}</option>`).join('')}</select></div>
                <div class="field"><label>難度</label><select name="difficulty_level">${['Beginner', 'Intermediate', 'Advanced'].map((level) => `<option>${level}</option>`).join('')}</select></div>
                <div class="field"><label>器材</label><input name="equipment" maxlength="100"></div>
                <div class="field" style="grid-column:1/-1"><label>動作說明</label><textarea name="description" required maxlength="4000"></textarea></div>
                <div class="field" style="grid-column:1/-1"><label>圖片或 GIF 路徑</label><input name="image_url" maxlength="2048" placeholder="/media/exercises/example.gif"></div>
                <div class="form-actions" style="grid-column:1/-1"><button class="button button-primary" type="submit">新增動作</button></div>
            </form>
            <table class="data-table responsive"><thead><tr><th>ID</th><th>動作</th><th>部位</th><th>難度</th><th>器材</th><th>狀態</th><th>操作</th></tr></thead><tbody>${exercises.items.map((item) => `<tr><td data-label="ID">${item.exercise_id}</td><td data-label="動作">${escapeHtml(item.exercise_name)}</td><td data-label="部位">${escapeHtml(item.body_part_name)}</td><td data-label="難度">${escapeHtml(item.difficulty_level)}</td><td data-label="器材">${escapeHtml(item.equipment || '-')}</td><td data-label="狀態"><span class="status status-${Number(item.is_active) ? 'active' : 'inactive'}">${Number(item.is_active) ? '啟用' : '停用'}</span></td><td data-label="操作"><div class="form-actions" style="margin-top:0"><button class="button button-small" data-action="toggle-exercise" data-exercise-id="${item.exercise_id}" data-active="${Number(item.is_active) ? 0 : 1}">${Number(item.is_active) ? '停用' : '啟用'}</button><button class="button button-small button-danger" data-action="delete-exercise" data-exercise-id="${item.exercise_id}">刪除</button></div></td></tr>`).join('')}</tbody></table>`
        : `<table class="data-table responsive"><thead><tr><th>ID</th><th>姓名</th><th>Email</th><th>身份</th><th>帳號狀態</th><th>建立時間</th></tr></thead><tbody>${users.items.map((item) => `<tr><td data-label="ID">${item.user_id}</td><td data-label="姓名">${escapeHtml(item.name)}</td><td data-label="Email">${escapeHtml(item.email)}</td><td data-label="身份">${Number(item.is_admin) ? 'ADMIN' : 'USER'}</td><td data-label="狀態"><span class="status status-${Number(item.is_active) ? 'active' : 'inactive'}">${Number(item.is_active) ? '啟用' : '停用'}</span></td><td data-label="建立時間">${formatDateTime(item.created_at)}</td></tr>`).join('')}</tbody></table>`;
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">管理後台</h1><p class="page-subtitle">管理會員與動作主資料，並檢視正式資料庫的結構、關聯與即時資料。</p></div></div>
            <div class="admin-grid">
                ${Object.entries({ users: '會員', exercises: '動作', plans: '課表', completed_workouts: '完成訓練', sets: '訓練組數' }).map(([key, label]) => `<div class="admin-stat"><span class="stat-label">${label}</span><strong>${formatNumber(stats[key])}</strong></div>`).join('')}
            </div>
            <div class="tabs"><button class="tab ${state.adminTab === 'users' ? 'is-active' : ''}" data-action="admin-tab" data-tab="users">會員清單</button><button class="tab ${state.adminTab === 'exercises' ? 'is-active' : ''}" data-action="admin-tab" data-tab="exercises">動作管理</button><button class="tab ${state.adminTab === 'database' ? 'is-active' : ''}" data-action="admin-tab" data-tab="database">資料庫系統</button></div>
            ${content}
        </div>`;
}

function renderDatabaseSystem(overview, tableData) {
    const totalRows = overview.tables.reduce((sum, table) => sum + Number(table.row_count), 0);
    const previewColumns = tableData.columns.map((column) => column.column_name);
    return `
        <section class="database-overview" aria-label="資料庫摘要">
            <div><span class="stat-label">DATABASE</span><strong>${escapeHtml(String(overview.driver).toUpperCase())}</strong><small>目前連線</small></div>
            <div><span class="stat-label">TABLES</span><strong>${overview.tables.length}</strong><small>核心資料表</small></div>
            <div><span class="stat-label">ROWS</span><strong>${formatNumber(totalRows)}</strong><small>目前總筆數</small></div>
            <div><span class="stat-label">FOREIGN KEYS</span><strong>${overview.relationships.length}</strong><small>資料關聯</small></div>
        </section>
        <div class="database-workspace">
            <aside class="database-table-list" aria-label="資料表清單">
                <h2 class="section-heading">TABLES</h2>
                ${overview.tables.map((table) => `<button class="database-table-button ${table.table_name === tableData.table_name ? 'is-active' : ''}" data-action="select-database-table" data-table="${table.table_name}"><span>${escapeHtml(table.table_name)}</span><strong>${formatNumber(table.row_count)}</strong></button>`).join('')}
            </aside>
            <div class="database-detail">
                <div class="database-detail-heading"><div><h2>${escapeHtml(tableData.table_name)}</h2><p>${formatNumber(tableData.row_count)} 筆資料 · 唯讀預覽前 ${tableData.limit} 筆</p></div><span class="read-only-badge">READ ONLY</span></div>
                <div class="database-columns">
                    ${tableData.columns.map((column) => `<div><strong>${escapeHtml(column.column_name)}</strong><span>${escapeHtml(column.data_type)}</span><small>${column.is_primary_key ? 'PK ' : ''}${column.foreign_key ? `FK → ${escapeHtml(column.foreign_key)} ` : ''}${column.is_nullable ? 'NULL' : 'NOT NULL'}</small></div>`).join('')}
                </div>
                <div class="database-preview-scroll">
                    ${tableData.rows.length ? `<table class="data-table database-preview"><thead><tr>${previewColumns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${tableData.rows.map((row) => `<tr>${previewColumns.map((column) => `<td>${escapeHtml(formatDatabaseValue(row[column]))}</td>`).join('')}</tr>`).join('')}</tbody></table>` : '<div class="empty-state">這張表目前沒有資料。</div>'}
                </div>
            </div>
        </div>
        <section class="database-section">
            <div><h2 class="section-heading">RELATIONSHIPS</h2><p class="section-copy">Foreign Key 與 1:N、M:N 關係。</p></div>
            <div class="relationship-grid">${overview.relationships.map((relationship) => `<div><strong>${escapeHtml(relationship.from_table)}.${escapeHtml(relationship.from_column)}</strong><span>→ ${escapeHtml(relationship.to_table)}.${escapeHtml(relationship.to_column)}</span><small>${escapeHtml(relationship.relationship_type)} · ON DELETE ${escapeHtml(relationship.on_delete)}</small></div>`).join('')}</div>
        </section>
        <section class="database-section">
            <div><h2 class="section-heading">SQL DEMONSTRATION</h2><p class="section-copy">由後端執行固定的唯讀查詢，結果會隨正式資料更新。</p></div>
            <div class="query-list">${overview.query_examples.map((example) => {
                const columns = example.rows.length ? Object.keys(example.rows[0]) : [];
                return `<article class="query-example"><h3>${escapeHtml(example.title)}</h3><pre><code>${escapeHtml(example.sql)}</code></pre>${example.rows.length ? `<div class="database-preview-scroll"><table class="data-table"><thead><tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${example.rows.map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(formatDatabaseValue(row[column]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p class="section-copy">目前沒有符合條件的資料。</p>'}</article>`;
            }).join('')}</div>
        </section>
        <section class="database-section">
            <div><h2 class="section-heading">3NF NORMALIZATION</h2><p class="section-copy">這套資料表如何避免重複與更新異常。</p></div>
            <div class="normalization-list">${overview.normalization_notes.map((note) => `<p>${escapeHtml(note)}</p>`).join('')}</div>
        </section>`;
}

function formatDatabaseValue(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    const text = String(value);
    return text.length > 100 ? `${text.slice(0, 97)}...` : text;
}

async function ensureSessionData() {
    if (!state.token) return;
    if (state.me && state.reference) return;
    const [me, reference] = await Promise.all([api('/me'), api('/reference')]);
    state.me = me;
    state.reference = reference;
}

async function renderRoute() {
    state.route = currentRoute();
    try {
        if (!state.token) {
            renderHeader();
            if (state.route === 'login' || state.route === 'register') {
                renderAuth(state.route);
            } else {
                renderLanding();
            }
            return;
        }

        await ensureSessionData();
        if (!state.me.profile_complete && !['profile', 'exercises', 'admin'].includes(state.route)) {
            location.hash = '#profile';
            return;
        }
        renderHeader();
        const views = {
            dashboard: renderDashboard,
            plans: renderPlans,
            workout: renderWorkout,
            exercises: renderExercises,
            history: renderHistory,
            profile: renderProfile,
            admin: renderAdmin,
        };
        await (views[state.route] || renderDashboard)();
    } catch (error) {
        main.innerHTML = `<div class="page-shell"><div class="error-banner">${escapeHtml(error.message)}</div><div class="form-actions"><button class="button" data-action="refresh">重新載入</button></div></div>`;
        showToast(error.message, 'error');
    }
}

document.addEventListener('click', async (event) => {
    const control = event.target.closest('[data-action]');
    if (!control) return;
    const action = control.dataset.action;
    try {
        if (action === 'navigate') {
            navigate(control.dataset.route);
        } else if (action === 'refresh') {
            renderRoute();
        } else if (action === 'logout') {
            await api('/auth/logout', { method: 'POST' });
            clearSession();
            renderHeader();
            navigate('home');
            showToast('已安全登出。');
        } else if (action === 'generate-plan') {
            control.disabled = true;
            const plan = await api('/plans/generate', { method: 'POST', body: JSON.stringify({}) });
            state.selectedPlanId = Number(plan.workout_plan_id);
            state.selectedDayIndex = 0;
            showToast('新的訓練課表已建立。');
            await renderPlans();
        } else if (action === 'edit-plan') {
            state.planEditing = true;
            await renderPlans();
        } else if (action === 'cancel-plan-edit') {
            state.planEditing = false;
            await renderPlans();
        } else if (action === 'save-plan') {
            const rows = [...document.querySelectorAll('.plan-exercise-editor')];
            const exercises = rows.map((row) => ({
                plan_exercise_id: Number(row.dataset.planExerciseId),
                exercise_id: Number(row.querySelector('.plan-exercise-select').value),
                target_sets: Number(row.querySelector('.plan-sets').value),
                target_reps: Number(row.querySelector('.plan-reps').value),
                rest_seconds: Number(row.querySelector('.plan-rest').value),
            }));
            if (new Set(exercises.map((item) => item.exercise_id)).size !== exercises.length) {
                throw new Error('同一天不能安排重複動作，請重新選擇。');
            }
            control.disabled = true;
            await api(`/plans/${control.dataset.planId}`, {
                method: 'PATCH',
                body: JSON.stringify({
                    plan_name: document.querySelector('#plan-name-editor').value,
                    exercises,
                }),
            });
            state.planEditing = false;
            showToast('課表名稱、動作與組次已更新。');
            await renderPlans();
        } else if (action === 'select-day') {
            state.selectedDayIndex = Number(control.dataset.index);
            await renderPlans();
        } else if (action === 'delete-plan') {
            if (!window.confirm('確定刪除這份課表？已完成的訓練歷史會保留。')) return;
            await api(`/plans/${control.dataset.planId}`, { method: 'DELETE' });
            state.selectedPlanId = null;
            state.selectedDayIndex = 0;
            showToast('課表已刪除，歷史訓練仍保留。');
            await renderPlans();
        } else if (action === 'start-workout') {
            control.disabled = true;
            await api('/workout-sessions', {
                method: 'POST',
                body: JSON.stringify({ plan_day_id: Number(control.dataset.dayId) }),
            });
            state.activeWorkoutExerciseIndex = 0;
            navigate('workout');
        } else if (action === 'select-workout-exercise') {
            state.activeWorkoutExerciseIndex = Number(control.dataset.index);
            await renderWorkout();
        } else if (action === 'save-set') {
            control.disabled = true;
            control.textContent = '儲存中';
            const exerciseId = Number(control.dataset.exerciseId);
            const setNumber = Number(control.dataset.setNumber);
            const weight = document.querySelector(`#weight-${exerciseId}-${setNumber}`).value;
            const reps = document.querySelector(`#reps-${exerciseId}-${setNumber}`).value;
            await api(`/workout-sessions/${control.dataset.sessionId}/sets`, {
                method: 'POST',
                body: JSON.stringify({ exercise_id: exerciseId, set_number: setNumber, weight_kg: Number(weight), reps: Number(reps) }),
            });
            showToast(`第 ${setNumber} 組已儲存。`);
            await renderWorkout();
            startRestTimer(Number(control.dataset.restSeconds));
        } else if (action === 'update-set') {
            const exerciseId = Number(control.dataset.exerciseId);
            const setNumber = Number(control.dataset.setNumber);
            const weight = document.querySelector(`#weight-${exerciseId}-${setNumber}`).value;
            const reps = document.querySelector(`#reps-${exerciseId}-${setNumber}`).value;
            await api(`/workout-sets/${control.dataset.setId}`, {
                method: 'PATCH',
                body: JSON.stringify({ weight_kg: Number(weight), reps: Number(reps) }),
            });
            showToast(`第 ${setNumber} 組已更新。`);
            await renderWorkout();
        } else if (action === 'delete-set') {
            if (!window.confirm('確定刪除這一組紀錄？')) return;
            await api(`/workout-sets/${control.dataset.setId}`, { method: 'DELETE' });
            showToast('這組訓練紀錄已刪除。');
            await renderWorkout();
        } else if (action === 'stop-rest-timer') {
            window.clearInterval(restTimerId);
            restTimerId = null;
            restTimerRemaining = 0;
            updateRestTimerDisplay();
        } else if (action === 'finish-workout') {
            const finishing = control.dataset.status === 'complete';
            if (!window.confirm(finishing ? '確定完成這次訓練？' : '確定取消這次訓練？')) return;
            await api(`/workout-sessions/${control.dataset.sessionId}/${control.dataset.status}`, {
                method: 'POST',
                body: JSON.stringify({ notes: document.querySelector('#workout-notes')?.value || '' }),
            });
            window.clearInterval(restTimerId);
            restTimerId = null;
            restTimerRemaining = 0;
            showToast(finishing ? '訓練已完成並納入統計。' : '本次訓練已取消。');
            navigate(finishing ? 'dashboard' : 'history');
        } else if (action === 'delete-workout') {
            if (!window.confirm('確定刪除這次訓練與所有組數？')) return;
            await api(`/workout-sessions/${control.dataset.sessionId}`, { method: 'DELETE' });
            showToast('訓練紀錄已刪除。');
            await renderHistory();
        } else if (action === 'edit-body-record') {
            const weight = window.prompt('輸入新的體重（kg）', control.dataset.weight);
            if (weight === null) return;
            const notes = window.prompt('輸入備註', control.dataset.notes || '');
            if (notes === null) return;
            await api(`/body-records/${control.dataset.recordId}`, {
                method: 'PATCH',
                body: JSON.stringify({
                    record_date: control.dataset.date,
                    weight_kg: Number(weight),
                    notes,
                }),
            });
            showToast('體重紀錄已更新。');
            await renderBodyRecordList();
        } else if (action === 'delete-body-record') {
            if (!window.confirm('確定刪除這筆體重紀錄？')) return;
            await api(`/body-records/${control.dataset.recordId}`, { method: 'DELETE' });
            showToast('體重紀錄已刪除。');
            await renderBodyRecordList();
        } else if (action === 'admin-tab') {
            state.adminTab = control.dataset.tab;
            await renderAdmin();
        } else if (action === 'select-database-table') {
            state.adminSelectedTable = control.dataset.table;
            await renderAdmin();
        } else if (action === 'toggle-exercise') {
            await api(`/admin/exercises/${control.dataset.exerciseId}`, {
                method: 'PATCH',
                body: JSON.stringify({ is_active: Number(control.dataset.active) }),
            });
            showToast('動作狀態已更新。');
            await renderAdmin();
        } else if (action === 'delete-exercise') {
            if (!window.confirm('確定刪除這個動作？若已被課表或歷史引用，系統會拒絕刪除。')) return;
            await api(`/admin/exercises/${control.dataset.exerciseId}`, { method: 'DELETE' });
            showToast('動作已刪除。');
            await renderAdmin();
        }
    } catch (error) {
        control.disabled = false;
        showToast(error.message, 'error');
    }
});

document.addEventListener('change', async (event) => {
    if (event.target.matches('#plan-select')) {
        state.selectedPlanId = Number(event.target.value);
        state.selectedDayIndex = 0;
        state.planEditing = false;
        await renderPlans();
    }
});

document.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const submit = form.querySelector('[type="submit"]');
    if (submit) submit.disabled = true;
    try {
        const values = Object.fromEntries(new FormData(form));
        if (form.id === 'auth-form') {
            const result = await api(`/auth/${form.dataset.mode === 'register' ? 'register' : 'login'}`, {
                method: 'POST',
                body: JSON.stringify(values),
            });
            setSession(result);
            state.me = null;
            state.reference = null;
            await ensureSessionData();
            showToast(form.dataset.mode === 'register' ? '帳號建立成功。' : '登入成功。');
            navigate(state.me.profile_complete ? 'dashboard' : 'profile');
        } else if (form.id === 'exercise-filter-form') {
            state.exerciseFilters = values;
            await renderExercises();
        } else if (form.id === 'generate-plan-form') {
            const plan = await api('/plans/generate', {
                method: 'POST',
                body: JSON.stringify({ plan_name: values.plan_name || null }),
            });
            state.selectedPlanId = Number(plan.workout_plan_id);
            state.selectedDayIndex = 0;
            state.planEditing = false;
            showToast('新的訓練規劃已建立。');
            await renderPlans();
        } else if (form.id === 'profile-form') {
            state.me = await api('/me/profile', { method: 'PUT', body: JSON.stringify(values) });
            showToast('基本資料已儲存。');
            await renderProfile();
        } else if (form.id === 'training-settings-form') {
            state.me = await api('/me/training-settings', { method: 'PUT', body: JSON.stringify({
                training_goal_id: Number(values.training_goal_id),
                training_days_per_week: Number(values.training_days_per_week),
                training_duration_minutes: Number(values.training_duration_minutes),
            }) });
            showToast('訓練設定已儲存。');
            await renderProfile();
        } else if (form.id === 'body-parts-form') {
            const ids = [...form.querySelectorAll('input[name="body_part_ids"]:checked')].map((input) => Number(input.value));
            state.me = await api('/me/body-parts', { method: 'PUT', body: JSON.stringify({ body_part_ids: ids }) });
            showToast('偏好部位已儲存。');
            await renderProfile();
        } else if (form.id === 'body-record-form') {
            await api('/body-records', { method: 'POST', body: JSON.stringify(values) });
            form.reset();
            showToast('體重紀錄已新增。');
            await renderBodyRecordList();
        } else if (form.id === 'password-form') {
            await api('/auth/password', { method: 'PATCH', body: JSON.stringify(values) });
            clearSession();
            renderHeader();
            showToast('密碼已更新，請重新登入。');
            navigate('login');
        } else if (form.id === 'deactivate-form') {
            if (!window.confirm('停用後將無法再次登入，確定繼續？')) return;
            await api('/auth/deactivate', { method: 'POST', body: JSON.stringify(values) });
            clearSession();
            renderHeader();
            showToast('帳號已停用。');
            navigate('home');
        } else if (form.id === 'admin-exercise-form') {
            await api('/admin/exercises', {
                method: 'POST',
                body: JSON.stringify({
                    ...values,
                    body_part_id: Number(values.body_part_id),
                    is_active: true,
                }),
            });
            showToast('新動作已加入資料庫。');
            await renderAdmin();
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        if (submit) submit.disabled = false;
    }
});

window.addEventListener('hashchange', renderRoute);
renderRoute();
