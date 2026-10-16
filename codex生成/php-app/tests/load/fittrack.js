import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import exec from 'k6/execution';

const fixture = JSON.parse(open(__ENV.USERS_FILE || '/data/users.json'));
const baseUrl = __ENV.BASE_URL || 'http://127.0.0.1';
const readLatency = new Trend('fittrack_read_latency', true);
const setLatency = new Trend('fittrack_set_latency', true);
const planLatency = new Trend('fittrack_plan_latency', true);
const unexpectedFailure = new Rate('fittrack_unexpected_failure');

export const options = {
  scenarios: {
    warmup: {
      executor: 'constant-vus',
      exec: 'warmup',
      vus: 20,
      duration: '60s',
    },
    acceptance: {
      executor: 'ramping-vus',
      exec: 'acceptance',
      startTime: '60s',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 200 },
        { duration: '5m', target: 200 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    fittrack_read_latency: ['p(95)<500'],
    fittrack_set_latency: ['p(95)<1000'],
    fittrack_plan_latency: ['p(95)<3000'],
    fittrack_unexpected_failure: ['rate<0.01'],
  },
};

function identity() {
  return fixture.load_users[(exec.vu.idInTest - 1) % fixture.load_users.length];
}

function login(user) {
  const response = http.post(`${baseUrl}/api/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password,
  }), {
    headers: { 'Content-Type': 'application/json', Origin: baseUrl },
    tags: { operation: 'login' },
  });
  const ok = check(response, { 'login returns 200': (result) => result.status === 200 });
  if (!ok) unexpectedFailure.add(true);
}

function csrfHeaders() {
  const cookies = http.cookieJar().cookiesForURL(baseUrl);
  const token = cookies.fittrack_csrf?.[0] || '';
  return {
    'Content-Type': 'application/json',
    Origin: baseUrl,
    'X-CSRF-Token': token,
  };
}

export function warmup() {
  const user = identity();
  if (exec.vu.iterationInScenario === 0) login(user);
  http.get(`${baseUrl}/api/dashboard`, { tags: { operation: 'warmup' } });
  sleep(1);
}

export function acceptance() {
  const user = identity();
  if (exec.vu.iterationInScenario === 0) login(user);
  const choice = Math.random();
  let response;
  let valid;
  if (choice < 0.70) {
    response = http.get(`${baseUrl}/api/dashboard`, { tags: { operation: 'read' } });
    readLatency.add(response.timings.duration);
    valid = check(response, { 'read succeeds': (result) => result.status === 200 });
  } else if (choice < 0.90) {
    response = http.post(
      `${baseUrl}/api/workout-sessions/${user.workout_session_id}/sets`,
      JSON.stringify({
        workout_session_exercise_id: user.workout_session_exercise_id,
        set_number: 1 + (exec.vu.iterationInScenario % 100),
        weight_kg: 40,
        reps: 10,
      }),
      { headers: csrfHeaders(), tags: { operation: 'save_set' } },
    );
    setLatency.add(response.timings.duration);
    valid = check(response, { 'set save is created or idempotent': (result) => [200, 201].includes(result.status) });
  } else {
    response = http.post(
      `${baseUrl}/api/plans/generate`,
      JSON.stringify({ plan_name: `Load ${exec.vu.idInTest}-${exec.vu.iterationInScenario}` }),
      { headers: csrfHeaders(), tags: { operation: 'generate_plan' } },
    );
    planLatency.add(response.timings.duration);
    valid = check(response, { 'plan generation succeeds': (result) => result.status === 201 });
  }
  unexpectedFailure.add(!valid);
  sleep(1);
}
