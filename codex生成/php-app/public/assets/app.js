const state = {
    authenticated: false,
    me: null,
    reference: null,
    route: '',
    plans: [],
    selectedPlanId: null,
    selectedDayIndex: 0,
    planCreationMode: 'computer',
    exerciseOptions: [],
    manualPlanDraft: null,
    manualPlanDayIndex: 0,
    manualExerciseQuery: '',
    manualBodyPartId: '',
    exerciseFilters: { q: '', body_part_id: '', difficulty_level: '' },
    exercisePage: 1,
    dashboardFilters: { start_date: '', end_date: '' },
    historyFilters: { start_date: '', end_date: '', status: '', exercise_id: '' },
    historyDetailId: null,
    adminTab: 'users',
    adminSelectedTable: 'users',
    adminEditingExerciseId: null,
    planEditing: false,
    activeWorkoutExerciseIndex: 0,
};

let restTimerId = null;
let restTimerRemaining = 0;
let restTimerState = 'idle';
let workoutTimerId = null;
let activeWorkoutSessionId = null;

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

const normalizeDateValue = (value) => {
    const text = String(value || '').trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return `${text}T00:00:00`;
    return text.replace(' ', 'T');
};

const formatDate = (value) => {
    if (!value) return '-';
    return new Intl.DateTimeFormat('zh-TW', { dateStyle: 'medium' }).format(new Date(normalizeDateValue(value)));
};

const formatDateTime = (value) => {
    if (!value) return '-';
    return new Intl.DateTimeFormat('zh-TW', {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(new Date(normalizeDateValue(value)));
};

const formatElapsedDuration = (seconds) => {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainingSeconds = total % 60;
    return [hours, minutes, remainingSeconds].map((part) => String(part).padStart(2, '0')).join(':');
};

const exerciseImage = (url, name, lazy = false) => url
    ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(name)} 動作示範" ${lazy ? 'loading="lazy"' : ''} data-exercise-image><span class="exercise-image-fallback" hidden>非此動作示範</span>`
    : '<span class="exercise-image-fallback">非此動作示範</span>';

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
    const method = String(options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const csrf = document.cookie.split('; ').find((item) => item.startsWith('fittrack_csrf=') || item.startsWith('__Host-fittrack_csrf='));
        if (csrf) headers['X-CSRF-Token'] = decodeURIComponent(csrf.split('=').slice(1).join('='));
    }
    const response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin' });
    let data = null;
    if (response.status !== 204) {
        data = await response.json().catch(() => ({
            code: 'INVALID_RESPONSE',
            message: '伺服器回應格式不正確。',
        }));
    }
    if (!response.ok) {
        if (response.status === 401 && state.authenticated) {
            clearSession();
            renderHeader();
            navigate('login');
        }
        throw new Error(data?.message || '要求失敗，請稍後再試。');
    }
    return data;
}

function setSession(result) {
    state.authenticated = true;
}

function clearSession() {
    state.authenticated = false;
    state.me = null;
    state.reference = null;
    state.plans = [];
    resetWorkoutTimers();
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
    return location.hash.replace(/^#/, '') || (state.authenticated ? 'dashboard' : 'home');
}

function renderHeader() {
    const route = currentRoute();
    if (!state.authenticated) {
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
                <div class="hero-proof-item"><strong>20 TABLES</strong><span>正規化 PostgreSQL 資料模型</span></div>
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
                            <input id="auth-password" name="password" type="password" autocomplete="${register ? 'new-password' : 'current-password'}" ${register ? 'minlength="10"' : ''} maxlength="72" required value="${register ? '' : 'Demo12345'}">
                        </div>
                        <button class="button button-primary" type="submit">${register ? '註冊並開始設定' : '登入系統'}</button>
                    </form>
                    <p class="auth-switch">
                        ${register ? '已經有帳號？' : '還沒有帳號？'}
                        <button class="text-link" data-action="navigate" data-route="${register ? 'login' : 'register'}">${register ? '登入' : '免費註冊'}</button>
                    </p>
                    <div class="demo-note">
                        示範會員：demo@fittrack.local / Demo12345<br>
                        課堂展示管理員：admin@fittrack.local / Admin12345<br>
                        你也可以免費註冊自己的帳號
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
    const params = new URLSearchParams(Object.entries(state.dashboardFilters).filter(([, value]) => value));
    const data = await api(`/dashboard?${params.toString()}`);
    state.dashboardFilters = { start_date: data.start_date, end_date: data.end_date };
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
            <form id="dashboard-filter-form" class="toolbar" aria-label="Dashboard 日期篩選">
                <label>開始日期 <input name="start_date" type="date" min="1900-01-01" value="${escapeHtml(data.start_date)}" required></label>
                <label>結束日期 <input name="end_date" type="date" min="1900-01-01" value="${escapeHtml(data.end_date)}" required></label>
                <button class="button button-small" type="submit">套用日期</button>
            </form>
            ${statsStrip([
                { label: '完成訓練', value: formatNumber(data.session_count), unit: '次' },
                { label: '完成工作組', value: formatNumber(data.set_count), unit: '組' },
                { label: '外加重量訓練量', value: formatNumber(data.external_load_volume_kg_reps), unit: 'kg·次' },
                { label: '徒手總次數', value: formatNumber(data.bodyweight_reps), unit: '次' },
                { label: '最新體重', value: data.latest_weight ? formatNumber(data.latest_weight, 1) : '--', unit: 'kg' },
            ])}
            <div class="dashboard-grid">
                <section class="data-section">
                    <h2 class="section-heading">外加重量訓練量</h2>
                    <p class="section-copy">Σ（外加重量 × 完成次數），純徒手組另以完成次數呈現</p>
                    ${volumes.length ? `
                        <div class="chart" aria-label="每週訓練量長條圖">
                            ${volumes.map((item) => `
                                <div class="chart-column" title="${escapeHtml(item.week)}：${formatNumber(item.volume)} kg·次／${formatNumber(item.session_count)} 次訓練">
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
                <td data-label="總量">${formatNumber(item.total_volume)} kg·次</td>
                ${compact ? '' : `<td data-label="操作"><div class="form-actions" style="margin-top:0"><button class="button button-small" data-action="view-workout" data-session-id="${item.workout_session_id}">查看</button><button class="button button-small button-danger" data-action="delete-workout" data-session-id="${item.workout_session_id}">刪除</button></div></td>`}
            </tr>`).join('')}</tbody>
    </table>`;
}

function manualPrescription() {
    return {
        Strength: [4, 5, 120],
        'Fat Loss': [3, 12, 45],
        'General Fitness': [2, 12, 45],
    }[state.me?.goal_name] || [3, 10, 60];
}

function ensureManualPlanDraft() {
    if (state.manualPlanDraft) return;
    const dayCount = Math.max(2, Math.min(6, Number(state.me?.training_days_per_week || 3)));
    state.manualPlanDraft = {
        days: Array.from({ length: dayCount }, (_, index) => ({
            day_title: `自訂訓練 ${index + 1}`,
            exercises: [],
        })),
    };
    state.manualPlanDayIndex = 0;
}

function syncManualDayTitle() {
    const input = document.querySelector('#manual-day-title');
    const day = state.manualPlanDraft?.days?.[state.manualPlanDayIndex];
    if (input && day) day.day_title = input.value;
}

function manualPlanCompletion(days = state.manualPlanDraft?.days || []) {
    const incomplete = days
        .map((day, index) => ({
            index,
            missingTitle: !String(day?.day_title || '').trim(),
            missingExercises: !Array.isArray(day?.exercises) || day.exercises.length === 0,
        }))
        .filter((day) => day.missingTitle || day.missingExercises);
    return {
        completedCount: days.length - incomplete.length,
        incomplete,
    };
}

function focusIncompleteManualDay(issue) {
    state.manualPlanDayIndex = issue.index;
    renderManualPlanBuilder();
    const target = issue.missingTitle
        ? document.querySelector('#manual-day-title')
        : document.querySelector('#manual-exercise-search');
    target?.focus({ preventScroll: true });
    document.querySelector('#manual-plan-builder')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function manualPlannerMarkup() {
    ensureManualPlanDraft();
    const days = state.manualPlanDraft.days;
    state.manualPlanDayIndex = Math.max(0, Math.min(state.manualPlanDayIndex, days.length - 1));
    const day = days[state.manualPlanDayIndex];
    const completion = manualPlanCompletion(days);
    const incompleteDayNumbers = completion.incomplete.map((item) => `Day ${item.index + 1}`);
    const selectedIds = new Set(day.exercises.map((item) => Number(item.exercise_id)));
    const query = state.manualExerciseQuery.trim().toLocaleLowerCase('zh-TW');
    const filtered = state.exerciseOptions.filter((exercise) => {
        if (state.manualBodyPartId && String(exercise.body_part_id) !== String(state.manualBodyPartId)) return false;
        if (!query) return true;
        return [exercise.exercise_name, exercise.body_part_name, exercise.equipment]
            .some((value) => String(value || '').toLocaleLowerCase('zh-TW').includes(query));
    });
    const visible = filtered.slice(0, 24);
    return `
        <section class="manual-plan-builder" aria-label="自己規劃課表">
            <div class="manual-planner-heading">
                <div><h2 class="section-heading zh">自己挑選訓練動作</h2><p class="section-copy">每一天可安排 1 至 10 個動作，組數、次數與休息時間都能自行調整。</p></div>
                <label>訓練天數
                    <select id="manual-day-count" aria-label="自訂課表訓練天數">
                        ${[2, 3, 4, 5, 6].map((count) => `<option value="${count}" ${count === days.length ? 'selected' : ''}>${count} 天</option>`).join('')}
                    </select>
                </label>
            </div>
            <div class="manual-plan-progress ${completion.incomplete.length ? 'is-incomplete' : 'is-complete'}" role="status">
                <strong>已完成 ${completion.completedCount} / ${days.length} 個訓練日</strong>
                <span>${completion.incomplete.length
                    ? `${incompleteDayNumbers.join('、')} 尚需要動作或名稱。每個訓練日都完成後才能建立課表；如果不需要 ${days.length} 天，請調整右上方的「訓練天數」。`
                    : '所有訓練日都已安排完成，現在可以建立課表。'}</span>
            </div>
            <div class="manual-planner-layout">
                <aside class="manual-day-tabs" aria-label="自訂課表訓練日">
                    ${days.map((item, index) => {
                        const isIncomplete = !item.day_title.trim() || item.exercises.length === 0;
                        return `<button type="button" class="manual-day-tab ${index === state.manualPlanDayIndex ? 'is-active' : ''} ${isIncomplete ? 'is-incomplete' : 'is-complete'}" data-action="manual-select-day" data-index="${index}" ${isIncomplete ? 'aria-invalid="true"' : ''}><strong>Day ${index + 1}</strong><span>${isIncomplete ? '尚未安排完成' : `${item.exercises.length} 個動作 · 已完成`}</span></button>`;
                    }).join('')}
                </aside>
                <div class="manual-day-editor">
                    <label class="field">這一天的名稱<input id="manual-day-title" maxlength="100" value="${escapeHtml(day.day_title)}" aria-label="自訂訓練日名稱"></label>
                    <div class="manual-selected-list">
                        <div class="manual-section-title"><strong>已選動作</strong><span>${day.exercises.length} / 10</span></div>
                        ${day.exercises.length ? day.exercises.map((item, index) => {
                            const exercise = state.exerciseOptions.find((option) => Number(option.exercise_id) === Number(item.exercise_id));
                            return `<article class="manual-selected-exercise" data-manual-index="${index}">
                                <div class="manual-exercise-thumb">${exerciseImage(exercise?.image_url, exercise?.exercise_name || '動作', true)}</div>
                                <div class="manual-exercise-copy"><strong>${escapeHtml(exercise?.exercise_name || `動作 #${item.exercise_id}`)}</strong><span>${escapeHtml(exercise?.body_part_name || '')} · ${escapeHtml(exercise?.equipment || 'Bodyweight')}</span></div>
                                <label>組數<input class="manual-target-input" data-field="target_sets" type="number" min="1" max="10" value="${item.target_sets}"></label>
                                <label>次數<input class="manual-target-input" data-field="target_reps" type="number" min="1" max="50" value="${item.target_reps}"></label>
                                <label>休息<input class="manual-target-input" data-field="rest_seconds" type="number" min="0" max="600" step="5" value="${item.rest_seconds}"><small>秒</small></label>
                                <div class="manual-order-actions"><button type="button" class="icon-button compact" data-action="manual-move-exercise" data-index="${index}" data-direction="-1" aria-label="上移動作" ${index === 0 ? 'disabled' : ''}>↑</button><button type="button" class="icon-button compact" data-action="manual-move-exercise" data-index="${index}" data-direction="1" aria-label="下移動作" ${index === day.exercises.length - 1 ? 'disabled' : ''}>↓</button><button type="button" class="icon-button compact danger" data-action="manual-remove-exercise" data-index="${index}" aria-label="移除動作">×</button></div>
                            </article>`;
                        }).join('') : '<div class="empty-state compact">還沒有選擇動作，請從下方動作庫加入。</div>'}
                    </div>
                    <div class="manual-picker">
                        <div class="manual-section-title"><strong>從動作庫加入</strong><span>符合 ${formatNumber(filtered.length)} 個</span></div>
                        <div class="manual-picker-filters">
                            <input id="manual-exercise-search" type="search" maxlength="100" placeholder="搜尋動作、部位或器材" value="${escapeHtml(state.manualExerciseQuery)}">
                            <select id="manual-body-part-filter" aria-label="自訂課表身體部位篩選"><option value="">全部部位</option>${state.reference.body_parts.map((part) => `<option value="${part.body_part_id}" ${String(part.body_part_id) === String(state.manualBodyPartId) ? 'selected' : ''}>${escapeHtml(part.body_part_name)}</option>`).join('')}</select>
                            <button type="button" class="button button-small" data-action="manual-apply-filter">搜尋</button>
                        </div>
                        <div class="manual-exercise-results">
                            ${visible.map((exercise) => `<article class="manual-exercise-option">
                                <div class="manual-exercise-thumb">${exerciseImage(exercise.image_url, exercise.exercise_name, true)}</div>
                                <div class="manual-exercise-copy"><strong>${escapeHtml(exercise.exercise_name)}</strong><span>${escapeHtml(exercise.body_part_name)} · ${escapeHtml(exercise.difficulty_level)} · ${escapeHtml(exercise.equipment || 'Bodyweight')}</span></div>
                                <button type="button" class="button button-small ${selectedIds.has(Number(exercise.exercise_id)) ? '' : 'button-primary'}" data-action="manual-add-exercise" data-exercise-id="${exercise.exercise_id}" ${selectedIds.has(Number(exercise.exercise_id)) || day.exercises.length >= 10 ? 'disabled' : ''}>${selectedIds.has(Number(exercise.exercise_id)) ? '已加入' : '加入'}</button>
                            </article>`).join('') || '<div class="empty-state compact">找不到符合條件的動作。</div>'}
                        </div>
                        ${filtered.length > visible.length ? `<p class="manual-result-note">目前顯示前 ${visible.length} 筆，請輸入更完整的關鍵字縮小範圍。</p>` : ''}
                    </div>
                </div>
            </div>
        </section>`;
}

function renderManualPlanBuilder() {
    const container = document.querySelector('#manual-plan-builder');
    if (container) container.innerHTML = manualPlannerMarkup();
}

async function renderPlans() {
    loading();
    const [result, exerciseResult] = await Promise.all([
        api('/plans'),
        api('/exercises/options'),
    ]);
    state.plans = result.items || [];
    state.exerciseOptions = exerciseResult.items || [];
    if (state.planCreationMode === 'manual') ensureManualPlanDraft();
    if (!state.selectedPlanId && state.plans.length) {
        state.selectedPlanId = Number(state.plans[0].workout_plan_id);
    }
    const selected = state.plans.find((plan) => Number(plan.workout_plan_id) === Number(state.selectedPlanId)) || state.plans[0];
    const day = selected?.days?.[state.selectedDayIndex] || selected?.days?.[0];
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">我的訓練課表</h1><p class="page-subtitle">可以自己挑動作安排，也可以交給電腦依你的目標與設定規劃。</p></div></div>
            <form id="generate-plan-form" class="plan-create-form">
                <div class="plan-create-row">
                    <input name="plan_name" maxlength="120" placeholder="新課表名稱（可留白）" aria-label="新課表名稱">
                    <select name="generation_mode" id="generation-mode" aria-label="課表產生方式">
                        <option value="computer" ${state.planCreationMode === 'computer' ? 'selected' : ''}>電腦規劃</option>
                        <option value="manual" ${state.planCreationMode === 'manual' ? 'selected' : ''}>自己規劃</option>
                    </select>
                    <button class="button button-primary" type="submit">${state.planCreationMode === 'manual' ? '建立我的課表' : '請電腦規劃'}</button>
                </div>
                <p class="plan-generator-status">${state.planCreationMode === 'manual'
                    ? '由你決定每一天的動作、順序、組數、次數與休息時間。'
                    : '電腦會依目標、程度、偏好部位與可用時間安排，並優先避開最近課表用過的動作。'}</p>
                <div id="manual-plan-builder" ${state.planCreationMode === 'manual' ? '' : 'hidden'}>${state.planCreationMode === 'manual' ? manualPlannerMarkup() : ''}</div>
            </form>
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
                            <span>${selected.algorithm_version === 'manual-v1' ? '自己規劃' : '電腦規劃'}</span>
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
                                        <td data-label="示意圖"><div class="plan-exercise-media">${exerciseImage(exercise.image_url, exercise.exercise_name, true)}</div></td>
                                        <td data-label="動作名稱">${state.planEditing
                                            ? `<select class="plan-exercise-select" aria-label="第 ${exercise.exercise_order} 個動作">${state.exerciseOptions.map((option) => `<option value="${option.exercise_id}" ${Number(option.exercise_id) === Number(exercise.exercise_id) ? 'selected' : ''}>${escapeHtml(option.exercise_name)} · ${escapeHtml(option.body_part_name)}</option>`).join('')}</select>`
                                            : `<span class="exercise-name">${escapeHtml(exercise.exercise_name)}</span>`}</td>
                                        <td data-label="主要部位">${escapeHtml(exercise.body_part_name)}</td>
                                        <td data-label="器材">${escapeHtml(exercise.equipment || 'Bodyweight')}</td>
                                        <td data-label="目標">${state.planEditing
                                            ? `<div class="plan-number-pair"><input class="plan-sets" type="number" min="1" max="10" value="${exercise.target_sets}" aria-label="目標組數"><span>×</span><input class="plan-reps" type="number" min="1" max="50" value="${exercise.target_reps}" aria-label="目標次數"></div>`
                                            : `${exercise.target_sets} × ${exercise.target_reps}`}</td>
                                        <td data-label="休息">${state.planEditing
                                            ? `<div class="plan-rest-input"><input class="plan-rest" type="number" min="0" max="600" step="5" value="${exercise.rest_seconds}" aria-label="休息秒數"><span>秒</span></div>`
                                            : `${exercise.rest_seconds} 秒`}</td>
                                    </tr>`).join('')}</tbody>
                            </table></div>` : ''}
                    </section>
                </div>` : `
                <div class="empty-state">
                    尚未建立課表。先在「編輯資料」完成基本資料、訓練設定與偏好部位，再建立第一份課表。
                </div>`}
        </div>`;
}

async function renderWorkout() {
    loading();
    const session = await api('/workout-sessions/current');
    if (!session) {
        resetWorkoutTimers();
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
    const sessionId = Number(session.workout_session_id);
    if (activeWorkoutSessionId !== sessionId) {
        resetRestTimer();
        activeWorkoutSessionId = sessionId;
    }
    const savedKeys = new Set((session.sets || []).map((set) => `${set.workout_session_exercise_id}-${set.set_number}`));
    const savedCount = savedKeys.size;
    const targetCount = (session.exercises || []).reduce((sum, exercise) => sum + Number(exercise.target_sets), 0);
    const progress = targetCount ? Math.min(100, savedCount / targetCount * 100) : 0;
    const exercises = session.exercises || [];
    state.activeWorkoutExerciseIndex = Math.max(0, Math.min(state.activeWorkoutExerciseIndex, exercises.length - 1));
    const exercise = exercises[state.activeWorkoutExerciseIndex];
    const exerciseSets = (session.sets || []).filter((set) => Number(set.workout_session_exercise_id) === Number(exercise?.workout_session_exercise_id));
    main.innerHTML = `
        <div class="workout-shell">
            <div class="workout-topline">
                <div>
                    <h1 class="page-title zh">${escapeHtml(session.day_title || '進行中訓練')}</h1>
                    <p class="page-subtitle">${escapeHtml(session.plan_name || '')} · 開始於 ${formatDateTime(session.started_at)}</p>
                </div>
                <div class="workout-topline-actions">
                    <div class="workout-total-timer" aria-label="總訓練時間">
                        <span class="stat-label">總訓練時間</span>
                        <strong id="workout-elapsed-time">00:00:00</strong>
                    </div>
                    <button class="icon-button" data-action="navigate" data-route="dashboard" title="離開訓練頁" aria-label="離開訓練頁">×</button>
                </div>
            </div>
            <div class="workout-progress"><span>${savedCount} / ${targetCount} 組</span><div class="progress-track"><span style="width:${progress}%"></span></div><span>${Math.round(progress)}%</span></div>
            <div class="workout-stepper" aria-label="訓練動作進度">
                ${exercises.map((item, index) => {
                    const complete = (session.sets || []).filter((set) => Number(set.workout_session_exercise_id) === Number(item.workout_session_exercise_id)).length >= Number(item.target_sets);
                    return `<button class="workout-step ${index === state.activeWorkoutExerciseIndex ? 'is-active' : ''} ${complete ? 'is-complete' : ''}" data-action="select-workout-exercise" data-index="${index}"><span>${index + 1}</span>${escapeHtml(item.exercise_name)}</button>`;
                }).join('')}
            </div>
            ${exercise ? `
                    <section class="workout-exercise is-focused">
                        <div class="workout-media">
                            ${exerciseImage(exercise.image_url, exercise.exercise_name)}
                        </div>
                        <div>
                            <span class="stat-label">${escapeHtml(exercise.body_part_name)} · ${escapeHtml(exercise.equipment || 'Bodyweight')}</span>
                            <h2>${escapeHtml(exercise.exercise_name)}</h2>
                            <p class="page-subtitle">目標 ${exercise.target_sets} × ${exercise.target_reps} · 休息 ${exercise.rest_seconds} 秒</p>
                            <button class="button button-small" data-action="adjust-session-target" data-session-id="${session.workout_session_id}" data-session-exercise-id="${exercise.workout_session_exercise_id}" data-target-sets="${exercise.target_sets}" data-target-reps="${exercise.target_reps}" data-rest-seconds="${exercise.rest_seconds}" data-target-weight="${exercise.target_weight_kg ?? ''}">調整本次目標</button>
                            <details style="margin-top:14px"><summary class="text-link">查看動作步驟</summary><p class="exercise-description" style="display:block;min-height:0;-webkit-line-clamp:initial">${escapeHtml(exercise.description)}</p></details>
                            <div class="set-table">
                                <div class="set-row set-row-head"><span>Set</span><span>Weight (kg)</span><span>Reps</span><span>狀態</span></div>
                                ${Array.from({ length: Number(exercise.target_sets) }, (_, index) => {
                                    const setNumber = index + 1;
                                    const saved = exerciseSets.find((set) => Number(set.set_number) === setNumber);
                                    return `<div class="set-row">
                                        <strong>${setNumber}</strong>
                                        <input class="set-input" id="weight-${exercise.workout_session_exercise_id}-${setNumber}" type="number" inputmode="decimal" min="0" max="999.99" step="0.01" value="${saved ? escapeHtml(saved.weight_kg) : escapeHtml(exercise.target_weight_kg ?? '0')}" aria-label="第 ${setNumber} 組重量">
                                        <input class="set-input" id="reps-${exercise.workout_session_exercise_id}-${setNumber}" type="number" inputmode="numeric" min="1" max="999" value="${saved ? escapeHtml(saved.reps) : exercise.target_reps}" aria-label="第 ${setNumber} 組次數">
                                        ${saved
                                            ? `<div class="set-actions"><button class="icon-button compact" data-action="update-set" data-set-id="${saved.workout_set_id}" data-session-exercise-id="${exercise.workout_session_exercise_id}" data-set-number="${setNumber}" title="更新此組" aria-label="更新此組">↻</button><button class="icon-button compact danger" data-action="delete-set" data-set-id="${saved.workout_set_id}" title="刪除此組" aria-label="刪除此組">×</button></div>`
                                            : `<button class="button button-small" data-action="save-set" data-session-id="${session.workout_session_id}" data-session-exercise-id="${exercise.workout_session_exercise_id}" data-set-number="${setNumber}" data-rest-seconds="${exercise.rest_seconds}">儲存此組</button>`}
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
                <div><span class="stat-label">REST TIMER</span><strong id="rest-countdown">${restTimerText()}</strong></div>
                <button class="button button-small" data-action="stop-rest-timer" ${restTimerState !== 'running' ? 'disabled' : ''}>略過休息</button>
            </aside>
            <div class="field workout-notes"><label for="workout-notes">本次訓練備註</label><textarea id="workout-notes" maxlength="1000" placeholder="記錄今天的狀態、疼痛或重量調整">${escapeHtml(session.notes || '')}</textarea></div>
            <div class="workout-actions">
                <button class="button button-danger" data-action="finish-workout" data-status="cancel" data-session-id="${session.workout_session_id}">取消本次訓練</button>
                <button class="button button-primary" data-action="finish-workout" data-status="complete" data-session-id="${session.workout_session_id}" ${savedCount === 0 ? 'disabled' : ''}>完成訓練</button>
            </div>
        </div>`;
    startWorkoutTimer(session.started_at);
    updateRestTimerDisplay();
}

function startRestTimer(seconds) {
    window.clearInterval(restTimerId);
    restTimerRemaining = Math.max(0, Number(seconds));
    restTimerState = restTimerRemaining > 0 ? 'running' : 'not-needed';
    updateRestTimerDisplay();
    if (restTimerRemaining <= 0) return;
    restTimerId = window.setInterval(() => {
        restTimerRemaining -= 1;
        updateRestTimerDisplay();
        if (restTimerRemaining <= 0) {
            window.clearInterval(restTimerId);
            restTimerId = null;
            restTimerState = 'finished';
            updateRestTimerDisplay();
            showToast('休息完成，可以開始下一組。');
        }
    }, 1000);
}

function restTimerText() {
    if (restTimerState === 'running') {
        return `${Math.floor(restTimerRemaining / 60)}:${String(restTimerRemaining % 60).padStart(2, '0')}`;
    }
    if (restTimerState === 'finished') return '休息完成';
    if (restTimerState === 'skipped') return '已略過休息';
    if (restTimerState === 'not-needed') return '本組不需休息';
    return '儲存一組後開始';
}

function updateRestTimerDisplay() {
    const display = document.querySelector('#rest-countdown');
    if (display) display.textContent = restTimerText();
    const stop = document.querySelector('[data-action="stop-rest-timer"]');
    if (stop) stop.disabled = restTimerState !== 'running';
}

function resetRestTimer() {
    window.clearInterval(restTimerId);
    restTimerId = null;
    restTimerRemaining = 0;
    restTimerState = 'idle';
    updateRestTimerDisplay();
}

function stopWorkoutTimer() {
    window.clearInterval(workoutTimerId);
    workoutTimerId = null;
}

function startWorkoutTimer(startedAt) {
    stopWorkoutTimer();
    const startedAtMs = new Date(normalizeDateValue(startedAt)).getTime();
    const update = () => {
        const display = document.querySelector('#workout-elapsed-time');
        if (!display) return;
        display.textContent = Number.isFinite(startedAtMs)
            ? formatElapsedDuration((Date.now() - startedAtMs) / 1000)
            : '--:--:--';
    };
    update();
    workoutTimerId = window.setInterval(update, 1000);
}

function resetWorkoutTimers() {
    resetRestTimer();
    stopWorkoutTimer();
    activeWorkoutSessionId = null;
}

async function renderExercises() {
    loading();
    const params = new URLSearchParams(Object.entries({
        ...state.exerciseFilters,
        page: state.exercisePage,
        page_size: 24,
    }).filter(([, value]) => value));
    const result = await api(`/exercises?${params.toString()}`);
    const items = result.items || [];
    const total = Number(result.total || 0);
    const totalPages = Math.max(1, Math.ceil(total / Number(result.page_size || 24)));
    if (state.exercisePage > totalPages) {
        state.exercisePage = totalPages;
        await renderExercises();
        return;
    }
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">動作資料庫</h1><p class="page-subtitle">搜尋動作、器材、難度與中文步驟，GIF 來自你提供的本機資料集。</p></div><span class="stat-label">共 ${formatNumber(total)} 個動作</span></div>
            <form id="exercise-filter-form" class="toolbar">
                <input name="q" type="search" maxlength="100" placeholder="搜尋動作名稱或身體部位" value="${escapeHtml(state.exerciseFilters.q)}">
                <select name="body_part_id"><option value="">全部部位</option>${state.reference.body_parts.map((part) => `<option value="${part.body_part_id}" ${String(part.body_part_id) === String(state.exerciseFilters.body_part_id) ? 'selected' : ''}>${escapeHtml(part.body_part_name)}</option>`).join('')}</select>
                <select name="difficulty_level"><option value="">全部難度</option>${['Beginner', 'Intermediate', 'Advanced'].map((level) => `<option ${level === state.exerciseFilters.difficulty_level ? 'selected' : ''}>${level}</option>`).join('')}</select>
            </form>
            ${items.length ? `<div class="exercise-grid">${items.map((exercise) => `
                <article class="exercise-card">
                    <div class="exercise-card-media">${exerciseImage(exercise.image_url, exercise.exercise_name, true)}</div>
                    <div class="exercise-card-body">
                        <h3>${escapeHtml(exercise.exercise_name)}</h3>
                        <div class="exercise-meta"><span>${escapeHtml(exercise.body_part_name)}</span><span>${escapeHtml(exercise.difficulty_level)}</span><span>${escapeHtml(exercise.equipment || 'Bodyweight')}</span></div>
                        <p class="exercise-description">${escapeHtml(exercise.description)}</p>
                    </div>
                </article>`).join('')}</div>` : '<div class="empty-state">沒有符合條件的動作。</div>'}
            ${totalPages > 1 ? `<nav class="pagination" aria-label="動作分頁">
                <button class="button button-small" data-action="exercise-page" data-page="${state.exercisePage - 1}" ${state.exercisePage <= 1 ? 'disabled' : ''}>← 上一頁</button>
                <span>第 ${formatNumber(state.exercisePage)} / ${formatNumber(totalPages)} 頁</span>
                <button class="button button-small" data-action="exercise-page" data-page="${state.exercisePage + 1}" ${state.exercisePage >= totalPages ? 'disabled' : ''}>下一頁 →</button>
            </nav>` : ''}
        </div>`;
}

async function renderHistory() {
    loading();
    const params = new URLSearchParams(Object.entries(state.historyFilters).filter(([, value]) => value));
    const [result, exercises] = await Promise.all([
        api(`/workout-sessions?${params.toString()}`),
        api('/exercises/options'),
    ]);
    state.historyFilters.start_date = result.start_date;
    state.historyFilters.end_date = result.end_date;
    const detail = state.historyDetailId ? await api(`/workout-sessions/${state.historyDetailId}`) : null;
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">訓練歷史</h1><p class="page-subtitle">已完成與已取消的訓練都會保留，Dashboard 只統計已完成項目。</p></div></div>
            <form id="history-filter-form" class="toolbar" aria-label="訓練歷史篩選">
                <label>開始日期 <input name="start_date" type="date" min="1900-01-01" value="${escapeHtml(result.start_date)}" required></label>
                <label>結束日期 <input name="end_date" type="date" min="1900-01-01" value="${escapeHtml(result.end_date)}" required></label>
                <select name="status" aria-label="訓練狀態"><option value="">全部狀態</option><option value="completed" ${state.historyFilters.status === 'completed' ? 'selected' : ''}>已完成</option><option value="cancelled" ${state.historyFilters.status === 'cancelled' ? 'selected' : ''}>已取消</option></select>
                <select name="exercise_id" aria-label="動作"><option value="">全部動作</option>${(exercises.items || []).map((item) => `<option value="${item.exercise_id}" ${String(item.exercise_id) === String(state.historyFilters.exercise_id) ? 'selected' : ''}>${escapeHtml(item.exercise_name)}</option>`).join('')}</select>
                <button class="button button-small" type="submit">套用篩選</button>
            </form>
            <section class="data-section" style="margin-top:32px">${historyTable(result.items || [])}</section>
            ${detail ? renderWorkoutHistoryDetail(detail) : ''}
        </div>`;
}

function renderWorkoutHistoryDetail(session) {
    return `<section class="data-section" style="margin-top:24px" aria-label="訓練歷史明細">
        <div class="page-header"><div><h2 class="section-heading">${escapeHtml(session.day_title || session.plan_name || '訓練明細')}</h2><p class="section-copy">${formatDateTime(session.started_at)} · ${session.status === 'completed' ? '已完成' : '已取消'}</p></div><button class="button button-small" data-action="close-workout-detail">關閉明細</button></div>
        ${(session.exercises || []).map((exercise) => {
            const sets = (session.sets || []).filter((set) => Number(set.workout_session_exercise_id) === Number(exercise.workout_session_exercise_id));
            return `<article class="settings-section" style="margin-top:16px">
                <div class="exercise-meta"><strong>${escapeHtml(exercise.exercise_name)}</strong><span>${escapeHtml(exercise.body_part_name)}</span><span>V${exercise.version_no}</span></div>
                <p>${escapeHtml(exercise.description)}</p>
                ${sets.length ? `<div class="set-table">${sets.map((set) => `<div class="set-row"><strong>${set.set_number}</strong><input id="history-weight-${set.workout_set_id}" class="set-input" type="number" min="0" max="999.99" step="0.01" value="${escapeHtml(set.weight_kg)}" aria-label="第 ${set.set_number} 組重量"><input id="history-reps-${set.workout_set_id}" class="set-input" type="number" min="1" max="999" value="${set.reps}" aria-label="第 ${set.set_number} 組次數"><div class="set-actions"><button class="icon-button compact" data-action="update-history-set" data-set-id="${set.workout_set_id}" title="更新此組" aria-label="更新此組">↻</button><button class="icon-button compact danger" data-action="delete-history-set" data-set-id="${set.workout_set_id}" title="刪除此組" aria-label="刪除此組">×</button></div></div>`).join('')}</div>` : '<p class="empty-state">這個動作沒有已儲存組數。</p>'}
            </article>`;
        }).join('')}
    </section>`;
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
                        <div class="field"><label for="record-date">日期</label><input id="record-date" name="record_date" type="date" min="1900-01-01" max="${new Date().toISOString().slice(0, 10)}" required></div>
                        <div class="field"><label for="record-weight">體重 kg</label><input id="record-weight" name="weight_kg" type="number" min="20" max="500" step="0.01" required></div>
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
    const aiStatus = state.adminTab === 'ai' ? await api('/ai/status') : null;
    let databaseTable = null;
    if (databaseOverview) {
        if (!databaseOverview.tables.some((table) => table.table_name === state.adminSelectedTable)) {
            state.adminSelectedTable = databaseOverview.tables[0]?.table_name || 'users';
        }
        databaseTable = await api(`/admin/database/tables/${state.adminSelectedTable}`);
    }
    const editingExercise = exercises.items.find((item) => Number(item.exercise_id) === Number(state.adminEditingExerciseId));
    const exerciseForm = `<form id="admin-exercise-form" class="form-grid two-columns" data-exercise-id="${editingExercise?.exercise_id || ''}" style="margin-top:24px;padding-bottom:24px;border-bottom:1px solid var(--line)">
            <div class="field"><label>動作名稱</label><input name="exercise_name" required maxlength="120" value="${escapeHtml(editingExercise?.exercise_name || '')}"></div>
            <div class="field"><label>主要部位</label><select name="body_part_id" required ${editingExercise ? 'disabled' : ''}>${state.reference.body_parts.map((part) => `<option value="${part.body_part_id}" ${Number(part.body_part_id) === Number(editingExercise?.body_part_id) ? 'selected' : ''}>${escapeHtml(part.body_part_name)}</option>`).join('')}</select></div>
            <div class="field"><label>難度</label><select name="difficulty_level">${['Beginner', 'Intermediate', 'Advanced'].map((level) => `<option ${level === editingExercise?.difficulty_level ? 'selected' : ''}>${level}</option>`).join('')}</select></div>
            <div class="field"><label>器材</label><input name="equipment" maxlength="100" value="${escapeHtml(editingExercise?.equipment || '')}"></div>
            <div class="field" style="grid-column:1/-1"><label>動作說明</label><textarea name="description" required maxlength="4000">${escapeHtml(editingExercise?.description || '')}</textarea></div>
            <div class="field" style="grid-column:1/-1"><label>HTTPS 圖片或 GIF 網址</label><input name="image_url" maxlength="2048" placeholder="https://example.com/exercise.gif" value="${escapeHtml(editingExercise?.image_url || '')}"></div>
            <div class="form-actions" style="grid-column:1/-1"><button class="button button-primary" type="submit">${editingExercise ? '建立新版內容' : '新增動作'}</button>${editingExercise ? '<button class="button" type="button" data-action="cancel-edit-exercise">取消編輯</button>' : ''}</div>
        </form>`;
    const referenceEditor = `<div class="reference-admin-grid">
        ${[['training-goals', state.reference.training_goals, 'training_goal_id', 'goal_name'], ['body-parts', state.reference.body_parts, 'body_part_id', 'body_part_name']].map(([type, items, idKey, nameKey]) => `<section class="settings-section"><h2 class="section-heading">${type === 'training-goals' ? '訓練目標說明' : '身體部位說明'}</h2>${items.map((item) => `<form class="form-grid admin-reference-form" data-reference-type="${type}" data-reference-id="${item[idKey]}"><div class="field"><label>${escapeHtml(item[nameKey])}</label><textarea name="description" maxlength="1000">${escapeHtml(item.description || '')}</textarea></div><button class="button button-small" type="submit">儲存說明</button></form>`).join('')}</section>`).join('')}
    </div>`;
    const content = state.adminTab === 'ai'
        ? renderAiSettings(aiStatus)
        : state.adminTab === 'database'
        ? renderDatabaseSystem(databaseOverview, databaseTable)
        : state.adminTab === 'references'
        ? referenceEditor
        : state.adminTab === 'exercises'
        ? `${exerciseForm}
            <table class="data-table responsive"><thead><tr><th>ID</th><th>動作</th><th>部位</th><th>難度</th><th>器材</th><th>狀態</th><th>操作</th></tr></thead><tbody>${exercises.items.map((item) => `<tr><td data-label="ID">${item.exercise_id}</td><td data-label="動作">${escapeHtml(item.exercise_name)}</td><td data-label="部位">${escapeHtml(item.body_part_name)}</td><td data-label="難度">${escapeHtml(item.difficulty_level)}</td><td data-label="器材">${escapeHtml(item.equipment || '-')}</td><td data-label="狀態"><span class="status status-${Number(item.is_active) ? 'active' : 'inactive'}">${Number(item.is_active) ? '啟用' : '停用'}</span></td><td data-label="操作"><div class="form-actions" style="margin-top:0"><button class="button button-small" data-action="edit-exercise" data-exercise-id="${item.exercise_id}">編輯</button>${Number(item.is_active) ? `<button class="button button-small button-danger" data-action="delete-exercise" data-exercise-id="${item.exercise_id}">停用</button>` : `<button class="button button-small" data-action="toggle-exercise" data-exercise-id="${item.exercise_id}" data-active="1">啟用</button>`}</div></td></tr>`).join('')}</tbody></table>`
        : `<table class="data-table responsive"><thead><tr><th>ID</th><th>姓名</th><th>Email</th><th>身份</th><th>帳號狀態</th><th>建立時間</th></tr></thead><tbody>${users.items.map((item) => `<tr><td data-label="ID">${item.user_id}</td><td data-label="姓名">${escapeHtml(item.name)}</td><td data-label="Email">${escapeHtml(item.email)}</td><td data-label="身份">${Number(item.is_admin) ? 'ADMIN' : 'USER'}</td><td data-label="狀態"><span class="status status-${Number(item.is_active) ? 'active' : 'inactive'}">${Number(item.is_active) ? '啟用' : '停用'}</span></td><td data-label="建立時間">${formatDateTime(item.created_at)}</td></tr>`).join('')}</tbody></table>`;
    main.innerHTML = `
        <div class="page-shell">
            <div class="page-header"><div><h1 class="page-title zh">管理後台</h1><p class="page-subtitle">管理會員與動作主資料，並檢視正式資料庫的結構、關聯與即時資料。</p></div></div>
            <div class="admin-grid">
                ${Object.entries({ users: '會員', exercises: '動作', plans: '課表', completed_workouts: '完成訓練', sets: '訓練組數' }).map(([key, label]) => `<div class="admin-stat"><span class="stat-label">${label}</span><strong>${formatNumber(stats[key])}</strong></div>`).join('')}
            </div>
            <div class="tabs"><button class="tab ${state.adminTab === 'users' ? 'is-active' : ''}" data-action="admin-tab" data-tab="users">會員清單</button><button class="tab ${state.adminTab === 'exercises' ? 'is-active' : ''}" data-action="admin-tab" data-tab="exercises">動作管理</button><button class="tab ${state.adminTab === 'references' ? 'is-active' : ''}" data-action="admin-tab" data-tab="references">參考資料</button><button class="tab ${state.adminTab === 'database' ? 'is-active' : ''}" data-action="admin-tab" data-tab="database">資料庫系統</button><button class="tab ${state.adminTab === 'ai' ? 'is-active' : ''}" data-action="admin-tab" data-tab="ai">模型接口</button></div>
            ${content}
        </div>`;
}

function renderAiSettings(status) {
    return `
        <section class="ai-settings" aria-label="模型 API 接口">
            <div class="ai-settings-heading">
                <div><h2 class="section-heading">模型 API 接口</h2><p class="section-copy">金鑰只儲存在 Render 環境設定，不會寫入資料庫或傳送到瀏覽器。</p></div>
                <span class="ai-state ${status.enabled ? 'is-ready' : ''}">${status.enabled ? '已啟用' : '尚未設定'}</span>
            </div>
            <dl class="ai-settings-list">
                <div><dt>AI_API_KEY</dt><dd>${status.secret_configured ? '已安全設定' : '等待你在 Render 填入'}</dd></div>
                <div><dt>AI_MODEL</dt><dd>${escapeHtml(status.model || '等待設定')}</dd></div>
                <div><dt>AI_API_URL</dt><dd>${escapeHtml(status.endpoint_host || '等待設定')}</dd></div>
                <div><dt>接口格式</dt><dd>${escapeHtml(status.provider)}</dd></div>
            </dl>
            <p class="ai-settings-note">設定完成後，會員可在「我的課表」選擇 AI 規劃並輸入訓練需求。模型輸出仍須通過動作 ID、程度、天數、組次與休息時間驗證。</p>
        </section>`;
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
    if (!state.authenticated) return;
    if (state.me && state.reference) return;
    const [me, reference] = await Promise.all([api('/me'), api('/reference')]);
    state.me = me;
    state.reference = reference;
}

async function renderRoute() {
    state.route = currentRoute();
    if (state.route !== 'workout') stopWorkoutTimer();
    try {
        if (!state.authenticated) {
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
        } else if (action === 'manual-select-day') {
            syncManualDayTitle();
            state.manualPlanDayIndex = Number(control.dataset.index);
            renderManualPlanBuilder();
        } else if (action === 'manual-add-exercise') {
            syncManualDayTitle();
            const day = state.manualPlanDraft.days[state.manualPlanDayIndex];
            const exerciseId = Number(control.dataset.exerciseId);
            if (day.exercises.length >= 10) throw new Error('每個訓練日最多安排 10 個動作。');
            if (!day.exercises.some((item) => Number(item.exercise_id) === exerciseId)) {
                const [sets, reps, rest] = manualPrescription();
                day.exercises.push({
                    exercise_id: exerciseId,
                    target_sets: sets,
                    target_reps: reps,
                    rest_seconds: rest,
                });
            }
            renderManualPlanBuilder();
        } else if (action === 'manual-remove-exercise') {
            syncManualDayTitle();
            state.manualPlanDraft.days[state.manualPlanDayIndex].exercises.splice(Number(control.dataset.index), 1);
            renderManualPlanBuilder();
        } else if (action === 'manual-move-exercise') {
            syncManualDayTitle();
            const exercises = state.manualPlanDraft.days[state.manualPlanDayIndex].exercises;
            const from = Number(control.dataset.index);
            const to = from + Number(control.dataset.direction);
            if (to >= 0 && to < exercises.length) {
                [exercises[from], exercises[to]] = [exercises[to], exercises[from]];
            }
            renderManualPlanBuilder();
        } else if (action === 'manual-apply-filter') {
            syncManualDayTitle();
            state.manualExerciseQuery = document.querySelector('#manual-exercise-search')?.value || '';
            state.manualBodyPartId = document.querySelector('#manual-body-part-filter')?.value || '';
            renderManualPlanBuilder();
        } else if (action === 'exercise-page') {
            state.exercisePage = Number(control.dataset.page);
            await renderExercises();
            window.scrollTo({ top: 0, behavior: 'smooth' });
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
            if (!window.confirm('確定封存這份課表？歷史訓練與場次快照會保留。')) return;
            await api(`/plans/${control.dataset.planId}`, { method: 'DELETE' });
            state.selectedPlanId = null;
            state.selectedDayIndex = 0;
            showToast('課表已封存，歷史訓練仍保留。');
            await renderPlans();
        } else if (action === 'start-workout') {
            control.disabled = true;
            await api('/workout-sessions', {
                method: 'POST',
                body: JSON.stringify({ plan_day_id: Number(control.dataset.dayId) }),
            });
            resetWorkoutTimers();
            state.activeWorkoutExerciseIndex = 0;
            navigate('workout');
        } else if (action === 'select-workout-exercise') {
            state.activeWorkoutExerciseIndex = Number(control.dataset.index);
            await renderWorkout();
        } else if (action === 'save-set') {
            control.disabled = true;
            control.textContent = '儲存中';
            const sessionExerciseId = Number(control.dataset.sessionExerciseId);
            const setNumber = Number(control.dataset.setNumber);
            const weight = document.querySelector(`#weight-${sessionExerciseId}-${setNumber}`).value;
            const reps = document.querySelector(`#reps-${sessionExerciseId}-${setNumber}`).value;
            await api(`/workout-sessions/${control.dataset.sessionId}/sets`, {
                method: 'POST',
                body: JSON.stringify({ workout_session_exercise_id: sessionExerciseId, set_number: setNumber, weight_kg: weight, reps: Number(reps) }),
            });
            showToast(`第 ${setNumber} 組已儲存。`);
            await renderWorkout();
            startRestTimer(Number(control.dataset.restSeconds));
        } else if (action === 'update-set') {
            const sessionExerciseId = Number(control.dataset.sessionExerciseId);
            const setNumber = Number(control.dataset.setNumber);
            const weight = document.querySelector(`#weight-${sessionExerciseId}-${setNumber}`).value;
            const reps = document.querySelector(`#reps-${sessionExerciseId}-${setNumber}`).value;
            await api(`/workout-sets/${control.dataset.setId}`, {
                method: 'PATCH',
                body: JSON.stringify({ weight_kg: weight, reps: Number(reps) }),
            });
            showToast(`第 ${setNumber} 組已更新。`);
            await renderWorkout();
        } else if (action === 'adjust-session-target') {
            const sets = window.prompt('本次目標組數（不可低於已完成組數）', control.dataset.targetSets);
            if (sets === null) return;
            const reps = window.prompt('本次每組目標次數', control.dataset.targetReps);
            if (reps === null) return;
            const weight = window.prompt('本次目標外加重量（kg，可填 0）', control.dataset.targetWeight || '0');
            if (weight === null) return;
            await api(`/workout-sessions/${control.dataset.sessionId}/exercises/${control.dataset.sessionExerciseId}`, {
                method: 'PATCH',
                body: JSON.stringify({
                    target_sets: Number(sets),
                    target_reps: Number(reps),
                    rest_seconds: Number(control.dataset.restSeconds),
                    target_weight_kg: weight,
                }),
            });
            showToast('已調整本次運動目標，不會修改原課表。');
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
            restTimerState = 'skipped';
            updateRestTimerDisplay();
        } else if (action === 'finish-workout') {
            const finishing = control.dataset.status === 'complete';
            if (!window.confirm(finishing ? '確定完成這次訓練？' : '確定取消這次訓練？')) return;
            await api(`/workout-sessions/${control.dataset.sessionId}/${control.dataset.status}`, {
                method: 'POST',
                body: JSON.stringify({ notes: document.querySelector('#workout-notes')?.value || '' }),
            });
            resetWorkoutTimers();
            showToast(finishing ? '訓練已完成並納入統計。' : '本次訓練已取消。');
            navigate(finishing ? 'dashboard' : 'history');
        } else if (action === 'delete-workout') {
            if (!window.confirm('確定刪除這次訓練與所有組數？')) return;
            await api(`/workout-sessions/${control.dataset.sessionId}`, { method: 'DELETE' });
            showToast('訓練紀錄已刪除。');
            await renderHistory();
        } else if (action === 'view-workout') {
            state.historyDetailId = Number(control.dataset.sessionId);
            await renderHistory();
        } else if (action === 'close-workout-detail') {
            state.historyDetailId = null;
            await renderHistory();
        } else if (action === 'update-history-set') {
            const setId = Number(control.dataset.setId);
            await api(`/workout-sets/${setId}`, {
                method: 'PATCH',
                body: JSON.stringify({
                    weight_kg: document.querySelector(`#history-weight-${setId}`).value,
                    reps: Number(document.querySelector(`#history-reps-${setId}`).value),
                }),
            });
            showToast('歷史組數已更新。');
            await renderHistory();
        } else if (action === 'delete-history-set') {
            if (!window.confirm('確定刪除這一組紀錄？完成場次至少須保留一組。')) return;
            await api(`/workout-sets/${control.dataset.setId}`, { method: 'DELETE' });
            showToast('歷史組數已刪除。');
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
            state.adminEditingExerciseId = null;
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
        } else if (action === 'edit-exercise') {
            state.adminEditingExerciseId = Number(control.dataset.exerciseId);
            await renderAdmin();
            document.querySelector('#admin-exercise-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (action === 'cancel-edit-exercise') {
            state.adminEditingExerciseId = null;
            await renderAdmin();
        } else if (action === 'delete-exercise') {
            if (!window.confirm('確定停用這個動作？既有課表與歷史版本會完整保留。')) return;
            await api(`/admin/exercises/${control.dataset.exerciseId}`, { method: 'DELETE' });
            showToast('動作已停用；舊課表與歷史版本仍保留。');
            await renderAdmin();
        }
    } catch (error) {
        control.disabled = false;
        if (action === 'save-set') control.textContent = '尚未儲存，重試';
        showToast(error.message, 'error');
    }
});

document.addEventListener('change', async (event) => {
    if (event.target.matches('#plan-select')) {
        state.selectedPlanId = Number(event.target.value);
        state.selectedDayIndex = 0;
        state.planEditing = false;
        await renderPlans();
    } else if (event.target.matches('#generation-mode')) {
        state.planCreationMode = event.target.value;
        if (state.planCreationMode === 'manual') ensureManualPlanDraft();
        await renderPlans();
    } else if (event.target.matches('#manual-day-count')) {
        syncManualDayTitle();
        const nextCount = Number(event.target.value);
        const days = state.manualPlanDraft.days;
        if (nextCount < days.length) {
            const removedHaveExercises = days.slice(nextCount).some((day) => day.exercises.length > 0);
            if (removedHaveExercises && !window.confirm('減少天數會移除後面訓練日已選的動作，確定繼續？')) {
                event.target.value = String(days.length);
                return;
            }
            days.splice(nextCount);
        } else {
            while (days.length < nextCount) {
                days.push({ day_title: `自訂訓練 ${days.length + 1}`, exercises: [] });
            }
        }
        state.manualPlanDayIndex = Math.min(state.manualPlanDayIndex, nextCount - 1);
        renderManualPlanBuilder();
    }
});

document.addEventListener('input', (event) => {
    if (event.target.matches('#manual-day-title')) {
        const day = state.manualPlanDraft?.days?.[state.manualPlanDayIndex];
        if (day) day.day_title = event.target.value;
        return;
    }
    if (event.target.matches('.manual-target-input')) {
        const row = event.target.closest('[data-manual-index]');
        const item = state.manualPlanDraft?.days?.[state.manualPlanDayIndex]?.exercises?.[Number(row?.dataset.manualIndex)];
        if (item) item[event.target.dataset.field] = Number(event.target.value);
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
            state.exercisePage = 1;
            await renderExercises();
        } else if (form.id === 'dashboard-filter-form') {
            state.dashboardFilters = values;
            await renderDashboard();
        } else if (form.id === 'history-filter-form') {
            state.historyFilters = values;
            state.historyDetailId = null;
            await renderHistory();
        } else if (form.id === 'generate-plan-form') {
            const manual = values.generation_mode === 'manual';
            let plan;
            if (manual) {
                syncManualDayTitle();
                const days = state.manualPlanDraft?.days || [];
                const issue = manualPlanCompletion(days).incomplete[0];
                if (issue) {
                    focusIncompleteManualDay(issue);
                    const missing = [
                        issue.missingTitle ? '訓練日名稱' : '',
                        issue.missingExercises ? '至少 1 個動作' : '',
                    ].filter(Boolean).join('與');
                    throw new Error(`Day ${issue.index + 1} 尚缺${missing}。你目前選擇 ${days.length} 個訓練日，請完成每一天，或調整「訓練天數」。`);
                }
                plan = await api('/plans/manual', {
                    method: 'POST',
                    body: JSON.stringify({ plan_name: values.plan_name || null, days }),
                });
                state.manualPlanDraft = null;
                state.manualPlanDayIndex = 0;
                state.manualExerciseQuery = '';
                state.manualBodyPartId = '';
            } else {
                plan = await api('/plans/generate', {
                    method: 'POST',
                    body: JSON.stringify({ plan_name: values.plan_name || null }),
                });
            }
            state.selectedPlanId = Number(plan.workout_plan_id);
            state.selectedDayIndex = 0;
            state.planEditing = false;
            showToast(manual ? '你的自訂課表已建立。' : '電腦已建立一份不同組合的訓練課表。');
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
            const exerciseId = Number(form.dataset.exerciseId || 0);
            const payload = { ...values };
            if (!exerciseId) payload.body_part_id = Number(values.body_part_id);
            await api(exerciseId ? `/admin/exercises/${exerciseId}` : '/admin/exercises', {
                method: exerciseId ? 'PATCH' : 'POST',
                body: JSON.stringify(payload),
            });
            showToast(exerciseId ? '動作已建立新的不可變版本。' : '新動作已加入資料庫。');
            state.adminEditingExerciseId = null;
            await renderAdmin();
        } else if (form.matches('.admin-reference-form')) {
            await api(`/admin/${form.dataset.referenceType}/${form.dataset.referenceId}`, {
                method: 'PATCH',
                body: JSON.stringify({ description: values.description || '' }),
            });
            state.reference = await api('/reference');
            showToast('參考資料說明已儲存。');
            await renderAdmin();
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        if (submit) submit.disabled = false;
    }
});

window.addEventListener('hashchange', renderRoute);

document.addEventListener('error', (event) => {
    const image = event.target;
    if (!(image instanceof HTMLImageElement) || !image.matches('[data-exercise-image]')) return;
    image.hidden = true;
    const fallback = image.nextElementSibling;
    if (fallback?.classList.contains('exercise-image-fallback')) fallback.hidden = false;
}, true);

async function initializeApplication() {
    try {
        const session = await api('/auth/session');
        state.authenticated = true;
        state.me = session;
    } catch (error) {
        state.authenticated = false;
        state.me = null;
    }
    await renderRoute();
}

initializeApplication();
