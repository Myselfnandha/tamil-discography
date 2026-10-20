---
description: Plan and implement modern, responsive, and aesthetic UI/UX interfaces with curated palettes, typography, and accessibility.
---

# /design-ui — Modern UI/UX Design & Implementation

Comprehensive architectural guide and design system generator for web and mobile interfaces. Prioritizes premium visual aesthetics, clean typography, responsive layouts, and WCAG AA accessibility standards.

---

## 🎨 Design Philosophy & Core Aesthetics

1. **Rich Aesthetics**: Avoid generic, plain colors and purple gradients. Use curated, harmonious color palettes (tailored dark modes, sleek neutrals with vibrant accents).
2. **Modern Typography**: Use clean, modern typefaces (Google Fonts: Inter, Outfit, Plus Jakarta Sans, DM Sans) instead of browser defaults.
3. **Dynamic & Responsive**: Implement fluid micro-animations (150–250ms), hover states, active transitions, and responsive grid/flexbox layouts.
4. **Touch & Ergonomics**: Ensure minimum 48dp touch targets on interactive mobile elements, with clear focus rings for accessibility.

---

## 📐 The 4-Step UI Implementation Workflow

### Step 1: Requirements & Theme Analysis
Identify key product parameters:
- **Product Type**: Dashboard, SaaS landing, mobile app, e-commerce, portfolio, tool.
- **Visual Personality**: Sleek dark-mode, clean editorial, high-density data, vibrant modern.
- **Target Tech Stack**: React/Next.js, Tailwind CSS, Vanilla HTML/CSS, Flutter, Vue.

### Step 2: Establish the Design System Tokens
Before writing components, define the unified CSS custom properties or theme tokens:

```css
:root {
  /* Curated Dark Palette (Midnight Slate) */
  --bg-primary: #0b0f19;
  --bg-secondary: #111827;
  --bg-card: rgba(17, 24, 39, 0.7);
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-focus: #3b82f6;

  /* Typography */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-heading: 'Outfit', sans-serif;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  /* Accents */
  --accent-cyan: #06b6d4;
  --accent-emerald: #10b981;
  --accent-amber: #f59e0b;

  /* Glassmorphism & Elevation */
  --glass-blur: blur(12px);
  --shadow-elevation: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

### Step 3: Component Assembly & Layout
- **Container Structure**: Consistent max-width container (`max-w-6xl` or `max-w-7xl`) centered with padding (`px-4 sm:px-6 lg:px-8`).
- **Floating Navbars**: Top floating navigation bar with subtle blur backdrop and clear border separation.
- **Card Grids**: Auto-fit CSS Grid (`repeat(auto-fit, minmax(280px, 1fr))`) with hover border-color transitions.
- **Forms & Inputs**: High-contrast labels, explicit placeholder styling, custom focus outline with offset.

### Step 4: Verification & Polish
- Ensure all interactive elements have `cursor: pointer`.
- Test contrast ratio: Text to background must achieve at least 4.5:1 for standard text.
- Verify mobile responsiveness at 375px, 768px, and 1280px breakpoints.
- Remove all default browser focus outlines without replacing them; replace with custom accessible rings.

---

## 🛡️ Common Anti-Patterns to Avoid

| Anti-Pattern | Correct Approach |
|:---|:---|
| Using emojis as UI icons (`🚀`, `⚙️`) | Use SVG icon sets (Lucide, Heroicons, Feather) |
| Purple gradient cliches | Curated slate/neutral tones with emerald/cyan/amber accents |
| Layout-shifting hover states (`scale-105`) | Subtle border glow, shadow transition, or background opacity shifts |
| Inaccessible low-contrast text | Ensure minimum `#94A3B8` on dark backgrounds |
| Hardcoded element widths (`width: 400px`) | Fluid responsive sizing (`width: 100%; max-width: 400px`) |