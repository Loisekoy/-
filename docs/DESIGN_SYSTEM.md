# Fitness Tracking Management System — UI Specification

## Concept references

- `design/onboarding-concept.png`
- `design/plan-concept.png`
- `design/dashboard-concept.png`
- `design/active-workout-mobile-concept.png`

The generated concepts are layout and visual references. Their inconsistent generated brand marks are not accepted copy. The canonical product name is **Fitness Tracking Management System**; the compact app-shell label is **Fitness Tracker**.

## Design direction

- Athletic editorial rather than a decorative fitness marketing site.
- True white primary background with pale cool-gray secondary regions.
- Near-black navy type and rules, vivid lime for the primary action/selection, cobalt for focus and data lines.
- Open layouts, tables, rails, and dividers instead of a grid of rounded cards.
- Strong numeric typography for metrics and workout inputs.
- No gradients, glassmorphism, photographs, decorative illustrations, or login controls.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--color-bg` | `#ffffff` | Main background |
| `--color-surface` | `#f6f8fb` | Secondary surface |
| `--color-ink` | `#07142e` | Main text and icons |
| `--color-muted` | `#60708b` | Secondary text |
| `--color-line` | `#dce3ec` | Dividers and field borders |
| `--color-lime` | `#b8f52f` | Primary CTA and selected state |
| `--color-cobalt` | `#1769ff` | Focus and chart series |
| `--color-danger` | `#d84941` | Validation errors |
| `--radius-control` | `10px` | Inputs and buttons |
| `--radius-panel` | `14px` | The one main onboarding frame |
| `--shadow-focus` | `0 0 0 3px rgb(23 105 255 / 16%)` | Keyboard focus |

Spacing follows a 4px base scale with primary gaps at 8, 12, 16, 24, 32, 48, and 64px.

## Typography

- UI font: `Inter`, `Noto Sans TC`, system sans-serif fallback.
- Display: 40–56px desktop, 32–40px mobile; 750–800 weight.
- Page heading: 32–40px desktop, 28–32px mobile; 750 weight.
- Section heading: 22–28px; 700 weight.
- Body: 16px, 1.6 line height.
- Controls: 15–16px, 600 weight; never browser-default typography.
- Metrics: tabular numerals, 48–72px desktop.

## Component families

- `AppHeader`: quiet brand, essential navigation, active lime rule.
- `OnboardingProgress`: five-step desktop rail and compact mobile progress.
- `Field`, `SelectField`, `ChoiceGroup`: consistent label, help, error, focus state.
- `PrimaryButton`, `SecondaryButton`, `TextButton`: minimum 44px tap target.
- `DayRail`: selected lime block on desktop, horizontal scroller on mobile.
- `ExerciseTable`: open row layout, editable target cells, content visibility for long lists.
- `MetricStrip`: one horizontal data band, not separate floating cards.
- `ChartPanel`: open chart region with a heading, range control, axes, and tooltip.
- `HistoryTable`: responsive desktop table that becomes a labeled list on mobile.
- `SetRow`: large numeric inputs, clear completed/current state, one-thumb-friendly.

## Responsive rules

- Desktop content max width: 1440px with 24–40px page gutters.
- At 900px, app navigation becomes a compact horizontal scroll or menu.
- At 760px, onboarding rail becomes a top progress bar and two-column fields stack.
- Plan day rail becomes a horizontal selector; exercise tables become labeled rows.
- Dashboard metrics wrap into two columns and then one; charts remain scroll-free.
- Active workout uses a dedicated mobile-first page with a sticky bottom action zone.

## Motion and accessibility

- 160–220ms color/border/transform transitions only where state changes.
- Respect `prefers-reduced-motion`.
- Visible keyboard focus on every interactive element.
- Semantic labels and error associations for every form field.
- Do not use color alone for selected, completed, or error states.

## Allowed first-viewport copy

- Fitness Tracking Management System / Fitness Tracker
- 開始建立我的健身計畫
- Step 1 / 5
- 基本資料
- 名字
- 性別（選填）
- 年齡
- 身高
- 體重
- 訓練經驗
- 下一步：選擇健身目標

No Login, Register, Sign In, Sign Up, eyebrow, badge, promotional claim, or unrelated metric may be added.
