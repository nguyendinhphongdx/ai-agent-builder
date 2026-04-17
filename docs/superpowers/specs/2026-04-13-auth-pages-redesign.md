# Auth Pages Redesign — Login & Register

## Goal

Redesign login and register pages from basic centered card to a polished split-screen layout with branding illustration.

## Layout

**Split screen** — left panel for branding, right panel for form.

```
>=1024px:
┌─────────────────┬─────────────────┐
│  Brand Panel    │   Form Panel    │
│  (50%)          │   (50%)         │
└─────────────────┴─────────────────┘

<1024px:
┌───────────────────────────────────┐
│  Logo (compact)                   │
│  Form Panel (full width)          │
└───────────────────────────────────┘
```

## Brand Panel (Left)

- **Background**: Light/white with brand color accents
- **Logo**: "AgentForge" text + Bot icon at top
- **Tagline**: "Build AI agents that work." or similar
- **Illustration**: SVG combining:
  - AI robot/assistant character (center)
  - Workflow nodes connected by lines (surrounding)
  - Data flow paths between nodes
  - Built with CSS + inline SVG (no external assets)
- **Feature highlights** at bottom: 2-3 short items with icons
  - e.g. "Visual Workflows", "Knowledge Base", "Multi-Agent"
- Sticky/fixed — does not scroll with form

## Form Panel (Right)

- **Background**: White (light mode) / dark surface (dark mode)
- **Vertically centered** form content
- **Max-width**: ~400px within the panel

### Login Form
- Heading: "Welcome back"
- Fields: Email, Password (with show/hide toggle)
- Error message inline (red text below form)
- "Sign in" button — full width, primary color
- Footer: "Don't have an account? Sign up" link

### Register Form
- Heading: "Create your account"
- Fields: Full Name, Email, Password (with show/hide toggle)
- Error message inline
- "Create account" button — full width, primary color
- Footer: "Already have an account? Sign in" link

### Future-ready
- Space for "or" divider + OAuth buttons (Google, GitHub)
- Not implemented now, just layout-ready

## Responsive Behavior

| Breakpoint | Behavior |
|---|---|
| `>=1024px` | Split 50/50, both panels visible |
| `<1024px` | Brand panel hidden, form full-width with compact logo above |

## Component Structure

```
features/auth/
├── components/
│   ├── AuthLayout.tsx      ← NEW: shared split-screen layout
│   ├── BrandPanel.tsx      ← NEW: branding + SVG illustration
│   ├── LoginForm.tsx       ← KEEP: form logic unchanged
│   └── RegisterForm.tsx    ← KEEP: form logic unchanged
└── views/
    ├── LoginView.tsx       ← REWRITE: use AuthLayout
    └── RegisterView.tsx    ← REWRITE: use AuthLayout
```

## Color & Style

- Brand panel: light background, brand color accents (primary from theme)
- Form panel: white/card background
- Illustration: brand primary + muted secondary colors
- Follow existing shadcn/ui theme tokens (--primary, --muted, etc.)
- Dark mode support via existing theme system

## What NOT to change

- Form validation logic (zod schemas)
- Auth hooks (useLogin, useRegister)
- Auth service layer
- Route structure (/login, /register)
