# 3D Print Calc Pro — Design System & Visual Architecture (DESIGN_DNA.md)

> **Document Classification**: Master Production Reference & Developer Specification  
> **Repository Target**: `c:\Users\Vitor\Documents\antigravity\splendid-hypatia`  
> **Architecture**: Dark Mode SaaS Premium (Obsidian Canvas, Layered Slates, Royal Blue, Emerald, Violet)  
> **Status**: Verified & Authoritative — Aligned with Production Codebase  
> **Target Audience**: Full-Stack Developers, Frontend Engineers, UI/UX Designers, and Maintainers  

---

## Table of Contents

1. [Executive Architecture & Styling Methodology](#1-executive-architecture--styling-methodology)
   - [1.1 Runtime Environment & Serving Architecture](#11-runtime-environment--serving-architecture)
   - [1.2 The Hybrid Dual-Layer Styling System](#12-the-hybrid-dual-layer-styling-system)
   - [1.3 Stylesheet Import Cascade & Specificity Order](#13-stylesheet-import-cascade--specificity-order)
   - [1.4 Global Resets, Box-Sizing & Viewport Normalization](#14-global-resets-box-sizing--viewport-normalization)
2. [Complete Color Palette & Token Taxonomy](#2-complete-color-palette--token-taxonomy)
   - [2.1 Canvas, Surface Elevation & Container Palette](#21-canvas-surface-elevation--container-palette)
   - [2.2 Backward Compatibility & Legacy Aliases](#22-backward-compatibility--legacy-aliases)
   - [2.3 Brand Royal Blue Series (Primary Accent & CTAs)](#23-brand-royal-blue-series-primary-accent--ctas)
   - [2.4 Emerald Series (Profits, Approved Quotes & Success)](#24-emerald-series-profits-approved-quotes--success)
   - [2.5 Royal Violet Series (Hardware & Technical Specs)](#25-royal-violet-series-hardware--technical-specs)
   - [2.6 Amber Series (Warnings, Filament Stock & In Production)](#26-amber-series-warnings-filament-stock--in-production)
   - [2.7 Rose Series (Scrap Errors, Alerts & Cancelled Quotes)](#27-rose-series-scrap-errors-alerts--cancelled-quotes)
   - [2.8 Text & Foreground Hierarchy](#28-text--foreground-hierarchy)
   - [2.9 Borders, Dividers & Hairlines](#29-borders-dividers--hairlines)
   - [2.10 Project Status Badges Color Contract](#210-project-status-badges-color-contract)
   - [2.11 Material Badges Color Contract](#211-material-badges-color-contract)
   - [2.12 Chart.js & Analytics Data Visualization Colors](#212-chartjs--analytics-data-visualization-colors)
   - [2.13 High-Fidelity Paper Print Stylesheet (@media print)](#213-high-fidelity-paper-print-stylesheet-media-print)
   - [2.14 Timing, Easings & Interactive Transitions Tokens](#214-timing-easings--interactive-transitions-tokens)
3. [Typography & Font Engineering](#3-typography--font-engineering)
   - [3.1 Font Family Stacks & CDN Imports](#31-font-family-stacks--cdn-imports)
   - [3.2 Tabular Numbers & Numeric Precision Features](#32-tabular-numbers--numeric-precision-features)
   - [3.3 Complete Typographic Scale Hierarchy (9px to 36px)](#33-complete-typographic-scale-hierarchy-9px-to-36px)
   - [3.4 Font Weights & Tracking / Letter-Spacing Values](#34-font-weights--tracking--letter-spacing-values)
4. [Spacing, Dimensions & Layout Conventions](#4-spacing-dimensions--layout-conventions)
   - [4.1 Layout Shell & Full Viewport Architecture](#41-layout-shell--full-viewport-architecture)
   - [4.2 Sidebar Navigation Geometry (Expanded & Collapsed)](#42-sidebar-navigation-geometry-expanded--collapsed)
   - [4.3 Sticky Topbar Header Dimensions](#43-sticky-topbar-header-dimensions)
   - [4.4 Sticky Financial Terminal Architecture & Scrolling](#44-sticky-financial-terminal-architecture--scrolling)
   - [4.5 Spacing Scale (Micro, Small, Medium, Large)](#45-spacing-scale-micro-small-medium-large)
   - [4.6 Grid & Flexbox Layout Configurations](#46-grid--flexbox-layout-configurations)
   - [4.7 CSS Subgrid Auto-Aligned Form Architecture](#47-css-subgrid-auto-aligned-form-architecture)
   - [4.8 Multi-Plate Hardware Grid Alignment](#48-multi-plate-hardware-grid-alignment)
   - [4.9 Responsive Breakpoints & Device Adaptation](#49-responsive-breakpoints--device-adaptation)
5. [Depth, Elevation, Shadows & Specialized Lighting](#5-depth-elevation-shadows--specialized-lighting)
   - [5.1 Elevation & Box-Shadows Scale](#51-elevation--box-shadows-scale)
   - [5.2 Ambient Halo Glows](#52-ambient-halo-glows)
   - [5.3 Physical Lighting Metaphor: Top Hairline Bevel (.card-dark::before)](#53-physical-lighting-metaphor-top-hairline-bevel-card-darkbefore)
   - [5.4 Dual-Accent Bevel (.summary-panel-card::before)](#54-dual-accent-bevel-summary-panel-cardbefore)
   - [5.5 Live Final Price Hero Halo & Neon Glow](#55-live-final-price-hero-halo--neon-glow)
   - [5.6 Net Profit Callout Pod Depth](#56-net-profit-callout-pod-depth)
   - [5.7 Border Radii System](#57-border-radii-system)
   - [5.8 Border Widths & Stroke Styles](#58-border-widths--stroke-styles)
   - [5.9 Motion Physics, Easings & Interactive Transition Curves](#59-motion-physics-easings--interactive-transition-curves)
6. [UI Components & Interactive States Directory](#6-ui-components--interactive-states-directory)
   - [6.1 Surface Archetypes & Containers](#61-surface-archetypes--containers)
   - [6.2 Buttons & Trigger Controls (Default, Hover, Active, Disabled)](#62-buttons--trigger-controls-default-hover-active-disabled)
   - [6.3 Form Controls (Inputs, Selects, Gradient Wraps, Pickers)](#63-form-controls-inputs-selects-gradient-wraps-pickers)
   - [6.4 Slicer File Dropzone Interactive States](#64-slicer-file-dropzone-interactive-states)
   - [6.5 Status & Material Badges Directory](#65-status--material-badges-directory)
   - [6.6 Modal Dialogs & Fullscreen Overlays](#66-modal-dialogs--fullscreen-overlays)
   - [6.7 Data Tables & Row Transitions](#67-data-tables--row-transitions)
   - [6.8 Toast Notifications & Micro-Indicators](#68-toast-notifications--micro-indicators)
   - [6.9 Keyframes & Micro-Interaction Animations](#69-keyframes--micro-interaction-animations)
   - [6.10 Catalog Cards, Cost Distribution & Production Failure Tracking](#610-catalog-cards-cost-distribution--production-failure-tracking)
7. [Developer Maintenance & Fine-Tuning Guide (Cheat Sheet)](#7-developer-maintenance--fine-tuning-guide-cheat-sheet)
   - [7.1 Recipe: How to Change the Primary Brand Accent Color](#71-recipe-how-to-change-the-primary-brand-accent-color)
   - [7.2 Recipe: How to Adjust Card Elevation, Background, or Rim Lighting](#72-recipe-how-to-adjust-card-elevation-background-or-rim-lighting)
   - [7.3 Recipe: How to Modify Typography or Add a New Font](#73-recipe-how-to-modify-typography-or-add-a-new-font)
   - [7.4 Recipe: How to Tune the Sticky Financial Terminal Dimensions](#74-recipe-how-to-tune-the-sticky-financial-terminal-dimensions)
   - [7.5 Recipe: How to Add or Tweak Status and Material Badges](#75-recipe-how-to-add-or-tweak-status-and-material-badges)
   - [7.6 Recipe: How to Add Form Fields into the Aligned Subgrid](#76-recipe-how-to-add-form-fields-into-the-aligned-subgrid)
   - [7.7 Recipe: How to Customize Print & PDF Layout Styles](#77-recipe-how-to-customize-print--pdf-layout-styles)
   - [7.8 Critical Contract Invariants & Protected Identifiers](#78-critical-contract-invariants--protected-identifiers)
   - [7.9 Architectural Precedence: Dual-Layer Specificity & Tailwind Utility Overrides](#79-architectural-precedence-dual-layer-specificity--tailwind-utility-overrides)

---

## 1. Executive Architecture & Styling Methodology

### 1.1 Runtime Environment & Serving Architecture
The frontend of **3D Print Calc Pro** is structured as a zero-bundler Single Page Application (SPA) served directly by a high-performance **FastAPI** backend (`Python 3.14`).

- **Serving Mount (`app.py:108`)**: The static root is mounted directly:
  ```python
  app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
  ```
- **Primary Routes**:
  - `GET /` &rarr; Serves `frontend/index.html` (`app.py:110-115`)
  - `GET /preview` &rarr; Serves `frontend/preview.html` (`app.py:117-119`)
  - `GET /{catchall:path}` &rarr; SPA client fallback to `frontend/index.html` (`app.py:121-134`)
- **Zero Build Tooling**: The application requires **no Node.js, Webpack, Vite, Rollup, or Babel**. Every visual adjustment in HTML or CSS is immediately live upon browser refresh.

### 1.2 The Hybrid Dual-Layer Styling System
The design system employs a synchronized hybrid architecture combining two complementary layers:

```
+-----------------------------------------------------------------------------------------+
|                                HYBRID DUAL-LAYER STYLING                                |
+------------------------------------------------------------+----------------------------+
| LAYER 1: Utility Engine (Tailwind CSS CDN)                 | LAYER 2: Modular CSS Cascade|
| - Loaded via https://cdn.tailwindcss.com                   | - Root tokens (:root)      |
| - Configured in <script> tailwind.config = { ... }         | - Base resets & typography |
| - Provides layout helpers (flex, grid, gap, space-y)       | - Component contracts      |
| - Handles responsive prefixes (sm:, md:, lg:)              | - Viewport & sticky shell  |
| - Defines semantic palette mirror (darkbg, brand, etc.)   | - Custom animations        |
+------------------------------------------------------------+----------------------------+
```

1. **Layer 1: Utility Engine (Tailwind CSS CDN)**:
   - Configured via an inline JavaScript object `tailwind.config` embedded in the `<head>` of `frontend/index.html:15-86` and `frontend/preview.html:14-85`.
   - Used throughout templates for responsive layouts (`grid-cols-1 lg:grid-cols-12`), flex alignment, and structural spacing.
2. **Layer 2: Modular CSS Cascade (Authoritative Design System)**:
   - Modular CSS stylesheets linked in document `<head>`: `<link rel="stylesheet" href="/static/css/styles.css?v=1.4.0">`, `<link rel="stylesheet" href="/static/css/components.css?v=1.4.0">`, and `<link rel="stylesheet" href="/static/css/views.css?v=1.4.0">` (`frontend/index.html:94-96`; standalone preview uses `/static/css/styles.css` at `frontend/preview.html:89`).
   - Governs visual tokens, physical rim lighting, glassmorphism filters, scrollbars, tabular numbers, and component states.
   - Component rules intentionally utilize `!important` flags where necessary to strictly override Tailwind CDN defaults and preserve the design system contract.

### 1.3 Stylesheet Import Cascade & Specificity Order
The entry point `frontend/css/styles.css` coordinates all stylesheet modules using strict sequential `@import` statements (`styles.css:13-17`):

```css
/* frontend/css/styles.css:13-17 */
@import url('./tokens.css');      /* 1. Master :root Design Tokens & Palette */
@import url('./base.css');        /* 2. Global Resets, Monospace Figures & Scrollbars */
@import url('./components.css');  /* 3. Reusable UI Components, Cards, Badges, Modals */
@import url('./views.css');       /* 4. Layout Shell, Sticky Terminal, View Grids */
@import url('./animations.css');  /* 5. Keyframes, Micro-Interactions & Reduced Motion */
```

#### Cascade Rule & Specificity Precedence:
1. `tokens.css`: Declares raw CSS custom properties on `:root`. Does not attach selectors.
2. `base.css`: Sets global tag resets (`body`, `headings`, `code`, `input[type="number"]`).
3. `components.css`: Styles atomic UI patterns (`.card-dark`, `.btn-primary`, `.badge-*`, `.dropzone`).
4. `views.css`: Defines layout view containers (`#app-layout`, `#app-sidebar`, `.summary-panel-card`, subgrids).
5. `animations.css`: Keyframes and motion utilities (`.animate-fade-in`, `.animate-pulse-glow`).
6. `styles.css:24-122`: Concludes with the `@media print` contract for physical quote documents.

### 1.4 Global Resets, Box-Sizing & Viewport Normalization
Defined in `frontend/css/base.css:10-172`:
- **Box Sizing**: `*, *::before, *::after { box-sizing: border-box; }` (`base.css:10-12`)
- **Smooth Scroll & HTML Defaults**: Defined globally across root, body, main layout, summary panel, and all overflow containers (`base.css:14-23`), with dark color scheme and font antialiasing on `html` (`base.css:25-30`):
  ```css
  /* base.css:14-30 */
  html,
  body,
  main,
  .summary-panel-body,
  .overflow-y-auto,
  .overflow-x-auto,
  [class*="overflow-y-auto"],
  [class*="overflow-x-auto"] {
      scroll-behavior: smooth;
  }

  html {
      color-scheme: dark;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
  }
  ```
- **Body Canvas**:
  ```css
  /* base.css:35-43 */
  body {
      background-color: var(--bg-app);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: var(--text-sm);
      line-height: 1.5;
      min-height: 100vh;
      overflow-x: hidden;
  }
  ```
- **Text Selection & Focus Ring**:
  ```css
  /* base.css:119-132 */
  ::selection {
      background-color: rgba(37, 99, 235, 0.40);
      color: #ffffff;
  }

  ::-moz-selection {
      background-color: rgba(37, 99, 235, 0.40);
      color: #ffffff;
  }

  :focus-visible {
      outline: 2px solid var(--brand-500);
      outline-offset: 2px;
  }
  ```
- **Autofill Normalization**: Suppresses browser autofill background flash in dark mode (`base.css:160-172`):
  ```css
  /* base.css:160-172 */
  input:-webkit-autofill,
  input:-webkit-autofill:hover, 
  input:-webkit-autofill:focus,
  textarea:-webkit-autofill,
  textarea:-webkit-autofill:hover,
  textarea:-webkit-autofill:focus,
  select:-webkit-autofill,
  select:-webkit-autofill:hover,
  select:-webkit-autofill:focus {
      -webkit-text-fill-color: var(--text-primary);
      -webkit-box-shadow: 0 0 0px 1000px var(--bg-input) inset;
      transition: background-color 5000s ease-in-out 0s;
  }
  ```
- **Custom Cyber Scrollbars**: Uses semantic design tokens for WebKit, Blink, and Gecko engines (`base.css:88-114`):
  ```css
  /* base.css:88-114 */
  ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
  }

  ::-webkit-scrollbar-track {
      background: var(--bg-app);
  }

  ::-webkit-scrollbar-thumb {
      background: var(--border-default);
      border-radius: var(--radius-full);
  }

  ::-webkit-scrollbar-thumb:hover {
      background: var(--border-hover);
  }

  ::-webkit-scrollbar-corner {
      background: var(--bg-app);
  }

  /* Firefox */
  * {
      scrollbar-width: thin;
      scrollbar-color: var(--border-default) var(--bg-app);
  }
  ```

---

## 2. Complete Color Palette & Token Taxonomy

### 2.1 Canvas, Surface Elevation & Container Palette
The foundation of 3D Print Calc Pro's dark interface is a layered hierarchy of obsidian and dark blue-slate tones that establish physical depth without visual clutter:

| CSS Variable | Hex / RGBA | Role / Architectural Semantic Usage | Source File & Line | Tailwind Config Key |
|---|---|---|---|---|
| `--bg-app` | `#080b11` | Ultra-deep obsidian viewport canvas; page background | `tokens.css:15` | `darkbg: '#080b11'` |
| `--bg-canvas` | `#0b0f17` | Primary workspace container & layout canvas | `tokens.css:16` | `darkcanvas: '#0b0f17'` |
| `--bg-surface` | `#111827` | Outer chrome: sidebar, sticky topbar, modal backdrop | `tokens.css:17` | `darksurface: '#111827'` |
| `--bg-surface-elevated`| `#151d2e` | High-elevation containers, tooltips & modals | `tokens.css:18` | `darkcard: '#151d2e'` |
| `--bg-card` | `#151d2e` | Standard elevated SaaS card surface (`.card-dark`) | `tokens.css:19` | `darkcard: '#151d2e'` |
| `--bg-card-hover` | `#1a2438` | Interactive card hover state | `tokens.css:20` | `darkcardhover: '#1a2438'`|
| `--bg-card-active` | `#1f2b42` | Selected / active card state | `tokens.css:21` | `darkcardactive: '#1f2b42'`|
| `--bg-glass` | `rgba(17, 24, 39, 0.75)` | Translucent chrome glass (sticky topbar) | `tokens.css:22` | N/A |
| `--bg-glass-card` | `rgba(21, 29, 46, 0.85)` | Translucent card glass (sticky financial terminal) | `tokens.css:23` | N/A |
| `--bg-input` | `#0c121e` | Recessed form input surface | `tokens.css:24` | `darkinput: '#0c121e'` |
| `--bg-input-focus` | `#0f1726` | Active focused input surface | `tokens.css:25` | `darkinputfocus: '#0f1726'`|

### 2.2 Backward Compatibility & Legacy Aliases
Defined in `frontend/css/tokens.css:28-35`. These tokens guarantee that existing code and third-party plugins referencing standard design token names resolve cleanly:

```css
/* frontend/css/tokens.css:28-35 */
--bg-primary: var(--bg-canvas);     /* Resolves to #0b0f17 */
--bg-secondary: var(--bg-surface);   /* Resolves to #111827 */
--border-color: var(--border-default); /* Resolves to #243044 */
--accent: var(--brand-500);         /* Resolves to #3b82f6 */
--accent-hover: var(--brand-600);   /* Resolves to #2563eb */
--success: var(--emerald-500);       /* Resolves to #10b981 */
--warning: var(--amber-500);         /* Resolves to #f59e0b */
--danger: var(--rose-500);           /* Resolves to #ef4444 */
```

### 2.3 Brand Royal Blue Series (Primary Accent & CTAs)
The primary action color of the application. Used for primary call-to-action buttons, active navigation states, input focus rings, and glowing highlights:

| CSS Variable | Hex / RGBA | Role / Usage | Source File & Line | Tailwind Key |
|---|---|---|---|---|
| `--brand-50` | `#eff6ff` | Tinted text highlight | `tokens.css:48` | `brand.50` |
| `--brand-100` | `#dbeafe` | High-contrast subtext | `tokens.css:49` | `brand.100` |
| `--brand-200` | `#bfdbfe` | Light badge text | `tokens.css:50` | `brand.200` |
| `--brand-300` | `#93c5fd` | Quoted badge text, real-time tags | `tokens.css:51` | `brand.300` |
| `--brand-400` | `#60a5fa` | Secondary link text, button hover text | `tokens.css:52` | `brand.400` |
| `--brand-500` | `#3b82f6` | Vibrant interactive blue, focus border, plate border | `tokens.css:53` | `brand.500` |
| `--brand-600` | `#2563eb` | Primary SaaS CTA button fill | `tokens.css:54` | `brand.600` |
| `--brand-700` | `#1d4ed8` | Pressed / active CTA button state | `tokens.css:55` | `brand.700` |
| `--brand-800` | `#1e40af` | Dark container tint | `tokens.css:56` | `brand.800` |
| `--brand-900` | `#1e3a8a` | Deep blue background surface | `tokens.css:57` | `brand.900` |
| `--brand-surface` | `rgba(37, 99, 235, 0.12)` | Subtle blue translucent backdrop | `tokens.css:58` | N/A |
| `--brand-border` | `rgba(59, 130, 246, 0.35)` | Glowing blue border | `tokens.css:59` | N/A |
| `--brand-glow` | `rgba(37, 99, 235, 0.30)` | Input focus ring and halo glow | `tokens.css:60` | N/A |

### 2.4 Emerald Series (Profits, Approved Quotes & Success)
Used for positive business outcomes: Net profit displays, margin percentages, approved and completed project states, and success toasts:

| CSS Variable | Hex / RGBA | Role / Usage | Source File & Line | Tailwind Key |
|---|---|---|---|---|
| `--emerald-300` | `#6ee7b7` | PETG material badge text | `tokens.css:63` | `emerald.300` |
| `--emerald-400` | `#34d399` | Net profit text, approved badge text | `tokens.css:64` | `emerald.400` |
| `--emerald-500` | `#10b981` | Vibrant emerald, success CTA button fill | `tokens.css:65` | `emerald.500` |
| `--emerald-600` | `#059669` | Success button active / hover gradient | `tokens.css:66` | `emerald.600` |
| `--emerald-700` | `#047857` | Pressed success button state | `tokens.css:67` | `emerald.700` |
| `--emerald-surface`| `rgba(16, 185, 129, 0.12)`| Net profit callout background | `tokens.css:68` | N/A |
| `--emerald-border` | `rgba(16, 185, 129, 0.35)` | Net profit callout border | `tokens.css:69` | N/A |
| `--emerald-glow` | `rgba(16, 185, 129, 0.25)` | Success pulse glow animation | `tokens.css:70` | N/A |

### 2.5 Royal Violet Series (Hardware & Technical Specs)
Used for 3D printer hardware specs, machine depreciation parameters, and filament cost breakdown charts:

| CSS Variable | Hex / RGBA | Role / Usage | Source File & Line | Tailwind Key |
|---|---|---|---|---|
| `--violet-300` | `#c4b5fd` | Filament specification tag | `tokens.css:73` | `violet.300` |
| `--violet-400` | `#a78bfa` | Machine rate subtext | `tokens.css:74` | `violet.400` |
| `--violet-500` | `#8b5cf6` | Vibrant hardware accent, printer badges | `tokens.css:75` | `violet.500` |
| `--violet-600` | `#7c3aed` | Violet button hover state | `tokens.css:76` | `violet.600` |
| `--violet-700` | `#6d28d9` | Dark hardware container fill | `tokens.css:77` | `violet.700` |
| `--violet-surface` | `rgba(139, 92, 246, 0.12)`| Violet translucent card surface | `tokens.css:78` | N/A |
| `--violet-border` | `rgba(139, 92, 246, 0.35)`| Violet illuminated border | `tokens.css:79` | N/A |
| `--violet-glow` | `rgba(139, 92, 246, 0.25)`| Hardware badge glow ring | `tokens.css:80` | N/A |

### 2.6 Amber Series (Warnings, Filament Stock & In Production)
Used for items in progress, warning callouts, and low-inventory filament badges:

| CSS Variable | Hex / RGBA | Role / Usage | Source File & Line | Tailwind Key |
|---|---|---|---|---|
| `--amber-300` | `#fcd34d` | Light warning subtext | `tokens.css:83` | N/A |
| `--amber-400` | `#fbbf24` | In-production badge text | `tokens.css:84` | `amber.400` |
| `--amber-500` | `#f59e0b` | Vibrant warning amber | `tokens.css:85` | `amber.500` |
| `--amber-600` | `#d97706` | Deep amber border | `tokens.css:86` | `amber.600` |
| `--amber-surface` | `rgba(245, 158, 11, 0.12)` | In-production badge fill | `tokens.css:87` | N/A |
| `--amber-border` | `rgba(245, 158, 11, 0.35)` | Warning border | `tokens.css:88` | N/A |
| `--amber-glow` | `rgba(245, 158, 11, 0.25)` | Amber notification halo | `tokens.css:89` | N/A |

### 2.7 Rose Series (Scrap Errors, Alerts & Cancelled Quotes)
Used for scrap loss notifications, delete/destructive actions, form errors, and cancelled project statuses:

| CSS Variable | Hex / RGBA | Role / Usage | Source File & Line | Tailwind Key |
|---|---|---|---|---|
| `--rose-300` | `#fca5a5` | Scrap loss subtext | `tokens.css:92` | N/A |
| `--rose-400` | `#f87171` | Cancelled badge text, error indicator | `tokens.css:93` | `rose.400` |
| `--rose-500` | `#ef4444` | Vibrant danger rose, scrap callout border | `tokens.css:94` | `rose.500` |
| `--rose-600` | `#dc2626` | Destructive button fill | `tokens.css:95` | `rose.600` |
| `--rose-surface` | `rgba(239, 68, 68, 0.12)` | Scrap section background | `tokens.css:96` | N/A |
| `--rose-border` | `rgba(239, 68, 68, 0.35)` | Danger input outline | `tokens.css:97` | N/A |
| `--rose-glow` | `rgba(239, 68, 68, 0.25)` | Danger halo pulse | `tokens.css:98` | N/A |

### 2.8 Text & Foreground Hierarchy
Text contrast is strictly calibrated to ensure WCAG AA compliance against deep obsidian surfaces:

| CSS Variable | Hex Value | Luminance / Role | Source File & Line |
|---|---|---|---|
| `--text-primary` | `#f8fafc` | 98% Luminance (Crisp White). Used for headings, primary values, active navigation, input text | `tokens.css:101` |
| `--text-secondary` | `#94a3b8` | Slate 400. Used for form labels, descriptions, inactive nav, table headers | `tokens.css:102` |
| `--text-muted` | `#64748b` | Slate 500. Used for input placeholders, unit suffixes, disabled captions | `tokens.css:103` |
| `--text-accent` | `#60a5fa` | Light Blue. Used for interactive hyperlinks and action icons | `tokens.css:104` |
| `--text-inverse` | `#080b11` | Inverted Obsidian. Used on bright badge pills or tooltips | `tokens.css:105` |

### 2.9 Borders, Dividers & Hairlines
All structural borders avoid pure gray lines, utilizing translucent whites and dark blues to maintain depth:

| CSS Variable | Value | Purpose | Source File & Line |
|---|---|---|---|
| `--border-subtle` | `rgba(255, 255, 255, 0.06)` | Hairline internal card dividers, table borders | `tokens.css:38` |
| `--border-default` | `#243044` | Standard card border, form input border, panel borders | `tokens.css:39` |
| `--border-hover` | `#334155` | Interactive card and button hover border | `tokens.css:40` |
| `--border-focus` | `#3b82f6` | Input focus ring border | `tokens.css:41` |
| `--border-highlight` | `rgba(255, 255, 255, 0.12)` | Top edge rim light hairline gradient sheen | `tokens.css:42` |
| `--border-glow-blue` | `rgba(59, 130, 246, 0.45)` | Slicer dropzone and sticky terminal glow border | `tokens.css:43` |
| `--border-glow-emerald`| `rgba(16, 185, 129, 0.45)` | Net profit callout and approved quote border | `tokens.css:44` |
| `--border-glow-violet` | `rgba(139, 92, 246, 0.45)` | Printer catalog card active border | `tokens.css:45` |

### 2.10 Project Status Badges Color Contract
Defined in `frontend/css/components.css:427-462`. Applied to status pills across dashboard, tables, and project headers:

| Status Key | Selector | Background (Fill) | Border | Text Color | Box Shadow |
|---|---|---|---|---|---|
| `draft` | `.badge-draft` | `rgba(148, 163, 184, 0.12)` | `1px solid rgba(148, 163, 184, 0.25)` | `#94a3b8` | none |
| `quoted` | `.badge-quoted` | `rgba(59, 130, 246, 0.14)` | `1px solid rgba(59, 130, 246, 0.35)` | `#60a5fa` | none |
| `approved` | `.badge-approved` | `rgba(16, 185, 129, 0.14)` | `1px solid rgba(16, 185, 129, 0.35)` | `#34d399` | none |
| `in_production`| `.badge-in_production` | `rgba(245, 158, 11, 0.14)` | `1px solid rgba(245, 158, 11, 0.35)` | `#fbbf24` | none |
| `completed` | `.badge-completed` | `rgba(16, 185, 129, 0.20)` | `1px solid rgba(16, 185, 129, 0.45)` | `#10b981` | `0 0 10px rgba(16, 185, 129, 0.18)` |
| `cancelled` | `.badge-cancelled` | `rgba(239, 68, 68, 0.14)` | `1px solid rgba(239, 68, 68, 0.35)` | `#f87171` | none |

### 2.11 Material Badges Color Contract
Defined in `frontend/css/components.css:465-507`. Renders distinct identification pills for filament polymers:

| Material Type | Selector | Background (Fill) | Border | Text Color | Box Shadow |
|---|---|---|---|---|---|
| **PLA** | `.badge-mat-pla` | `rgba(30, 58, 138, 0.45)` | `1px solid rgba(59, 130, 246, 0.35)` | `#93c5fd` | none |
| **PETG** | `.badge-mat-petg` | `rgba(6, 78, 59, 0.45)` | `1px solid rgba(16, 185, 129, 0.35)` | `#6ee7b7` | none |
| **ABS** | `.badge-mat-abs` | `rgba(124, 45, 18, 0.45)` | `1px solid rgba(249, 115, 22, 0.35)` | `#fdba74` | none |
| **TPU** | `.badge-mat-tpu` | `rgba(88, 28, 135, 0.45)` | `1px solid rgba(168, 85, 247, 0.35)` | `#d8b4fe` | none |
| **ASA** | `.badge-mat-asa` | `rgba(113, 63, 18, 0.45)` | `1px solid rgba(234, 179, 8, 0.35)` | `#fde047` | none |
| **Resina UV**| `.badge-mat-resina` | `rgba(13, 148, 136, 0.45)` | `1px solid rgba(20, 184, 166, 0.35)` | `#5eead4` | `0 0 10px rgba(20, 184, 166, 0.15)` |
| **Outro** | `.badge-mat-other`, `.badge-mat-outro` | `rgba(55, 65, 81, 0.45)` | `1px solid rgba(107, 114, 128, 0.35)` | `#d1d5db` | none |

### 2.12 Chart.js & Analytics Data Visualization Colors
Configured in `frontend/js/app.js:742-1013`. Governs dark-mode telemetry charts on the Executive Dashboard:

1. **Global Theme Defaults (`app.js:744-768`)**:
   - Label Color: `#94a3b8`
   - Gridlines: `rgba(255, 255, 255, 0.04)`
   - Tooltip Background: `#0f172a` with border `1px solid #334155`
2. **Pipeline Status Funnel Doughnut (`#chart-status-funnel`, `app.js:778`)**:
   - Palette: `['#64748b', '#3b82f6', '#10b981', '#8b5cf6', '#06b6d4', '#ef4444']`
   - Arc Border: `#151d2e`
3. **Financial Timeline (`#chart-financial-timeline`, `app.js:846-870`)**:
   - Faturamento (Revenue): `rgba(59, 130, 246, 0.8)` (Royal Blue bar)
   - Custo Base (Cost): `rgba(245, 158, 11, 0.75)` (Amber bar)
   - Lucro Líquido (Net Profit): Line `#10b981`, Fill `rgba(16, 185, 129, 0.12)`
4. **Cost Breakdown CPV Doughnut (`#chart-cost-breakdown`, `app.js:937-947`)**:
   - Filamento: `#8b5cf6` (Royal Violet)
   - Máquina & Energia: `#3b82f6` (Royal Blue)
   - Mão de Obra: `#f59e0b` (Amber)
   - Insumos BOM: `#64748b` (Slate Muted)
   - Lucro Líquido: `#10b981` (Emerald)
5. **Top Projects Horizontal Bar (`#chart-top-projects`, `app.js:1004-1012`)**:
   - Faturamento: `rgba(59, 130, 246, 0.85)`
   - Lucro Líquido: `rgba(16, 185, 129, 0.85)`

### 2.13 High-Fidelity Paper Print Stylesheet (@media print)
Declared in `frontend/css/styles.css:24-122`. Inverts dark mode to high-contrast monochrome paper formatting:

- Page Background: `#ffffff !important;` (`styles.css:36`)
- Text Color: `#000000 !important;` (`styles.css:30, 37`)
- Table Header: `background-color: #f1f5f9; color: #0f172a; border-bottom: 2px solid #94a3b8;` (`styles.css:76-78`)
- Table Cells: `border-bottom: 1px solid #cbd5e1; color: #1e293b;` (`styles.css:84-86`)
- Final Price Box: `background: #f8fafc; border: 2px solid #2563eb; color: #1e40af;` (`styles.css:104-109`)
- Net Profit Box: `background: #f0fdf4; border: 1px solid #16a34a; color: #15803d;` (`styles.css:115-120`)
- Hidden Selectors: `aside, header, #toast-container, #auth-modal, #modal-printer, #modal-filament, #dropzone, #btn-add-plate-bottom, button, .btn` (`styles.css:46-59`).

### 2.14 Timing, Easings & Interactive Transitions Tokens
Declared in `frontend/css/tokens.css:161-170`. Governs all kinetic motion, hover transformations, focus expansion, and modal animations across the application:

```css
/* frontend/css/tokens.css:161-170 */
/* ==========================================================================
   5. TRANSITIONS & TIMING
   ========================================================================== */
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
--transition-fast: 150ms var(--ease-spring);
--transition-normal: 250ms var(--ease-spring);
--transition-slow: 350ms var(--ease-spring);
```

#### Complete Motion Tokens Directory:

| Token Name | Computed Value | Timing Function | UI Application & Kinetic Intent | Source Declaration |
|---|---|---|---|---|
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Standard Deceleration Curve | View entrances, list items appearing, drawer slide-ins | `tokens.css:164` |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Acceleration-Deceleration | Continuous breathing loops (`pulseGlow`, `pulseSuccess`) | `tokens.css:165` |
| `--ease-spring` | `cubic-bezier(0.16, 1, 0.3, 1)` | Low-Friction Snappy Spring | Fast interactive feedback: button clicks, card lifts, focus rings | `tokens.css:166` |
| `--transition-fast` | `150ms cubic-bezier(0.16, 1, 0.3, 1)` | Snappy Micro-Interaction | Form input focus, button hovers, swatch zooms, badge highlights | `tokens.css:167` |
| `--transition-normal` | `250ms cubic-bezier(0.16, 1, 0.3, 1)` | Component Transformation | Card elevation lift, sidebar collapse/expand, table row hover | `tokens.css:168` |
| `--transition-slow` | `350ms cubic-bezier(0.16, 1, 0.3, 1)` | Layout & Backdrop Morph | Modal backdrop blur-in, fullscreen container expansion | `tokens.css:169` |

---

## 3. Typography & Font Engineering

### 3.1 Font Family Stacks & CDN Imports
3D Print Calc Pro integrates two Google Fonts to distinguish readable UI typography from precise tabular numeric metrics:

```css
/* frontend/css/tokens.css:7 */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap');
```

1. **Sans-Serif UI Stack (`tokens.css:110`)**:
   ```css
   --font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
   ```
   - Used for all standard body copy, section titles, navigation menus, labels, badges, and modals.
2. **Monospace Tabular Metric Stack (`tokens.css:111`)**:
   ```css
   --font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
   ```
   - Used for all financial values, currency figures (`R$`), slicer weights (`g`), times (`h:min`), and calculation tables.
3. **Print Stack (`styles.css:38`)**:
   ```css
   font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
   ```
4. **Backend PDF Generation (`backend/pdf_service.py:64, 72, 80`)**:
   - Employs ReportLab built-in Type 1 fonts: `Helvetica`, `Helvetica-Bold`, and `Helvetica-Oblique`.

### 3.2 Tabular Numbers & Numeric Precision Features
To prevent horizontal layout jitter when prices or calculations update in real time, tabular numeric figures are globally enforced on numeric controls:

```css
/* frontend/css/base.css:60-71 and components.css:111-118 */
code, 
kbd, 
samp, 
pre, 
.font-mono, 
input[type="number"], 
input[inputmode="decimal"],
.font-numeric,
.tabular-nums {
    font-family: var(--font-mono);
    font-feature-settings: 'tnum' 1, 'zero' 1;
    font-variant-numeric: tabular-nums;
}
```

#### Native Number Spinner Suppression:
Native browser increment spinners are hidden to preserve clean numerical alignments across all browsers:
```css
/* frontend/css/base.css:74-81 */
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
input[type="number"] {
    -moz-appearance: textfield;
}
```

### 3.3 Complete Typographic Scale Hierarchy (9px to 36px)
The type scale is calibrated in `rem` units based on a `1rem = 16px` root browser standard:

| Token / Class | Computed Value | Pixel Equivalent | Exact CSS Selector & File Location | Primary Semantic Usage |
|---|---|---|---|---|
| `text-[9px]` | `0.5625rem` | 9px | `index.html:1032` | Cost distribution mini-bar legend tags |
| `text-[10px]` | `0.625rem` | 10px | `index.html:1021`, `preview.html:102` | Uppercase section pill tags, chart axis ticks |
| `--text-2xs` | `0.6875rem` | 11px | `tokens.css:114`, `components.css:415` | Status and material badges, table uppercase `th` |
| `--text-xs` | `0.75rem` | 12px | `tokens.css:115`, `components.css:285` | Small buttons, secondary captions, form helpers |
| `0.8125rem` | `0.8125rem` | 13px | `components.css:153` | Native `<select>` dropdown option items |
| `--text-sm` | `0.875rem` | 14px | `tokens.css:116`, `base.css:39` | Global default body text, form input values |
| `--text-base` | `1rem` | 16px | `tokens.css:117`, `app.js:2636, 2674, 2928` | Card titles (`app.js:2674`), view empty states (`app.js:2636, 2928`) |
| `--text-lg` | `1.125rem` | 18px | `tokens.css:118`, `views.css:175` | `#view-title` (sticky topbar current view heading) |
| `--text-xl` | `1.25rem` | 20px | `tokens.css:119` | Modal dialog titles, major section headings |
| `--text-2xl` | `1.5rem` | 24px | `tokens.css:120`, `views.css:610, 687`, `index.html:110` | Hourly machine rate hero (`views.css:610`), filament unit cost display (`#filaments-grid`, `views.css:687`), auth modal title (`index.html:110`) |
| `1.75rem` | `1.75rem` | 28px | `views.css:209` | Dashboard stat counters (`#stat-*-count`) |
| `--text-3xl` | `1.875rem` | 30px | `tokens.css:121`, `views.css:512` | `#live-final-price` hero commercial quote display |
| `--text-4xl` | `2.25rem` | 36px | `tokens.css:122` | Hero marketing displays |

### 3.4 Font Weights & Tracking / Letter-Spacing Values
- **Font Weights**:
  - `400` (`--font-normal`, `tokens.css:125`): Body copy, table cells, form helpers.
  - `500` (`--font-medium`, `tokens.css:126`): Navigation menu items, form labels.
  - `600` (`--font-semibold`, `tokens.css:127`): Card headers, button labels, badge text.
  - `700` (`--font-bold`, `tokens.css:128`): Modal titles, table `th`, base cost summary line.
  - `800` (Extra Bold, `views.css:210, 514`): Stat card metrics, `#live-final-price`.
  - `900` (Black, `views.css:611, 688`): Hourly machine rate breakdown numbers.
- **Letter Spacing / Tracking Hierarchy**:
  - `-0.03em`: Dashboard stat counter numbers (`views.css:211`)
  - `-0.025em`: Live final price gradient text (`views.css:515`)
  - `-0.02em`: Headings h1-h6 (`base.css:51`), topbar view title (`views.css:177`), machine rates (`views.css:613`)
  - `-0.01em`: Summary panel h3 titles (`views.css:440`)
  - `0.025em`: Status & material badge pills (`components.css:417`)
  - `0.05em`: Real-time pill badge (`views.css:451`)
  - `0.06em`: Uppercase table headers (`components.css:597`, `views.css:280`)

---

## 4. Spacing, Dimensions & Layout Conventions

### 4.1 Layout Shell & Full Viewport Architecture
The application layout establishes a non-scrolling parent shell where individual panels control their internal overflow:

```css
/* frontend/css/views.css:13-21 */
#app-layout {
    display: flex;
    min-height: 100vh;
    height: 100vh;
    background-color: var(--bg-canvas, #0b0f17);
    overflow: hidden;
    position: relative;
}
```

### 4.2 Sidebar Navigation Geometry (Expanded & Collapsed)
The navigation sidebar supports both manual toggle and responsive collapse states:

- **Expanded Desktop State (`views.css:24-36`, `components.css:641-650`)**:
  - Width: `16rem` (`256px`), `min-width: 16rem`, `max-width: 16rem`
  - Background: `var(--bg-surface, #111827) !important`
  - Border Right: `1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))`
  - Box Shadow: `var(--shadow-lg)`
- **JavaScript Collapsed State (`components.css:660-664`)**:
  - Selector: `#app-sidebar.sidebar-collapsed`
  - Width: `5rem !important` (`80px`), `min-width: 5rem`, `max-width: 5rem`
  - Hides `.sidebar-text`, `.sidebar-label`, centers icons and brand header.
- **Responsive Tablet Collapsed (`views.css:858-862`)**:
  - `@media (max-width: 1024px)`: Width drops to `4.5rem` (`72px`).
- **Brand Header Geometry (`views.css:39-42`)**:
  - Height: `4rem` (`64px` / `h-16`), Padding: `0 1.5rem`

### 4.3 Sticky Topbar Header Dimensions
The application header remains locked to the top of the main viewport:

```css
/* frontend/css/views.css:163-171 */
main header.sticky {
    height: 4rem; /* 64px */
    background: var(--bg-glass, rgba(17, 24, 39, 0.75)) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.06));
    z-index: 20;
    padding-left: 2rem; /* 32px */
    padding-right: 2rem;
}
```

### 4.4 Sticky Financial Terminal Architecture & Scrolling
The project calculator features a persistent financial terminal card (`.summary-panel-card`) on the right side:

- **Top Offset (`views.css:347`)**: `top: 5rem`
- **Desktop Height Constraint (`views.css:369-373`)**:
  ```css
  @media (min-width: 1024px) {
      .summary-panel-card {
          max-height: calc(100vh - 6.5rem);
      }
  }
  ```
- **Internal 3-Section Flex Architecture (`views.css:376-389`)**:
  1. `.summary-panel-top`: `flex-shrink: 0;` (Fixed header & real-time badge)
  2. `.summary-panel-body`: `flex: 1 1 auto; overflow-y: auto; overscroll-behavior: contain;` (Scrollable metrics)
  3. `.summary-panel-bottom`: `flex-shrink: 0;` (Fixed CTA action buttons)
- **Dedicated Slim Cyber Scrollbar (`views.css:391-418`)**: Width `5px`, Track `rgba(15, 23, 42, 0.5)`, Thumb `rgba(59, 130, 246, 0.35)`.

### 4.5 Spacing Scale (Micro, Small, Medium, Large)
- **Micro (2px - 6px)**:
  - `p-0.5` (2px): Cost distribution bar container (`index.html:1025`)
  - `0.15rem 0.5rem` (2.4px / 8px): Real-time summary tag (`views.css:448`)
  - `0.2rem 0.6rem` (3.2px / 9.6px): Status and material badges (`components.css:419`)
  - `0.25rem` (4px): Form subgrid label gaps (`views.css:716`)
- **Small (8px - 14px)**:
  - `0.375rem 0.625rem` (6px / 10px): Info tooltip popup (`components.css:214`)
  - `0.5rem 0.875rem` (8px / 14px): Standard `.btn` padding (`components.css:289`)
  - `0.625rem 0.875rem` (10px / 14px): Select dropdowns, nav buttons (`views.css:63`)
  - `0.75rem` (12px): Aside navigation container padding (`views.css:54`)
  - `0.75rem 1rem` (12px / 16px): Table header cells (`views.css:282`)
  - `0.875rem 1rem` (14px / 16px): Table body data cells (`views.css:306`)
- **Medium (16px - 24px)**:
  - `p-4` (16px): Mobile auth modal padding, preview header (`preview.html:93`)
  - `p-5` (20px): Dashboard stat cards (`index.html:268`), multi-plate cards (`app.js:1506`)
  - `p-6` (24px): Catalog cards (`app.js:2542`), sticky financial terminal (`index.html:984`)
- **Large (32px - 48px)**:
  - `padding: 32px` (2rem): Topbar desktop padding (`views.css:171`)
  - `p-8` (32px): Slicer dropzone container (`index.html:793`), auth modal card (`index.html:105`)
  - `p-12` (48px): Catalog zero-state card (`app.js:2506`)

### 4.6 Grid & Flexbox Layout Configurations
- **Dashboard Telemetry Grid (`index.html:266`)**:
  `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`
- **Dashboard Analytics Charts Grid (`index.html:314`)**:
  `grid grid-cols-1 lg:grid-cols-2 gap-6`
- **Project Editor Asymmetric Split (`index.html:785-787`)**:
  `grid grid-cols-1 lg:grid-cols-12 gap-6`
  - Left Workspace Column: `lg:col-span-8 space-y-6`
  - Right Sticky Summary Terminal: `lg:col-span-4 sticky top-20`
- **Catalog Grids (`#printers-grid`, `#filaments-grid`, `views.css:574, 629`)**:
  `display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem;`

### 4.7 CSS Subgrid Auto-Aligned Form Architecture
Located in `frontend/css/views.css:699-758`. Guarantees that multi-column form inputs remain vertically aligned across identical baseline rows regardless of label wrap length:

```css
/* frontend/css/views.css:700-757 */
.form-aligned-grid {
    display: grid;
    align-items: start;
}

.form-col-aligned {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

/* Fallback for non-subgrid browsers */
.form-label-header {
    min-height: 3.5rem; /* Accommodates up to 3 lines without shifting inputs */
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.25rem;
    margin-bottom: 0.375rem;
}

.form-helper-text {
    min-height: 2.25rem; /* Accommodates up to 2 helper lines */
    margin-top: 0.25rem;
    display: block;
}

/* Modern CSS Subgrid Enhancement */
@supports (grid-template-rows: subgrid) {
    .form-aligned-grid {
        grid-auto-rows: auto;
    }

    .form-col-aligned {
        display: grid;
        grid-row: span 3;
        grid-template-rows: subgrid;
        row-gap: 0.375rem;
    }

    .form-label-header {
        min-height: 0 !important;
        margin-bottom: 0 !important;
        align-self: start;
    }

    .form-input-container {
        align-self: start;
    }

    .form-helper-text {
        min-height: 0 !important;
        margin-top: 0 !important;
        align-self: start;
    }
}
```

### 4.8 Multi-Plate Hardware Grid Alignment
Defined in `frontend/css/views.css:905-933`. Enforces visual harmony across multi-plate 3D slicer rows:

- Selector: `.plate-grid-aligned`
- Columns: `grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3`
- Minimum Label Slot: `.plate-label-slot { min-height: 30px !important; }`
- Bottom Alignment Anchor: `.plate-field-col > input, select, .relative { margin-top: auto !important; }`

### 4.9 Responsive Breakpoints & Device Adaptation
1. **640px (`sm:`)**: Single column grids expand to 2-4 columns.
2. **768px (`md:`)**: Modal cards expand to maximum bounded dialog sizes.
3. **1024px (`lg:`, `@media (max-width: 1024px)`)**:
   - Sidebar contracts to `4.5rem` (72px) with label suppression (`views.css:858`).
   - Project editor activates the 8/4 column asymmetric split.
   - Sticky financial terminal enables `max-height: calc(100vh - 6.5rem)` (`views.css:369`).
4. **Mobile Height Adaptation (`@media (max-width: 640px)`)**:
   - Reduces `.chart-canvas-wrapper` height to `230px` (max 240px) (`views.css:897`).
5. **Print Media (`@media print`)**: Activates paper white reset (`styles.css:24-122`).
6. **Motion Sensitivity (`@media (prefers-reduced-motion: reduce)`)**: Reduces all animation and transition durations to `0.01ms` (`animations.css:115-124`).

---

## 5. Depth, Elevation, Shadows & Specialized Lighting

### 5.1 Elevation & Box-Shadows Scale
Defined in `frontend/css/tokens.css:133-148`. Every elevation plane is calibrated to create realistic visual depth against `#080b11`:

| Token | Shadow Value | Architectural Application |
|---|---|---|
| `--shadow-xs` | `0 1px 2px 0 rgba(0, 0, 0, 0.30)` | Subtle inner elements, badges |
| `--shadow-sm` | `0 2px 4px 0 rgba(0, 0, 0, 0.35)` | Secondary buttons, recessed inputs |
| `--shadow-md` | `0 4px 12px -2px rgba(0, 0, 0, 0.45), 0 2px 4px -2px rgba(0, 0, 0, 0.35)` | Default SaaS surface cards (`.card-dark`) |
| `--shadow-lg` | `0 12px 24px -4px rgba(0, 0, 0, 0.55), 0 4px 8px -2px rgba(0, 0, 0, 0.40)` | Hovered interactive cards, persistent sidebar |
| `--shadow-xl` | `0 24px 48px -12px rgba(0, 0, 0, 0.70), 0 8px 16px -4px rgba(0, 0, 0, 0.50)` | Sticky financial terminal, modal dialog windows |
| `--shadow-inner-glow`| `inset 0 1px 0 0 rgba(255, 255, 255, 0.08)` | Top glass bevel applied to `.card-dark` |
| `--shadow-input-focus`| `0 0 0 3px rgba(37, 99, 235, 0.25), 0 1px 2px 0 rgba(0, 0, 0, 0.35)` | Form input active focus ring |

### 5.2 Ambient Halo Glows
Soft radial drop shadows simulating light emanating from active elements:

- `--glow-brand`: `0 0 20px -3px rgba(37, 99, 235, 0.35)` (`tokens.css:144`)
- `--glow-emerald`: `0 0 20px -3px rgba(16, 185, 129, 0.35)` (`tokens.css:145`)
- `--glow-violet`: `0 0 20px -3px rgba(139, 92, 246, 0.35)` (`tokens.css:146`)
- `--glow-amber`: `0 0 20px -3px rgba(245, 158, 11, 0.35)` (`tokens.css:147`)
- `--glow-card-hover`: `0 8px 30px -4px rgba(0, 0, 0, 0.60), 0 0 16px -2px rgba(59, 130, 246, 0.15)` (`tokens.css:148`)

### 5.3 Physical Lighting Metaphor: Top Hairline Bevel (.card-dark::before)
A signature design detail of 3D Print Calc Pro is the simulated top rim-lighting on elevated cards:

```css
/* frontend/css/components.css:25-37 */
.card-dark::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.12) 50%, transparent 100%);
    border-top-left-radius: inherit;
    border-top-right-radius: inherit;
    pointer-events: none;
    z-index: 1;
}
```
*Note*: This technique originated from the prototype reference in `efeito-borda-iluminada.html`.

### 5.4 Dual-Accent Bevel (.summary-panel-card::before)
The sticky financial terminal card features an enhanced dual-accent top hairline transition:

```css
/* frontend/css/views.css:421-433 */
.summary-panel-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, #3b82f6 35%, #10b981 70%, transparent 100%);
    border-top-left-radius: inherit;
    border-top-right-radius: inherit;
    pointer-events: none;
    z-index: 2;
}
```

### 5.5 Live Final Price Hero Halo & Neon Glow
The commercial quote price hero box combines radial gradient lighting with text neon glow:

```css
/* frontend/css/components.css:614-624 and views.css:487-521 */
.final-price-box {
    background: radial-gradient(circle at center, rgba(37, 99, 235, 0.22) 0%, rgba(15, 23, 42, 0.75) 100%) !important;
    border: 1px solid rgba(59, 130, 246, 0.45);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 4px 20px rgba(37, 99, 235, 0.25);
    border-radius: var(--radius-lg, 0.75rem);
}

#live-final-price {
    font-family: var(--font-mono, 'JetBrains Mono', monospace);
    font-size: 1.875rem; /* 30px */
    font-weight: 800;
    letter-spacing: -0.025em;
    background: linear-gradient(135deg, #60a5fa 0%, #38bdf8 50%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 14px rgba(56, 189, 248, 0.40));
}
```

### 5.6 Net Profit Callout Pod Depth
```css
/* frontend/css/components.css:626-635 and views.css:523-535 */
.net-profit-box {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 78, 59, 0.20) 100%) !important;
    border: 1px solid rgba(16, 185, 129, 0.35);
    box-shadow: 0 0 16px rgba(16, 185, 129, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: var(--radius-md, 0.5rem);
}
```

### 5.7 Border Radii System
Defined in `frontend/css/tokens.css:153-159`:

- `--radius-xs: 0.25rem` (4px): Real-time badge pill, paper print summary boxes.
- `--radius-sm: 0.375rem` (6px): Table action buttons, base cost highlight bar.
- `--radius-md: 0.5rem` (8px): Form inputs, select dropdowns, standard buttons (`.btn`), tooltips.
- `--radius-lg: 0.75rem` (12px): Standard elevated cards (`.card-dark`), final price hero box, net profit box.
- `--radius-xl: 1rem` (16px): Interactive file dropzone (`.dropzone`), summary panel card (`.summary-panel-card`).
- `--radius-2xl: 1.25rem` (20px): Auth modal window, high-emphasis dialogs.
- `--radius-full: 9999px`: Status badges, material badges, scrollbar thumbs, color swatches.

### 5.8 Border Widths & Stroke Styles
- `1px solid var(--border-default, #243044)`: Standard card borders, form input borders, modal borders.
- `1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))`: Table internal dividers, sidebar right border.
- `2px dashed var(--border-default, #243044)`: Slicer dropzone (`#dropzone`), bottom add plate button (`#btn-add-plate-bottom`).
- `3px solid var(--brand-500, #3b82f6)`: Dynamic left accent border on multi-plate cards (`views.css:779`).
- `1px dashed var(--border-default, #243044)`: Filament modal live preview box (`views.css:764`).

### 5.9 Motion Physics, Easings & Interactive Transition Curves
The user interface implements a cohesive physical kinetic metaphor based on a low-friction mechanical spring response (`--ease-spring: cubic-bezier(0.16, 1, 0.3, 1)`):

1. **Micro-Interaction Cadence (150ms — `--transition-fast`)**:
   - **Form Fields (`components.css:89-91`)**: Smooth background and border shifts when activating inputs (`.form-input-dark`, `select`, `textarea`).
   - **Action Triggers (`components.css:306, 332, 358`)**: Immediate tactile response on primary (`.btn-primary`), success (`.btn-success`), and secondary buttons (`.btn-secondary`).
   - **Color Swatches (`views.css:657-658`)**: Instant swatch scaling and halo intensity change upon cursor hover.
2. **Component Elevation Cadence (250ms — `--transition-normal`)**:
   - **Elevated Cards (`components.css:18-21`, `views.css:584-586, 639-641`)**: Cards smoothly rise by `translateY(-2px)` while expanding `--shadow-lg` and border illumination without visual tearing.
   - **Sidebar Geometry (`components.css:645-647`, `views.css:35`)**: Smooth width expansion from `4.5rem` (collapsed) to `16rem` (expanded).
3. **Modal Window Kinetic Scale (`animations.css:88-90`)**:
   - Modal dialogs enter using `@keyframes modalScaleIn` with duration `0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards`, expanding from `scale(0.95)` with subtle `translateY(8px)` up to `scale(1)`.
4. **Accessibility Contract (`prefers-reduced-motion`)**:
   - Declared in `frontend/css/animations.css:115-124`:
     ```css
     @media (prefers-reduced-motion: reduce) {
         *, *::before, *::after {
             animation-duration: 0.01ms !important;
             animation-iteration-count: 1 !important;
             transition-duration: 0.01ms !important;
             scroll-behavior: auto !important;
         }
     }
     ```
   - Guarantees zero vestibular motion discomfort for users requesting reduced motion in operating system preferences.

---

## 6. UI Components & Interactive States Directory

### 6.1 Surface Archetypes & Containers
All surfaces inherit consistent background tokens and depth treatment:

| Component | Selector | Background | Border | Radius | Shadow / Filter | File & Line |
|---|---|---|---|---|---|---|
| **Base Dark Card** | `.card-dark` | `var(--bg-card, #151d2e)` | `1px solid #243044` | `0.75rem` | `--shadow-md` + inner sheen | `components.css:11` |
| **Interactive Card** | `.card-dark.card-interactive` | `var(--bg-card, #151d2e)` | `1px solid #243044` | `0.75rem` | Hover: `translateY(-2px)`, border `#3b82f6` | `components.css:46` |
| **Featured Card** | `.card-dark-featured` | `var(--bg-card, #151d2e)` | `1px solid rgba(59, 130, 246, 0.35) !important` | `0.75rem` | `--shadow-xl` + `0 0 25px rgba(37, 99, 235, 0.15)` + `--shadow-inner-glow` | `components.css:61` |
| **Glass Card** | `.card-dark-glass` | `rgba(21, 29, 46, 0.85)` | `1px solid #243044` | `0.75rem` | `backdrop-filter: blur(16px)` | `components.css:54` |
| **Terminal Panel** | `.summary-panel-card` | `rgba(21, 29, 46, 0.88)` | `1px solid rgba(59, 130, 246, 0.35)` | `1rem` | `blur(20px)`, `--shadow-xl`, blue halo | `views.css:352` |
| **Analytics Chart Card** | `.chart-card` | `var(--bg-card, #151d2e)` | `1px solid #243044` | `0.75rem` | Min-height `360px`; Hover: `0 10px 25px -5px rgba(0,0,0,0.5), 0 0 15px rgba(59,130,246,0.12)` | `views.css:880` |
| **Empty State Banner** | `#dashboard-empty-banner` | `linear-gradient(to right, rgba(23, 37, 84, 0.3), rgba(15, 23, 42, 0.6), rgba(15, 23, 42, 0.8))` | `1px solid rgba(59, 130, 246, 0.30)` | `0.75rem` | `--shadow-xl`, sparkles icon container `shadow-blue-500/10` | `index.html:429` |
| **Modal Dialog** | `#auth-modal .card-dark` | `var(--bg-surface-elevated, #151d2e)` | `1px solid #243044` | `1.25rem` | `0 25px 60px -15px rgba(0, 0, 0, 0.85)` | `components.css:566` |

### 6.2 Buttons & Trigger Controls (Default, Hover, Active, Disabled)

| Component Variant | CSS Selector | State | Background Gradient / Fill | Border | Text Color | Box Shadow & Transform | Source File:Line |
|---|---|---|---|---|---|---|---|
| **Base Button** | `.btn` | Default | transparent | transparent | inherit | radius: `var(--radius-md)`, padding: `0.5rem 0.875rem` | `components.css:279` |
| **Primary CTA** | `.btn-primary` | Default | `linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)` | `1px solid rgba(255, 255, 255, 0.16)` | `#ffffff` | `0 2px 6px rgba(37, 99, 235, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.22)` | `components.css:299` |
| | | `:hover` | `linear-gradient(180deg, #60a5fa 0%, #2563eb 100%)` | unchanged | `#ffffff` | `0 4px 16px rgba(37, 99, 235, 0.50); transform: translateY(-1px)` | `components.css:309` |
| | | `:active` | `linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%)` | unchanged | `#ffffff` | `0 1px 3px rgba(37, 99, 235, 0.40); transform: translateY(0) scale(0.98)` | `components.css:318` |
| **Success CTA** | `.btn-success` | Default | `linear-gradient(180deg, #10b981 0%, #059669 100%)` | `1px solid rgba(255, 255, 255, 0.18)` | `#ffffff` | `0 2px 6px rgba(16, 185, 129, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.22)` | `components.css:325` |
| | | `:hover` | `linear-gradient(180deg, #34d399 0%, #059669 100%)` | unchanged | `#ffffff` | `0 4px 16px rgba(16, 185, 129, 0.50); transform: translateY(-1px)` | `components.css:334` |
| | | `:active` | `linear-gradient(180deg, #059669 0%, #047857 100%)` | unchanged | `#ffffff` | `0 1px 3px rgba(16, 185, 129, 0.40); transform: translateY(0) scale(0.98)` | `components.css:343` |
| **Secondary Button** | `.btn-secondary` | Default | `#182234` | `1px solid #243044` | `#94a3b8` | `--shadow-sm`, inset sheen | `components.css:351` |
| | | `:hover` | `#202d44` | `1px solid #334155` | `#ffffff` | `--shadow-md; transform: translateY(-1px)` | `components.css:361` |
| | | `:active` | `#151d2e` | unchanged | `#ffffff` | `transform: translateY(0) scale(0.98)` | `components.css:370` |
| **Ghost Button** | `.btn-ghost` | Default | transparent | transparent | `#94a3b8` | none | `components.css:377` |
| | | `:hover` | `rgba(255, 255, 255, 0.06)` | transparent | `#ffffff` | none | `components.css:382` |
| **Save Terminal CTA**| `.btn-save-project` | Default | `linear-gradient(to right, #2563eb, #3b82f6, #4f46e5)` | none | `#ffffff` | `0 4px 16px rgba(37, 99, 235, 0.35)` | `views.css:554` |
| | | `:hover` | `linear-gradient(to right, #3b82f6, #60a5fa, #6366f1)` | none | `#ffffff` | `0 6px 22px rgba(37, 99, 235, 0.50); transform: translateY(-1px)` | `views.css:561` |
| | | `:active` | unchanged | none | `#ffffff` | `transform: scale(0.98)` | `views.css:566` |
| **Bottom Add Plate**| `#btn-add-plate-bottom` | Default | `rgba(21, 29, 46, 0.40)` | `2px dashed #243044` | `#60a5fa` | none | `views.css:783` |
| | | `:hover` | `rgba(37, 99, 235, 0.08)` | `2px dashed #3b82f6` | `#ffffff` | `0 4px 12px rgba(37, 99, 235, 0.15); transform: translateY(-1px)` | `views.css:796` |
| **Add BOM Item** | `#btn-add-bom-item` | Default | `rgba(30, 41, 59, 0.70)` | `1px solid rgba(59, 130, 246, 0.30)` | `#60a5fa` | none | `views.css:809` |
| | | `:hover` | `rgba(37, 99, 235, 0.15)` | `1px solid #3b82f6` | `#ffffff` | `0 0 12px rgba(37, 99, 235, 0.25); transform: translateY(-1px)` | `views.css:821` |
| **Sidebar Nav Item**| `aside nav button` | Inactive | transparent | transparent | `#94a3b8` | none | `views.css:57` |
| | | `:hover` | `rgba(255, 255, 255, 0.04)` | `rgba(255, 255, 255, 0.06)` | `#f8fafc` | `transform: translateX(2px); i: scale(1.08)` | `views.css:73` |
| | | Active (`.bg-blue-600`)| `linear-gradient(90deg, rgba(37, 99, 235, 0.22) 0%, rgba(37, 99, 235, 0.08) 100%)` | `1px solid rgba(59, 130, 246, 0.40)` | `#ffffff` | `0 2px 10px rgba(37, 99, 235, 0.20), left indicator bar` | `views.css:91` |
| **Filter Chip (Inactive)** | `.project-filter-chip` | Inactive | `rgba(30, 41, 59, 0.60)` (`bg-slate-800/60`) | `1px solid rgba(51, 65, 85, 0.50)` (`border-slate-700/50`) | `#94a3b8` (`text-slate-400`); hover: `#ffffff` | radius: `0.5rem`; font-size: `11px`; font-weight: 600; padding: `0.25rem 0.625rem` | `index.html:605`, `app.js:1308` |
| **Filter Chip (Active)** | `.project-filter-chip` | Active | `rgba(37, 99, 235, 0.20)` (`bg-blue-600/20`) | `1px solid rgba(59, 130, 246, 0.40)` (`border-blue-500/40`) | `#60a5fa` (`text-blue-400`) | `--shadow-sm`; radius: `0.5rem`; font-size: `11px`; font-weight: 600 | `index.html:602`, `app.js:1306` |
| **Sidebar Logout** | `aside button[title*="Sair"]` / `.sidebar-logout-btn` | Default | transparent | transparent | `#94a3b8` (`text-slate-400`) | none (radius: `0.5rem`, padding: `0.375rem`) | `index.html:234`, `components.css:711` |
| | | `:hover` | `rgba(239, 68, 68, 0.12) !important` | transparent | `var(--rose-400, #f87171) !important` | `i { transform: rotate(-10deg) scale(1.1); }` | `views.css:149-156` |
| **Universal Disabled**| `button:disabled, .btn:disabled` | `:disabled` | unchanged | unchanged | unchanged | `opacity: 0.45 !important; cursor: not-allowed !important; transform: none; box-shadow: none; filter: grayscale(0.5);` | `components.css:390` |

### 6.3 Form Controls (Inputs, Selects, Gradient Wraps, Pickers)

| Control Type | CSS Selector | State | Background | Border & Outline | Text & Placeholder | Shadow & FX | File:Line |
|---|---|---|---|---|---|---|---|
| **Unified Form Input** | `.form-input-dark` | Default | `var(--bg-input, #0c121e) !important` | `1px solid var(--border-default, #243044) !important` | `var(--text-primary, #f8fafc); font-size: 0.875rem; line-height: 1.25rem;` | radius: `var(--radius-md, 0.5rem)`; `--transition-fast` | `components.css:82` |
| | | `:focus` | `var(--bg-input-focus, #0f1726) !important` | `var(--brand-500, #3b82f6) !important; outline: none !important;` | unchanged | `0 0 0 3px var(--brand-glow, rgba(37, 99, 235, 0.25)), var(--shadow-sm) !important` | `components.css:102` |
| **Text/Number Inputs** | `input[type="text"]`, `input[type="number"]` | Default | `#0c121e` | `1px solid #243044` | `#f8fafc`, placeholder `#64748b` | radius `0.5rem` | `components.css:74` |
| | | `:focus` | `#0f1726` | `#3b82f6`, `outline: none` | unchanged | `0 0 0 3px rgba(37, 99, 235, 0.25)` | `components.css:94` |
| | | `:focus-visible`| unchanged | `outline: 2px solid #3b82f6` | unchanged | `outline-offset: 2px` | `base.css:129` |
| | | `:disabled` | `rgba(12, 18, 30, 0.4)` | `rgba(255, 255, 255, 0.06)` | `opacity: 0.45; cursor: not-allowed` | none | `components.css:128` |
| **Native `<select>`** | `select` | Default | `#0c121e` + embedded SVG chevron | `1px solid #243044` | `#f8fafc; padding-right: 2.25rem; appearance: none;` | radius `0.5rem` | `components.css:138` |
| | | `:focus` | `#0f1726` + embedded SVG chevron | `#3b82f6; outline: none` | unchanged | `0 0 0 3px rgba(37, 99, 235, 0.25)` | `components.css:94` |
| **Select Gradient Wrap**| `.select-wrap::after` | Default | `linear-gradient(to right, transparent, #0c121e)` | none | pointer-events: none (prevents text clipping chevron) | width `3.5rem`, right `2.25rem` | `components.css:165` |
| | `.select-wrap:has(select:focus)::after` | Focus Parent | `linear-gradient(to right, transparent, #0f1726)` | none | pointer-events: none | smooth background sync | `components.css:239` |
| **Select Options** | `select option` | Default | `#0f172a` | none | `#f8fafc; padding: 0.625rem 0.875rem; font-size: 0.8125rem` | N/A | `components.css:148` |
| | `select option:checked` | Checked | `#1e293b` | none | `#f8fafc` | N/A | `components.css:156` |
| **Color Picker** | `input[type="color"]` | Default | transparent | `1px solid #243044` | width `2.5rem`, height `2.5rem`, cursor pointer | radius `0.5rem` | `components.css:244` |
| | | `:hover` | unchanged | `#3b82f6` | unchanged | `transform: scale(1.05)` | `components.css:259` |
| | `::-webkit-color-swatch` | Swatch | user color | none | padding `2px` | radius `calc(0.5rem - 2px)` | `components.css:264` |
| **Checkboxes** | `input[type="checkbox"]` | Default | `#1e293b` | `1px solid #334155` | `w-4 h-4 rounded cursor-pointer` | none | `index.html:1575` |
| | | `:checked` | brand blue fill | brand blue border | checkmark icon white | none | `index.html:1575` |
| **Info Tooltip Icon** | `.info-icon` | Default | inline-flex | none | cursor `help`, relative | N/A | `components.css:197` |
| | `.info-icon::after` | Hover Reveal | `#1e293b` | `1px solid #334155` | `#f8fafc; font-size: 0.6875rem` | `opacity: 1; translateY(0); shadow: 0 4px 14px rgba(0,0,0,0.5)` | `components.css:205` |

### 6.4 Slicer File Dropzone Interactive States
Located in `frontend/css/components.css:514-549`:

1. **Default State (`components.css:514-521`)**:
   - Background: `linear-gradient(180deg, rgba(20, 28, 44, 0.5) 0%, rgba(12, 18, 30, 0.7) 100%)`
   - Border: `2px dashed var(--border-default, #334155)`
   - Border Radius: `var(--radius-xl, 1rem)`
   - Transition: `var(--transition-normal)`
2. **Hover State (`components.css:523-534`)**:
   - Background: `linear-gradient(180deg, rgba(37, 99, 235, 0.08) 0%, rgba(17, 24, 39, 0.7) 100%)`
   - Border Color: `var(--brand-500, #3b82f6)`
   - Box Shadow: `0 0 25px rgba(37, 99, 235, 0.12)`
   - Icon Transform: `translateY(-2px)` with color `var(--brand-400, #60a5fa)`
3. **Active Dragover State (`components.css:536-548`, toggled by `app.js:2244-2263`)**:
   - Selector: `.dropzone.dragover`
   - Background: `linear-gradient(180deg, rgba(37, 99, 235, 0.20) 0%, rgba(17, 24, 39, 0.88) 100%) !important`
   - Border Color: `#60a5fa !important`
   - Box Shadow: `0 0 35px rgba(37, 99, 235, 0.30), inset 0 0 20px rgba(37, 99, 235, 0.15) !important`
   - Scale Transform: `transform: scale(1.015);`
   - Icon Transform: `transform: scale(1.15) translateY(-4px); color: #60a5fa;`

### 6.5 Status & Material Badges Directory
Every badge is styled via dedicated classes in `components.css:405-507`:
- **Common Badge Rules (`components.css:408-422`)**:
  - `display: inline-flex; align-items: center; gap: 0.375rem;`
  - Font Size: `var(--text-2xs, 0.6875rem)` (11px)
  - Font Weight: `var(--font-semibold, 600)`
  - Letter Spacing: `0.025em`
  - Padding: `0.2rem 0.6rem`
  - Border Radius: `var(--radius-full, 9999px)`
- **Dynamic Swatch Box (`views.css:653-665`)**:
  - Filament card color dots (`w-10 h-10 rounded-xl`) feature `box-shadow: 0 2px 8px rgba(0, 0, 0, 0.40), inset 0 0 0 1px rgba(255, 255, 255, 0.15)`.
  - `:hover`: `transform: scale(1.10); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.50);`

### 6.6 Modal Dialogs & Fullscreen Overlays
Configured in `frontend/css/components.css:555-577` and templates:

- **Backdrop Overlay (`index.html:104, 1323, 1400, 1483`)**:
  - Classes: `fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4`
- **Modal Window Container (`components.css:566-576`)**:
  - Background: `var(--bg-surface-elevated, #151d2e)`
  - Border: `1px solid var(--border-default, #243044)`
  - Border Radius: `var(--radius-2xl, 1.25rem)` (20px)
  - Box Shadow: `0 25px 60px -15px rgba(0, 0, 0, 0.85), 0 0 40px rgba(37, 99, 235, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important`
  - Animation: `animation: modalScaleIn 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards;`

### 6.7 Data Tables & Row Transitions
Defined in `frontend/css/components.css:583-611` and `views.css:251-337`:

- Table Layout: `width: 100%; border-collapse: collapse; text-align: left;`
- Table Header (`thead th`):
  - Height / Padding: `0.75rem 1rem`
  - Typography: `font-size: var(--text-2xs, 0.6875rem); font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;`
  - Color: `var(--text-secondary, #94a3b8)`
  - Border Bottom: `1px solid var(--border-default, #243044)`
- Table Body (`tbody td`):
  - Padding: `0.875rem 1rem`
  - Typography: `font-size: var(--text-xs, 0.75rem); color: var(--text-secondary, #94a3b8);`
  - Border Bottom: `1px solid var(--border-subtle, rgba(255, 255, 255, 0.06))`
- Row Hover State (`tbody tr:hover`):
  - Background: `rgba(37, 99, 235, 0.06) !important;`
  - Transition: `background-color var(--transition-fast, 150ms)`
- Table Action Icon Buttons (`views.css:326-337`):
  - Padding: `0.375rem; border-radius: var(--radius-sm, 0.375rem);`
  - Hover: `background-color: rgba(255, 255, 255, 0.05); transform: scale(1.12);`

### 6.8 Toast Notifications & Micro-Indicators
- **Host Container (`index.html:101`)**:
  - `fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none`
- **Dynamic Injection (`app.js:356-379`)**:
  - Background: `#1e293b` with border `1px solid #334155`
  - Shadow: `--shadow-lg`
  - Icon & Accent: Green checkmark for success, red alert for errors, blue info icon.
  - Dismiss: Auto-fade out after 3000ms.

### 6.9 Keyframes & Micro-Interaction Animations
Defined in `frontend/css/animations.css:11-109`:

1. `@keyframes fadeIn`: `opacity 0 -> 1, translateY(6px -> 0)` (Used for view transitions, duration `0.25s`).
2. `@keyframes modalScaleIn`: `opacity 0 -> 1, scale(0.95 -> 1), translateY(8px -> 0)` (Spring modal reveal, duration `0.24s`).
3. `@keyframes pulseGlow`: Smooth 2s breathing loop shifting box-shadow from 20px to 35px with `#60a5fa`.
4. `@keyframes pulseSuccess`: 2s emerald breathing loop shifting shadow from 15px to 28px with `#34d399`.
5. `@keyframes shimmer`: 1.8s gradient translation `-200% 0` to `200% 0` for skeleton loading.
6. `@keyframes spin`: 1s linear continuous rotation for loading spinners.

### 6.10 Catalog Cards, Cost Distribution & Production Failure Tracking

#### A. Hardware Printer & Filament Catalog Archetypes

| Component | Selector | State | Background Fill | Border | Radius | Box Shadow & Kinetic FX | File & Line |
|---|---|---|---|---|---|---|---|
| **Printer Card** | `.printer-card`, `#printers-grid .card-dark` | Default | `var(--bg-card, #151d2e)` | `1px solid #243044` | `0.75rem` | Flex column; transition: `--transition-normal` | `views.css:580` |
| | | `:hover` | unchanged | `rgba(59, 130, 246, 0.40) !important` | unchanged | `translateY(-2px); --shadow-lg, 0 0 20px rgba(37, 99, 235, 0.15) !important` | `views.css:590` |
| **Printer Machine Rate Box** | `.printer-rate-box` | Default | `radial-gradient(circle at center, rgba(37, 99, 235, 0.18) 0%, rgba(15, 23, 42, 0.80) 100%) !important` | `1px solid rgba(59, 130, 246, 0.40) !important` | `0.75rem` | `inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 2px 10px rgba(37, 99, 235, 0.15) !important; padding: 0.75rem;` Number: `#60a5fa`, `var(--font-mono)`, weight 900 | `views.css:598-614` |
| **Filament Card** | `.filament-card`, `#filaments-grid .card-dark` | Default | `var(--bg-card, #151d2e)` | `1px solid #243044` | `0.75rem` | Flex column; transition: `--transition-normal` | `views.css:635` |
| | | `:hover` | unchanged | `rgba(16, 185, 129, 0.40) !important` | unchanged | `translateY(-2px); --shadow-lg, 0 0 20px rgba(16, 185, 129, 0.15) !important` | `views.css:645` |
| **Filament Color Swatch Box** | `.filament-swatch` | Default | transparent (user hex dot inside) | none | `0.75rem` (`rounded-xl`) | 40x40px; `inset 0 0 0 1px rgba(255, 255, 255, 0.15), 0 2px 8px rgba(0, 0, 0, 0.40)`; transition: `--transition-fast` | `views.css:653` |
| | | Card `:hover` | unchanged | none | unchanged | `transform: scale(1.10); inset 0 0 0 1px rgba(255, 255, 255, 0.30), 0 4px 12px rgba(0, 0, 0, 0.50)` | `views.css:661` |
| **Filament Swatch Inner Dot** | `.filament-swatch-dot` | Default | dynamic inline user color | none | `9999px` (`rounded-full`) | 16x16px; `0 0 8px rgba(0, 0, 0, 0.60), inset 0 1px 1px rgba(255, 255, 255, 0.45)` | `views.css:668` |
| **Filament Cost/Gram Box** | `.filament-cost-box` | Default | `radial-gradient(circle at center, rgba(16, 185, 129, 0.18) 0%, rgba(15, 23, 42, 0.80) 100%) !important` | `1px solid rgba(16, 185, 129, 0.40) !important` | `0.75rem` | `inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 2px 10px rgba(16, 185, 129, 0.15) !important; padding: 0.75rem;` Number: `#34d399`, `var(--font-mono)`, weight 900 | `views.css:675-690` |
| **Filament Name Preview Box** | `#filament-name-preview-box` | Default | `rgba(12, 18, 30, 0.85)` | `1px dashed var(--border-default, #243044)` | `0.5rem` | `padding: 0.625rem 0.875rem; min-width: 0; overflow: hidden;` Shows real-time filament pill preview | `views.css:762` |

#### B. Visual Cost Distribution Mini-Bar (`.cost-distribution-bar`)
Defined in `frontend/css/views.css:544-551` and `frontend/index.html:1025-1030`. Positioned inside the Sticky Financial Summary Terminal directly below the Cost of Goods Sold (CPV) subtotal:

- **Outer Shell**: `box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.6);` (`views.css:545`), height `0.5rem` (`h-2`), border radius `9999px` (`rounded-full`), background `#0f172a` (`bg-slate-900`), border `1px solid #1e293b`.
- **Segmented Proportions**: Inner bars declare `.cost-distribution-bar > div { height: 100%; min-width: 2px; }` (`views.css:548-551`) with transitions `transition-all duration-300`:
  1. Material Filament (`.cost-bar-mat`): `bg-blue-500` (`#3b82f6`)
  2. Machine & Electricity (`.cost-bar-mach`): `bg-amber-500` (`#f59e0b`)
  3. Labor & Engineering (`.cost-bar-labor`): `bg-purple-500` (`#a855f7`)
  4. BOM Insumos & Hardware (`.cost-bar-bom`): `bg-cyan-500` (`#06b6d4`)
  5. Operational Overhead (`.cost-bar-over`): `bg-indigo-500` (`#6366f1`)

#### C. Scrap Tracking & Failure Dialog (`#modal-failure`)
Defined in `frontend/index.html:1483-1603`. Dedicated modal for tracking print failures, lost machine time, and discarded filament:

- **Backdrop**: `fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 hidden`
- **Dialog Window**: `card-dark max-w-lg w-full p-6 shadow-2xl animate-fade-in border border-rose-500/30 rounded-2xl space-y-4`
- **Icon Header Badge**: `w-10 h-10 rounded-xl bg-gradient-to-br from-rose-600/30 to-amber-600/20 text-rose-400 border border-rose-500/30 shadow-md` with `alert-triangle` icon.
- **Affected Plate Indicator**: `p-3 bg-slate-900/70 border border-slate-800 rounded-xl flex items-center justify-between`.
- **Live Loss Financial Impact Box (`index.html:1585-1593`)**:
  - Background: `bg-gradient-to-br from-rose-950/40 to-slate-900`
  - Border: `1px solid rgba(244, 63, 94, 0.30)` (`border-rose-500/30`)
  - Border Radius: `0.75rem` (`rounded-xl`)
  - Value (`#fail-cost-total`): `font-mono text-lg font-bold text-rose-300`
- **Submit Action**: `bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white rounded-xl text-xs font-bold shadow-md shadow-rose-600/20`.

---

## 7. Developer Maintenance & Fine-Tuning Guide (Cheat Sheet)

### 7.1 Recipe: How to Change the Primary Brand Accent Color
To replace the Royal Blue (`#3b82f6` / `#2563eb`) with another corporate hue (e.g., Purple or Cyan):

1. **Update CSS Custom Properties (`frontend/css/tokens.css:48-60`)**:
   - Change `--brand-500` (e.g. from `#3b82f6` to `#06b6d4`).
   - Change `--brand-600` (e.g. from `#2563eb` to `#0891b2`).
   - Change `--brand-700` (e.g. from `#1d4ed8` to `#0e7490`).
   - Update `--brand-surface`, `--brand-border`, and `--brand-glow` with corresponding RGBA values.
2. **Synchronize Tailwind Configuration**:
   - Edit `frontend/index.html:35-46` (`tailwind.config.theme.extend.colors.brand`).
   - Edit `frontend/preview.html:34-45` (`tailwind.config.theme.extend.colors.brand`).
3. **Verify Button Gradients (`frontend/css/components.css:301, 311`)**:
   - Update `.btn-primary` and `.btn-primary:hover` linear gradients.

### 7.2 Recipe: How to Adjust Card Elevation, Background, or Rim Lighting
1. **Change Card Background**:
   - Modify `--bg-card: #151d2e;` in `frontend/css/tokens.css:19`.
   - Update `darkcard: '#151d2e'` in `frontend/index.html:28` and `frontend/preview.html:27`.
2. **Tune Card Default Shadows**:
   - Adjust `--shadow-md` in `frontend/css/tokens.css:135`.
3. **Adjust Physical Rim Light (Top Highlight)**:
   - Edit `.card-dark::before` in `frontend/css/components.css:25-37`.
   - To increase brightness, change `rgba(255, 255, 255, 0.12)` to `0.20`.
   - To adjust thickness, modify `height: 1px;`.

### 7.3 Recipe: How to Modify Typography or Add a New Font
1. **Import Font Family**:
   - Add font link to `<head>` of `frontend/index.html:8-12` and `frontend/preview.html:7-11`.
   - Add `@import` to line 7 of `frontend/css/tokens.css`.
2. **Update Font Tokens (`frontend/css/tokens.css:110-111`)**:
   - Set `--font-sans` or `--font-mono`.
3. **Update Tailwind Font Stacks (`index.html:20-23`, `preview.html:19-22`)**:
   - Synchronize `tailwind.config.theme.extend.fontFamily`.
4. **Preserve Tabular Numeric Features**:
   - Ensure numeric inputs retain `font-feature-settings: 'tnum' 1, 'zero' 1; font-variant-numeric: tabular-nums;` in `base.css:69-70`.

### 7.4 Recipe: How to Tune the Sticky Financial Terminal Dimensions
1. **Adjust Sticky Viewport Height**:
   - Edit `views.css:371`:
     ```css
     @media (min-width: 1024px) {
         .summary-panel-card {
             max-height: calc(100vh - 6.5rem); /* Adjust 6.5rem offset here */
         }
     }
     ```
2. **Adjust Top Sticky Offset**:
   - Edit `views.css:347` (`top: 5rem`) and `index.html:787` (`sticky top-20`).
3. **Adjust Dual-Accent Top Bevel Colors**:
   - Edit `.summary-panel-card::before` gradient stops in `frontend/css/views.css:428`.

### 7.5 Recipe: How to Add or Tweak Status and Material Badges
1. **Adding a New Status Badge**:
   - Add new CSS rule in `frontend/css/components.css` following the pattern:
     ```css
     .badge-my_status {
         background: rgba(147, 51, 234, 0.14) !important;
         color: #c084fc !important;
         border: 1px solid rgba(147, 51, 234, 0.35) !important;
     }
     ```
   - Reference the new status in `frontend/js/app.js` (`renderProjectsTable`).
2. **Adding a New Material Polymer Badge**:
   - Add `.badge-mat-my_material` in `frontend/css/components.css:465-507`.
   - Add material color mapping in `frontend/js/app.js:2855`.

### 7.6 Recipe: How to Add Form Fields into the Aligned Subgrid
When introducing a new form column to `.form-aligned-grid` in `index.html` or `app.js`:

```html
<div class="form-col-aligned">
    <!-- Row 1: Header + Label + Help Tooltip -->
    <div class="form-label-header">
        <label class="text-xs font-medium text-slate-300">My Parameter</label>
        <span class="info-icon" data-tooltip="Description of parameter"></span>
    </div>

    <!-- Row 2: Input Container -->
    <div class="form-input-container">
        <input type="number" step="any" class="form-input-dark font-mono text-sm w-full" />
    </div>

    <!-- Row 3: Helper Text -->
    <span class="form-helper-text text-[11px] text-slate-500">Suggested default: 15%</span>
</div>
```
*Note*: This 3-child structure automatically locks into CSS subgrid rows without custom margin hacks.

### 7.7 Recipe: How to Customize Print & PDF Layout Styles
1. **Screen Web Print Styling**:
   - Modify `@media print` in `frontend/css/styles.css:24-122`.
   - To hide an additional element from paper output, append its selector to `.no-print, aside, header...` at line 46.
2. **Customer Quotation PDF Generator**:
   - Modify `backend/pdf_service.py:60-120`.
   - Update `colors.HexColor('#1e293b')` to mirror updated brand colors.

### 7.8 Critical Contract Invariants & Protected Identifiers
To prevent regression failures across automated test suites (`test_e2e_redesign.py`, `test_css_adversarial.py`, `test_frontend_inputs.py`), observe the following inviolable rules:

1. **Protected DOM IDs**:
   - Never rename or delete any of the 117 static IDs tested in `test_e2e_redesign.py:32-62` (including `#app-layout`, `#dropzone`, `#live-final-price`, `#live-net-profit`, `#plates-container`, `#bom-container`, `#modal-printer`, `#modal-filament`, `#form-settings`, `#dashboard-empty-banner`, `#filament-name-preview-box`).
   - Additional production modals and interactive containers outside the 117-suite baseline (such as `#modal-failure` for scrap tracking, and `#app-sidebar` for collateral sidebar state overrides) are equally protected and must maintain their contractual IDs.
2. **Do Not Add `overflow: hidden` to `.card-dark`**:
   - The `.card-dark` base rule must NEVER specify `overflow: hidden`. Doing so clips tooltips (`.info-icon::after`), select dropdowns, and elevated popovers (enforced by `test_css_adversarial.py`).
3. **Step Attribute on Numeric Inputs**:
   - All floating-point numeric inputs must declare `step="any"` or `step="0.01"` to prevent browser native `stepMismatch` validation errors on decimal inputs (enforced by `test_frontend_inputs.py`).
4. **Preserve Legacy Variable Aliases**:
   - Lines 28-35 in `frontend/css/tokens.css` must remain intact for backward compatibility.
5. **Preserve Stylesheet Import Cascade**:
   - The order `tokens.css` &rarr; `base.css` &rarr; `components.css` &rarr; `views.css` &rarr; `animations.css` in `frontend/css/styles.css` is mandatory.

### 7.9 Architectural Precedence: Dual-Layer Specificity & Tailwind Utility Overrides

#### 1. The Architectural Rationale
The frontend architecture operates a hybrid dual-layer styling stack combining **Tailwind CSS CDN** (Layer 1 utility engine) with **Modular CSS stylesheets** (`tokens.css`, `base.css`, `components.css`, `views.css`, `animations.css` in Layer 2).

Because Tailwind CDN injects standard utility classes at single-class specificity `(0, 1, 0)` without `!important`, modular CSS classes (`.card-dark`, `.btn-primary`, `.form-input-dark`, `.summary-panel-card`, `.badge-*`) intentionally enforce critical design system properties using `!important` declarations. This guarantees that accidental utility combinations or CDN timing variations cannot corrupt core brand gradients, glow halos, glassmorphism filters, or input contrast.

#### 2. The 5-Level Specificity Cascade Hierarchy

```
+-------------------------------------------------------------------------------------------------+
| LEVEL 5: Tailwind Inline Important Modifiers (!bg-purple-600) [Discouraged]                    |
+-------------------------------------------------------------------------------------------------+
| LEVEL 4: Modular Component Rules with !important (.btn-primary, .card-dark-featured, inputs)  |
|          --> Strictly enforces design tokens and overrides normal utility classes               |
+-------------------------------------------------------------------------------------------------+
| LEVEL 3: Standard Tailwind Utility Classes (p-4, flex, grid, gap-2, text-sm)                   |
|          --> Governs structural layouts, spacing, flex alignments, and responsive grids        |
+-------------------------------------------------------------------------------------------------+
| LEVEL 2: Global Base Element Resets (base.css)                                                  |
|          --> html, body, code, headings, input[type="number"], scrollbars                       |
+-------------------------------------------------------------------------------------------------+
| LEVEL 1: Master Root Design Tokens (tokens.css :root)                                          |
|          --> Raw CSS custom properties (--brand-500, --bg-canvas, --shadow-md)                  |
+-------------------------------------------------------------------------------------------------+
```

#### 3. Why Naive Utility Additions Fail
If a developer adds a Tailwind color class to an element with a modular component class:
```html
<!-- ANTIPATTERN: bg-purple-600 will be SILENTLY IGNORED by the browser -->
<button class="btn-primary bg-purple-600 hover:bg-purple-700">Submit Quote</button>
```
**Why this fails**: In `frontend/css/components.css:299-318`, `.btn-primary` declares:
```css
.btn-primary {
    background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
    color: #ffffff !important;
}
```
The `!important` declaration in `components.css` takes strict precedence over Tailwind's `.bg-purple-600 { background-color: rgb(147 51 234); }`.

#### 4. Prescribed Modification Workflows for Maintainers

1. **Global System-Wide Adjustments (Palette, Elevation, Radii)**:
   - **Action**: Modify the master token in `frontend/css/tokens.css` (e.g. `--brand-500`, `--bg-card`, `--radius-md`).
   - **Result**: All buttons, cards, borders, and input rings automatically update across the entire application simultaneously.
2. **Creating or Customizing Component Variants**:
   - **Action**: Add a semantic modifier class in `frontend/css/components.css` rather than chaining arbitrary Tailwind utilities:
     ```css
     /* Example: Adding a dedicated danger action CTA in components.css */
     .btn-danger {
         background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important;
         border: 1px solid rgba(255, 255, 255, 0.16) !important;
         color: #ffffff !important;
         box-shadow: 0 2px 6px rgba(220, 38, 38, 0.35) !important;
     }
     ```
3. **Safe Use of Tailwind Utilities**:
   - Tailwind utility classes are fully supported and encouraged for **structural layout** properties that do NOT specify `!important` in modular CSS:
     - Spacing & Padding: `p-4`, `px-6`, `py-2`, `m-2`, `space-y-4`
     - Flexbox & Grid: `flex`, `items-center`, `justify-between`, `grid`, `grid-cols-1 md:grid-cols-3`, `gap-4`
     - Responsive Visibility: `hidden`, `md:block`, `lg:flex`
     - Dimensions: `w-full`, `max-w-xl`, `h-10`
4. **Ad-Hoc One-Off Overrides (Exception Path)**:
   - If an isolated element strictly requires an ad-hoc color override in HTML without editing CSS files, use Tailwind's `!` important prefix modifier:
     ```html
     <button class="btn-secondary !bg-purple-900/40 !border-purple-500/50 !text-purple-300">
         Special Action
     </button>
     ```
   - *Note*: Use this sparingly; prefer token adjustments and component classes to maintain design consistency.
