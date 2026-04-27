# Theme Audit & Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit and fix all theme inconsistencies across the RehberlikOS web app — replacing gray/blue tokens with brand palette, adding dark variants, and fixing CSS modules to use `.dark` class instead of `prefers-color-scheme`.

**Architecture:** Replace hardcoded `gray-*`/`blue-*` Tailwind classes with `brand-*` equivalents, add explicit `dark:` variants to every affected component, fix CSS modules to use class-based dark mode. No architectural changes.

**Tech Stack:** Tailwind CSS (brand palette), CSS Modules, class-based dark mode via `.dark` on `<html>`.

---

## File Map

| File | Changes |
|------|---------|
| `apps/web/components/ui/ScoreBar.tsx` | Replace gray-* → brand-* + dark: |
| `apps/web/components/messaging/ThreadList.tsx` | Replace blue-* badge → brand-* + dark: |
| `apps/web/components/ui/LoadingSpinner.tsx` | Replace blue/gray → brand-* + dark: |
| `apps/web/components/auth/PasswordInput.tsx` | Replace focus:ring-blue-500 → brand-500 |
| `apps/web/components/auth/GoogleSignInButton.tsx` | Replace focus:ring-blue-500 → brand-500 |
| `apps/web/components/career/HollandAssessmentWizard.tsx` | Replace blue-* → brand-* + dark: |
| `apps/web/components/ui/Header.tsx` | Replace role blue-* → brand-* + dark: |
| `apps/web/components/ui/MobileNav.tsx` | Replace text-blue-600 → brand-600 + dark: |
| `apps/web/components/analytics/AdminAnalyticsClient.tsx` | Replace inline rgba blue → CSS var |
| `apps/web/components/calendar/AppointmentCalendar.tsx` | Replace inline colors → Tailwind + dark: |
| `apps/web/components/checkin/GemSlider.module.css` | Replace prefers-color-scheme → .dark class |

---

## Tasks

### Task 1: ScoreBar.tsx

**Files:**
- Modify: `apps/web/components/ui/ScoreBar.tsx:26,40`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/ui/ScoreBar.tsx`

- [ ] **Step 2: Replace gray-* with brand-* + dark: variants**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/ui/ScoreBar.tsx
git commit -m "fix(theme): use brand palette in ScoreBar"
```

---

### Task 2: ThreadList.tsx

**Files:**
- Modify: `apps/web/components/messaging/ThreadList.tsx:69`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/messaging/ThreadList.tsx`

- [ ] **Step 2: Replace blue-* badge with brand-* + dark: variants**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/messaging/ThreadList.tsx
git commit -m "fix(theme): use brand palette in ThreadList"
```

---

### Task 3: LoadingSpinner.tsx

**Files:**
- Modify: `apps/web/components/ui/LoadingSpinner.tsx:23,29`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/ui/LoadingSpinner.tsx`

- [ ] **Step 2: Replace blue border with brand-500 and gray text with brand-500, add dark: variants**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/ui/LoadingSpinner.tsx
git commit -m "fix(theme): use brand palette in LoadingSpinner"
```

---

### Task 4: PasswordInput.tsx

**Files:**
- Modify: `apps/web/components/auth/PasswordInput.tsx:44`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/auth/PasswordInput.tsx`

- [ ] **Step 2: Replace focus:ring-blue-500 with focus:ring-brand-500**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/auth/PasswordInput.tsx
git commit -m "fix(theme): use brand focus ring in PasswordInput"
```

---

### Task 5: GoogleSignInButton.tsx

**Files:**
- Modify: `apps/web/components/auth/GoogleSignInButton.tsx:22,27-30`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/auth/GoogleSignInButton.tsx`

- [ ] **Step 2: Replace focus:ring-blue-500 with focus:ring-brand-500**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/auth/GoogleSignInButton.tsx
git commit -m "fix(theme): use brand focus ring in GoogleSignInButton"
```

---

### Task 6: HollandAssessmentWizard.tsx

**Files:**
- Modify: `apps/web/components/career/HollandAssessmentWizard.tsx:114,141,176,185`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/career/HollandAssessmentWizard.tsx`

- [ ] **Step 2: Replace all blue-* classes with brand-* + dark: variants on progress bar and buttons**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/career/HollandAssessmentWizard.tsx
git commit -m "fix(theme): use brand palette in HollandAssessmentWizard"
```

---

### Task 7: Header.tsx

**Files:**
- Modify: `apps/web/components/ui/Header.tsx:59-61`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/ui/Header.tsx`

- [ ] **Step 2: Replace role bg-blue-*/text-blue-* with brand-* + dark: variants**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/ui/Header.tsx
git commit -m "fix(theme): use brand palette in Header"
```

---

### Task 8: MobileNav.tsx

**Files:**
- Modify: `apps/web/components/ui/MobileNav.tsx:45`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/ui/MobileNav.tsx`

- [ ] **Step 2: Replace text-blue-600 active state with text-brand-600 dark:text-brand-400**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/ui/MobileNav.tsx
git commit -m "fix(theme): use brand palette in MobileNav"
```

---

### Task 9: AdminAnalyticsClient.tsx

**Files:**
- Modify: `apps/web/components/analytics/AdminAnalyticsClient.tsx:85`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/analytics/AdminAnalyticsClient.tsx`

- [ ] **Step 2: Replace inline rgba(37, 99, 235) with a CSS variable or Tailwind class using brand palette**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/analytics/AdminAnalyticsClient.tsx
git commit -m "fix(theme): use brand palette in AdminAnalyticsClient"
```

---

### Task 10: AppointmentCalendar.tsx

**Files:**
- Modify: `apps/web/components/calendar/AppointmentCalendar.tsx:151-152,186`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/calendar/AppointmentCalendar.tsx`

- [ ] **Step 2: Replace inline status colors with Tailwind classes + dark: variants; remove forced white text or make it respect dark mode**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/calendar/AppointmentCalendar.tsx
git commit -m "fix(theme): use brand palette in AppointmentCalendar"
```

---

### Task 11: GemSlider.module.css

**Files:**
- Modify: `apps/web/components/checkin/GemSlider.module.css:89-107`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/components/checkin/GemSlider.module.css`

- [ ] **Step 2: Replace @media (prefers-color-scheme: dark) block with .dark .gem-slider { ... } selector**

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/checkin/GemSlider.module.css
git commit -m "fix(theme): use .dark class in GemSlider CSS module"
```

---

### Task 12: globals.css — Review CSS variables

**Files:**
- Modify: `apps/web/app/globals.css:7-29,37-55,157-179`

- [ ] **Step 1: Read the file**

Run: `Read apps/web/app/globals.css`

- [ ] **Step 2: Ensure --background and --foreground CSS variables are defined for both :root and .dark, mapping to brand palette**

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/globals.css
git commit -m "fix(theme): ensure CSS variables in globals.css cover both themes"
```

---

### Task 13: Final lint

**Files:**
- None (verification only)

- [ ] **Step 1: Run lint fix**

Run: `npm run lint --filter=@rehberlik/web -- --fix`

- [ ] **Step 2: Run dark mode e2e test**

Run: `npx playwright test e2e/navigation/dark-mode-mobile-smoke.spec.ts`

- [ ] **Step 3: Commit any remaining changes**

---

## Self-Review Checklist
- [ ] All 12 files from spec are covered
- [ ] No `blue-*` or `gray-*` remain in affected components (except SVG brand logos)
- [ ] Every component has dark: variants
- [ ] CSS module uses `.dark` class selector
- [ ] No placeholders or TODOs in code
