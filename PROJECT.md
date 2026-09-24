# Project: 3D Print Calc Pro — SaaS Premium Dark Mode Redesign

## Architecture
3D Print Calc Pro is a modern web application for 3D printing cost calculation, workshop management, and quote generation:
- **Backend**: FastAPI with SQLite and SQLAlchemy, handling auth, user profiles, printers, filaments, projects, multi-plate slicer parsing, engineering cost engine, and WeasyPrint PDF generation.
- **Frontend Architecture**: Single Page Application (SPA) served statically via `/static`:
  - `frontend/index.html`: Main SPA containing 6 views (`dashboard`, `projects`, `project-editor`, `printers`, `filaments`, `settings`) and 3 modals (`auth-modal`, `modal-printer`, `modal-filament`).
  - `frontend/preview.html`: Standalone commercial PDF previewer with download/print actions and iframe integration.
  - `frontend/css/`: Modular CSS styling system with design tokens, base typography, component styles, view layouts, animations, and master `styles.css`.
  - `frontend/js/app.js`: Client application controller, reactive state, DOM renderer, live financial calculation engine, and resilient decimal input handlers.
  - `frontend/js/api.js`: REST client with JWT authentication interceptors and local storage caching.
  - `frontend/js/parsers/`: Client-side slicer parsers (`gcode.js` and `threemf.js`).
- **Data Flow & Navigation**:
  - Sidebar triggers `navigateTo(viewName)` which toggles the `hidden` class on `#view-${viewName}` sections.
  - Inputs in the Calculator dynamically call `recalcLiveSummary()` on `input` events, immediately updating the sticky live financial summary.
  - Slicer files (.3mf, .gcode, .gcode.3mf) dropped onto `#dropzone` extract plate metadata client-side and dynamically populate `#plates-container`.
  - Server endpoints mirror the client calculations via `backend/engine.py` for PDF generation and API persistence.

---

## Feature Inventory
Every feature from the Survey phase is mapped to an assigned milestone.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | SaaS Dark Mode Tokens | Obsidian canvas (`#080B11`, `#0B0F17`), slate surfaces (`#111827`, `#151D2E`), royal blue (`#2563EB`), emerald (`#10B981`), violet (`#8B5CF6`) | M1 | Survey CSS / R1 |
| 2 | Typography & Font Stack | `Inter` for UI, `JetBrains Mono` for tabular currency/metrics, clear hierarchy | M1 | Survey CSS / R1 |
| 3 | Elevated Cards & Depth | `.card-dark` with subtle top gradient hairline, elevation shadows, ambient glow | M1 | Survey CSS / R1 |
| 4 | Polished Inputs & Buttons | Input focus glow, royal blue CTA gradients, emerald save buttons, micro-interactions | M1 | Survey CSS / R1 |
| 5 | Status & Material Badges | Glowing status pills (`badge-*`) and material badges (`badge-mat-*`) including Resina | M1 | Survey CSS / R1 |
| 6 | Navigation & Layout Shell | Modern sidebar with active pill indicators, user profile footer, sticky topbar glassmorphism | M2 | Survey UI / R2 |
| 7 | Dashboard Visual Metrics | Operational stat cards (`stat-*-count`), visual indicators/charts, onboarding banner | M2 | Survey UI / R2 |
| 8 | Recent Quotes Table | Polished dashboard recent quotes (`dashboard-recent-projects`) with client avatars & quick actions | M2 | Survey UI / R2 |
| 9 | Projects List & Toolbar | Live search filter (`project-search-input`), status filter chips, modern table view | M2 | Survey UI / R2 |
| 10 | Slicer Dropzone UI | Interactive dropzone for `.3mf`, `.gcode`, `.gcode.3mf` with dragover glow and animations | M3 | Survey UI / R2 |
| 11 | Multi-Plate Manager | Dynamic plate cards in `#plates-container` with hardware/slicing parameter hierarchy | M3 | Survey UI / R2 |
| 12 | Bottom Add Plate Button | `#btn-add-plate-bottom` strictly placed after `#plates-container` with `addNewPlateRow()` | M3 | Survey Tests / R3 |
| 13 | BOM Insumos Manager | Dynamic BOM items in `#bom-container` with category icons, unit cost and live subtotal | M3 | Survey UI / R2 |
| 14 | Labor, Overhead & Terms Inputs | Ergonomic CAD/Post labor fields, overhead, tax, discount, shipping, payment/warranty terms | M3 | Survey UI / R2 |
| 15 | Sticky Financial Terminal | Mini-dashboard with cost distribution bar, neon final price box (`live-final-price`), emerald net profit | M3 | Survey UI / R2 |
| 16 | Printers Catalog & Rates | Visual grid in `#printers-grid` with machine hourly rate breakdown (depreciation, power, maintenance) | M4 | Survey UI / R2 |
| 17 | Printer Modal | Ergononmic `#modal-printer` preserving IDs (`cost`, `lifespan`, `power`, `maintenance`, `energy`) | M4 | Survey Tests / R3 |
| 18 | Filaments Catalog & Swatches | Visual grid in `#filaments-grid` with color swatch, material pill, cost/g, duplicate action | M4 | Survey UI / R2 |
| 19 | Filament Modal & Hex Picker | `#modal-filament` with `#filament-color-hex`, NO `#filament-name`, dynamic preview text | M4 | Survey Tests / R3 |
| 20 | Workshop Settings View | Form `#form-settings` with company identity, default rates, and commercial terms | M4 | Survey UI / R2 |
| 21 | Auth Modal & Registration | Frosted backdrop modal `#auth-modal` with login/register tabs, clean initial state | M4 | Survey UI / R2 |
| 22 | PDF Web Viewer Screen | Standalone `frontend/preview.html` with dark mode styling, download, print, error handling | M4 | Survey UI / R2 |
| 23 | DOM IDs & Numeric Constraints | Strict preservation of 117 DOM IDs, `step="any"` on decimals, no `min=1` with `step > 1` | M1–M4 | Survey Tests / R3 |
| 24 | Script Order & Integrations | Script sequence (`api.js` -> `gcode.js` -> `threemf.js` -> `app.js`), dynamic input typing | M1–M4 | Survey Tests / R3 |
| 25 | Full Test Suite Verification | 100% pass of 61+ automated tests (`pytest`) including all 16 frontend input tests | M5 | Survey Tests / R3 |
| 26 | Adversarial Hardening | Zero console errors, headless browser typing checks, edge case inputs, responsive audit | M5 | Acceptance Criteria |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Design System & CSS Foundation | Tokens, base typography, component styles (`.card-dark`, inputs, buttons, badges), animations, and Tailwind config | none | DONE |
| M2 | Shell, Dashboard & Projects List | Sidebar, Topbar, Dashboard metrics & recent table, Projects listing & search | M1 | DONE |
| M3 | Calculator Workspace & Financial Terminal | Slicer Dropzone, Multi-Plate Manager, BOM Table, Labor/Terms, Sticky Summary Panel | M1, M2 | DONE |
| M4 | Catalogs, Settings, Modals & Preview | Printers Grid & Modal, Filaments Grid & Modal, Workshop Settings, Auth Modal, preview.html | M1, M2 | DONE |
| M5 | E2E Test Pass & Adversarial Hardening | Pass 100% of automated tests (118/118 tests), adversarial coverage hardening, zero console errors | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### HTML ↔ JavaScript Contract Invariants
- **DOM IDs**: All 117 IDs cataloged in Survey Hand-off must remain intact in `frontend/index.html`.
- **Plate Container & Bottom Button**: `#btn-add-plate-bottom` MUST exist and appear AFTER `#plates-container` in DOM order.
- **Filament Modal**: `#filament-color-hex` MUST exist as `type="color"`. `#filament-name` text input MUST NOT exist.
- **Project Delivery Days**: `#proj-delivery-days` MUST exist in project editor form.
- **Terms Inputs**: `#proj-payment-terms`, `#proj-warranty-terms`, `#pref-payment-terms`, `#pref-warranty-terms` MUST exist.
- **Script Loading Order**:
  ```html
  <script src="/static/js/api.js"></script>
  <script src="/static/js/parsers/gcode.js"></script>
  <script src="/static/js/parsers/threemf.js"></script>
  <script src="/static/js/app.js"></script>
  ```
- **Numeric Step Attributes**:
  - `#filament-weight`: `type="number" step="any"`
  - `#filament-price`: `type="number" step="any"` or `step="0.01"`
  - `#printer-lifespan`: `type="number" step="any"`
  - `#printer-cost`: `type="number" step="any"` or `step="0.01"`
  - Universal Rule: No numeric input may have `min="1"` combined with `step > 1`.
- **Runtime Class Invariants**:
  - Views toggle via `.hidden`.
  - Modals toggle via `.hidden`.
  - Dropzone active state toggles `.dragover`.
  - Status badges use `.badge-${status}`.
  - Material badges use `.badge-mat-${matLower}`.

---

## Code Layout

- `frontend/css/`:
  - `tokens.css`: Color variables, typography, shadows, elevation, glow, radius, transitions.
  - `base.css`: Body styling, typography scale, custom scrollbars, text selection.
  - `components.css`: `.card-dark`, buttons, form inputs, tables, badges, dropzone, modals.
  - `views.css`: Sidebar, topbar, sticky financial summary card, plate rows, catalog items.
  - `animations.css`: Keyframe animations (`fadeIn`, `modalScaleIn`, `pulseGlow`).
  - `styles.css`: Master stylesheet importing all modular CSS files via `@import`.
- `frontend/index.html`: Core single page application markup.
- `frontend/preview.html`: Commercial quotation PDF previewer.
- `frontend/js/`:
  - `app.js`: State management, event handlers, procedural HTML renderers, financial calculations.
  - `api.js`: REST client.
  - `parsers/gcode.js`: Client-side G-code parser.
  - `parsers/threemf.js`: Client-side 3MF parser.
