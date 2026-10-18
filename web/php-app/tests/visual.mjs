import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

let chromium;
try {
    ({ chromium } = await import('playwright'));
} catch {
    console.log('Playwright package unavailable; browser QA can use the local preview instead.');
    process.exit(0);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const css = fs.readFileSync(path.join(root, 'public/assets/app.css'), 'utf8');
const appSource = fs.readFileSync(path.join(root, 'public/assets/app.js'), 'utf8');
const hero = fs.readFileSync(path.join(root, 'public/assets/hero-fitness-v2.png'));
const outputDir = path.resolve(root, '../../tmp/qa-php');
fs.mkdirSync(outputDir, { recursive: true });

const me = {
    user_id: 1,
    name: '示範會員',
    email: 'demo@fittrack.local',
    gender: 'Other',
    age: 25,
    height_cm: '170.00',
    training_experience: 'Beginner',
    training_goal_id: 1,
    training_days_per_week: 4,
    training_duration_minutes: 60,
    goal_name: 'Muscle Gain',
    is_admin: 0,
    current_weight_kg: '68.40',
    profile_complete: true,
    preferred_body_parts: [
        { body_part_id: 1, body_part_name: 'Chest', priority: 1 },
        { body_part_id: 2, body_part_name: 'Back', priority: 2 },
        { body_part_id: 6, body_part_name: 'Legs', priority: 3 },
    ],
};

const reference = {
    training_goals: [
        { training_goal_id: 1, goal_name: 'Muscle Gain' },
        { training_goal_id: 2, goal_name: 'Fat Loss' },
        { training_goal_id: 3, goal_name: 'Strength' },
        { training_goal_id: 4, goal_name: 'General Fitness' },
    ],
    body_parts: ['Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps', 'Legs', 'Glutes', 'Core']
        .map((body_part_name, index) => ({ body_part_id: index + 1, body_part_name })),
};

const exercises = [
    ['Barbell Bench Press #0025', 'Chest', 'Barbell', 1],
    ['Dumbbell Incline Bench Press #0289', 'Chest', 'Dumbbell', 2],
    ['Cable Chest Press #0170', 'Chest', 'Cable', 3],
    ['Triceps Pushdown #0595', 'Triceps', 'Cable', 4],
    ['Overhead Triceps Extension #1332', 'Triceps', 'Dumbbell', 5],
].map(([exercise_name, body_part_name, equipment, exercise_id], index) => ({
    plan_exercise_id: exercise_id,
    exercise_id,
    exercise_order: index + 1,
    exercise_name,
    body_part_name,
    equipment,
    description: '保持核心穩定，以可控制的速度完成動作，避免使用慣性。',
    image_url: '/assets/hero-fitness-v2.png',
    target_sets: 3,
    target_reps: 10,
    rest_seconds: 60,
}));

const plan = {
    workout_plan_id: 1,
    plan_name: '4 天增肌訓練計畫',
    experience_snapshot: 'Beginner',
    goal_name: 'Muscle Gain',
    duration_minutes: 60,
    created_at: '2026-10-05T08:00:00Z',
    days: [
        { plan_day_id: 1, day_number: 1, day_title: '第 1 天：胸 + 三頭', exercises },
        { plan_day_id: 2, day_number: 2, day_title: '第 2 天：背 + 二頭', exercises },
        { plan_day_id: 3, day_number: 3, day_title: '第 3 天：腿 + 臀', exercises },
        { plan_day_id: 4, day_number: 4, day_title: '第 4 天：肩 + 核心', exercises },
    ],
};

const dashboard = {
    session_count: 4,
    set_count: 36,
    total_volume: 12480,
    latest_weight: 68.4,
    favorite_body_part: 'Chest',
    favorite_exercise: 'Bench Press',
    volume_by_week: [
        { week: '2026-W37', volume: 4200 },
        { week: '2026-W38', volume: 7800 },
        { week: '2026-W39', volume: 10200 },
        { week: '2026-W40', volume: 12480 },
    ],
    weight_history: [
        { date: '2026-09-01', weight: 70.1 },
        { date: '2026-09-15', weight: 69.6 },
        { date: '2026-09-29', weight: 69.0 },
        { date: '2026-10-05', weight: 68.4 },
    ],
    recent_workouts: [
        { workout_session_id: 1, status: 'completed', started_at: '2026-10-05T08:00:00Z', day_title: '第 1 天：胸 + 三頭', set_count: 10, total_volume: 4320 },
        { workout_session_id: 2, status: 'completed', started_at: '2026-10-03T08:00:00Z', day_title: '第 2 天：背 + 二頭', set_count: 9, total_volume: 3580 },
    ],
};

const workout = {
    workout_session_id: 7,
    status: 'in_progress',
    started_at: '2026-10-05T09:20:00Z',
    plan_day_id: 1,
    day_title: '第 1 天：胸 + 三頭',
    plan_name: '4 天增肌訓練計畫',
    exercises: exercises.slice(0, 3),
    sets: [
        { workout_set_id: 1, exercise_id: 1, set_number: 1, weight_kg: '60.00', reps: 12 },
        { workout_set_id: 2, exercise_id: 1, set_number: 2, weight_kg: '65.00', reps: 10 },
    ],
};

function mock(pathname) {
    if (pathname === '/api/me') return me;
    if (pathname === '/api/reference') return reference;
    if (pathname === '/api/dashboard') return dashboard;
    if (pathname === '/api/plans') return { items: [plan] };
    if (pathname === '/api/workout-sessions/current') return workout;
    if (pathname === '/api/workout-sessions') return { items: dashboard.recent_workouts };
    if (pathname === '/api/body-records') return { items: [] };
    if (pathname.startsWith('/api/exercises')) return { items: exercises, total: exercises.length };
    return {};
}

function html(script) {
    return `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><base href="http://fittrack.local/"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body><div id="app"><header class="site-header" id="site-header"></header><main id="main-content"></main><footer class="site-footer"><span>FitTrack Pro</span><span>Exercise media © Gym visual</span><span>POSTGRESQL</span></footer></div><div id="toast-region" class="toast-region"></div><script>${script}</script></body></html>`;
}

const offlineMocks = {
    '/api/me': me,
    '/api/reference': reference,
    '/api/dashboard': dashboard,
    '/api/plans': { items: [plan] },
    '/api/workout-sessions/current': workout,
    '/api/workout-sessions': { items: dashboard.recent_workouts },
    '/api/body-records': { items: [] },
    '/api/exercises': { items: exercises, total: exercises.length },
};
const heroDataUrl = `data:image/png;base64,${hero.toString('base64')}`;

function offlineScript(route, authenticated) {
    const fetchMock = `
        window.__FITTRACK_QA_TOKEN__ = ${authenticated ? "'qa-token'" : 'null'};
        const __offlineMocks = ${JSON.stringify(offlineMocks)};
        window.fetch = async (input) => {
            const url = new URL(String(input), 'http://fittrack.local');
            const key = url.pathname.startsWith('/api/exercises') ? '/api/exercises' : url.pathname;
            const payload = __offlineMocks[key] ?? {};
            return { ok: true, status: 200, json: async () => payload };
        };
        location.hash = '#${route}';
    `;
    let source = appSource;
    source = source.replaceAll('/assets/hero-fitness-v2.png', heroDataUrl);
    return fetchMock + source;
}

for (const [name, route, authenticated] of [
    ['landing-desktop', 'home', false],
    ['dashboard-desktop', 'dashboard', true],
    ['plans-desktop', 'plans', true],
    ['workout-mobile', 'workout', true],
]) {
    fs.writeFileSync(path.join(outputDir, `${name}.html`), html(offlineScript(route, authenticated)));
}

let browser;
try {
    browser = await chromium.launch({ headless: true });
} catch (error) {
    console.log(`Playwright browser unavailable; offline fixtures written to ${outputDir}`);
    process.exit(0);
}

async function capture(name, route, viewport, authenticated) {
    const page = await browser.newPage({ viewportSize: viewport, deviceScaleFactor: 1 });
    await page.route('**/assets/hero-fitness-v2.png', (request) => request.fulfill({
        status: 200,
        body: hero,
        contentType: 'image/png',
    }));
    await page.route('**/api/**', (request) => request.fulfill({
        status: 200,
        body: JSON.stringify(mock(new URL(request.request().url()).pathname)),
        contentType: 'application/json',
    }));
    if (route) {
        await page.addInitScript((hash) => { location.hash = hash; }, `#${route}`);
    }
    const script = authenticated
        ? `window.__FITTRACK_QA_TOKEN__ = 'qa-token';\n${appSource}`
        : appSource;
    await page.setContent(html(script), { waitUntil: 'networkidle' });
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outputDir, `${name}.png`), fullPage: true });
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    if (bodyWidth > viewport.width) {
        throw new Error(`${name} overflows horizontally: ${bodyWidth}px > ${viewport.width}px`);
    }
    await page.close();
}

await capture('landing-desktop', 'home', { width: 1440, height: 900 }, false);
await capture('dashboard-desktop', 'dashboard', { width: 1440, height: 1024 }, true);
await capture('plans-desktop', 'plans', { width: 1440, height: 1024 }, true);
await capture('workout-mobile', 'workout', { width: 390, height: 844 }, true);

await browser.close();
console.log(`Visual screenshots written to ${outputDir}`);
