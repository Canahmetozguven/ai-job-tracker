# Theme Audit & Fix — 2026-04-27

## Context
RehberlikOS has inconsistent dark/light mode handling. Some components use `gray-*`/`blue-*` tokens without dark variants, others hardcode blue inline styles, and `GemSlider.module.css` uses `prefers-color-scheme` media query instead of the app's `.dark` class. The brand palette is defined but not used consistently.

## Principles
1. **Brand palette only** — Replace `blue-*` (except brand-blue SVG assets) and `gray-*` with `brand-*` equivalents
2. **Dark mode required** — Every component gets explicit `dark:` variants
3. **Class-based dark mode** — CSS modules must use `.dark` class selectors, not `prefers-color-scheme`
4. **CSS variables for dynamic inline colors** — Inline `style={}` props should reference CSS variables

## Files & Changes

### 1. `components/ui/ScoreBar.tsx`
- `text-gray-400` → `text-brand-400 dark:text-brand-300`
- `bg-gray-100` → `bg-brand-100 dark:bg-brand-900`

### 2. `components/messaging/ThreadList.tsx`
- `bg-blue-100 text-blue-700` → `bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300`
- (unread badge)

### 3. `components/ui/LoadingSpinner.tsx`
- Blue border color → `border-brand-500 dark:border-brand-400`
- `text-gray-500` → `text-brand-500 dark:text-brand-400`

### 4. `components/auth/PasswordInput.tsx`
- `focus:ring-blue-500` → `focus:ring-brand-500`

### 5. `components/auth/GoogleSignInButton.tsx`
- `focus:ring-blue-500` → `focus:ring-brand-500`
- Google SVG logo fills: keep as-is (external brand)

### 6. `components/career/HollandAssessmentWizard.tsx`
- All `blue-*` → `brand-*` with dark variants on progress bar and buttons

### 7. `components/ui/Header.tsx`
- Role color `bg-blue-*`/`text-blue-*` → `bg-brand-*`/`text-brand-*` with dark variants

### 8. `components/ui/MobileNav.tsx`
- Active state `text-blue-600` → `text-brand-600 dark:text-brand-400`

### 9. `components/analytics/AdminAnalyticsClient.tsx`
- Inline `backgroundColor: rgba(37, 99, 235, ...)` → CSS variable or Tailwind class

### 10. `components/calendar/AppointmentCalendar.tsx`
- Inline status colors → Tailwind classes with dark variants
- Calendar event text forced white → `text-white dark:text-gray-100`

### 11. `components/checkin/GemSlider.module.css`
- Remove `@media (prefers-color-scheme: dark)` block
- Add `.dark` class wrapper around dark styles: `.dark .gem-slider { ... }`

### 12. `components/ThemeToggle.tsx`
- System preference check: current implementation acceptable (uses `prefers-color-scheme` only as fallback), no change needed

### 13. `app/layout.tsx`
- Initial theme bootstrap script: current implementation acceptable, no change needed

### 14. `app/globals.css`
- Review `--background` / `--foreground` CSS variables are defined for both `:root` and `.dark`
- Ensure they map to `brand` palette

## Verification
- `npm run lint --filter=@rehberlik/web -- --fix`
- `npx playwright test e2e/navigation/dark-mode-mobile-smoke.spec.ts`
