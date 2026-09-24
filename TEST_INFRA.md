# 3D Print Calc Pro — E2E Testing Infrastructure Specification (TEST_INFRA.md)

**Version:** 1.0.0  
**Status:** Authoritative  
**Standard:** 4-Tier Opaque-Box Quality Assurance Methodology  
**Target Application:** 3D Print Calc Pro (SaaS Dark Mode UI/UX Redesign)  
**Execution Engine:** `pytest` + `FastAPI TestClient` + `BeautifulSoup4` + Headless Browser Runner  

---

## 1. Quality Architecture & 4-Tier Methodology

The testing infrastructure guarantees 100% functional integrity, strict DOM contract preservation, numerical precision, and SaaS-grade Dark Mode visual compliance across all 26 inventoried features. Testing follows an **opaque-box** contract-first methodology where tests observe interfaces, network contracts, DOM structures, and end-to-end calculations rather than internal implementation details.

```
       ┌────────────────────────────────────────────────────────┐
       │         TIER 4: Real-World Application Scenarios       │
       │    End-to-end multi-plate jobs, quote-to-PDF lifecycle, │
       │     bulk production batches, multi-tenant isolation    │
       └───────────────────────────▲────────────────────────────┘
                                   │
       ┌───────────────────────────┴────────────────────────────┐
       │       TIER 3: Cross-Feature Combinations & Pairs       │
       │  Multi-plate + BOM + Labor + Tax + Margin + Discount;  │
       │  Slicer parser -> Plate generation -> Financial engine │
       └───────────────────────────▲────────────────────────────┘
                                   │
       ┌───────────────────────────┴────────────────────────────┐
       │        TIER 2: Boundary & Corner Stress Cases          │
       │  Nullish coalescing (0% tax), division by zero guards, │
       │  extreme decimals ("56,50"), step="any" stepMismatch   │
       └───────────────────────────▲────────────────────────────┘
                                   │
       ┌───────────────────────────┴────────────────────────────┐
       │        TIER 1: Feature Coverage (>=5 / feature)        │
       │  26 Features x >=5 tests = 130+ exhaustive test specs  │
       │  DOM IDs (117), CSS tokens, Badges, Modals, Forms      │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Tier 1: Feature Coverage (>= 5 Tests Per Feature)

Every one of the 26 features cataloged in `PROJECT.md § Feature Inventory` is mapped to at least 5 dedicated verification specifications.

### Feature 1: SaaS Dark Mode Tokens
- **T1.F01.01**: Verify CSS custom properties in `:root` define primary Obsidian canvas (`--bg-primary`, `#080B11` / `#0b1120` / `#0f172a`).
- **T1.F01.02**: Verify card surface tokens (`--bg-card`, `--bg-secondary`, `#111827` / `#1e293b`).
- **T1.F01.03**: Verify royal blue brand accents (`--accent`, `#3b82f6` / `#2563eb`).
- **T1.F01.04**: Verify emerald success tokens (`--success`, `#10b981`).
- **T1.F01.05**: Verify dark border tokens (`--border-color`, `#334155`).

### Feature 2: Typography & Font Stack
- **T1.F02.01**: Verify `font-sans` stack with antialiased rendering on `<body>`.
- **T1.F02.02**: Verify tabular figures and currency formatting utilize monospaced/numeric hierarchy.
- **T1.F02.03**: Verify uppercase tracking on category badges and section subtitles.
- **T1.F02.04**: Verify font weight contrast between metric labels (`text-xs text-slate-400`) and metric values (`font-bold text-white`).
- **T1.F02.05**: Verify text selection contrast in dark mode styling.

### Feature 3: Elevated Cards & Depth
- **T1.F03.01**: Verify `.card-dark` class is applied to all primary container cards across views.
- **T1.F03.02**: Verify `.card-dark` border definition (`1px solid #334155` or slate border).
- **T1.F03.03**: Verify hover border transition on `.card-dark` (`border-color: #475569`).
- **T1.F03.04**: Verify elevation shadows on `.card-dark` (`box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2)`).
- **T1.F03.05**: Verify backdrop blur and shadow on modal cards.

### Feature 4: Polished Inputs & Buttons
- **T1.F04.01**: Verify input focus transitions (`focus:outline-none focus:border-blue-500`).
- **T1.F04.02**: Verify primary action buttons have royal blue background and hover elevation (`bg-blue-600 hover:bg-blue-700`).
- **T1.F04.03**: Verify registration/save button styling (`bg-emerald-600 hover:bg-emerald-700`).
- **T1.F04.04**: Verify secondary action button styling (`bg-slate-800 hover:bg-slate-700 text-slate-300`).
- **T1.F04.05**: Verify button shadow glow on active/CTA buttons (`shadow-blue-600/30`, `shadow-emerald-600/30`).

### Feature 5: Status & Material Badges
- **T1.F05.01**: Verify presence and styling of `.badge-draft` (`#94a3b8`).
- **T1.F05.02**: Verify presence and styling of `.badge-quoted` (`#60a5fa`).
- **T1.F05.03**: Verify presence and styling of `.badge-approved` and `.badge-completed` (`#10b981`).
- **T1.F05.04**: Verify presence and styling of `.badge-in_production` (`#fbbf24`) and `.badge-cancelled` (`#f87171`).
- **T1.F05.05**: Verify material pills: `.badge-mat-pla`, `.badge-mat-petg`, `.badge-mat-abs`, `.badge-mat-tpu`, `.badge-mat-asa`, `.badge-mat-other`.

### Feature 6: Navigation & Layout Shell
- **T1.F06.01**: Verify `#app-layout` flex container enclosing `<aside>` sidebar and `<main>` content.
- **T1.F06.02**: Verify presence of all 5 navigation buttons: `#nav-dashboard`, `#nav-projects`, `#nav-printers`, `#nav-filaments`, `#nav-settings`.
- **T1.F06.03**: Verify user profile footer in sidebar (`#user-avatar`, `#user-display-name`, `#user-display-company`).
- **T1.F06.04**: Verify sticky topbar header with `#view-title` and `#topbar-actions`.
- **T1.F06.05**: Verify navigation view switching toggles `.hidden` across 6 view sections (`#view-dashboard`, `#view-projects`, `#view-project-editor`, `#view-printers`, `#view-filaments`, `#view-settings`).

### Feature 7: Dashboard Visual Metrics
- **T1.F07.01**: Verify `#stat-projects-count` exists and displays integer count.
- **T1.F07.02**: Verify `#stat-active-quotes` counts projects in `draft`, `quoted`, and `in_production` states.
- **T1.F07.03**: Verify `#stat-printers-count` displays total registered printers.
- **T1.F07.04**: Verify `#stat-filaments-count` displays total registered filaments.
- **T1.F07.05**: Verify `#dashboard-empty-banner` is displayed when 0 projects exist and hidden when projects exist.

### Feature 8: Recent Quotes Table
- **T1.F08.01**: Verify `#dashboard-recent-projects` container exists in `#view-dashboard`.
- **T1.F08.02**: Verify recent projects table renders client name, project name, date, and final price.
- **T1.F08.03**: Verify quick edit action (`editProject(id)`) is bound to each recent project row.
- **T1.F08.04**: Verify status badge is rendered inside recent table rows.
- **T1.F08.05**: Verify empty state message inside `#dashboard-recent-projects` when no projects exist.

### Feature 9: Projects List & Toolbar
- **T1.F09.01**: Verify `#project-search-input` input element exists with real-time `filterProjects()` listener.
- **T1.F09.02**: Verify `#projects-table-container` element exists in `#view-projects`.
- **T1.F09.03**: Verify status chips/filter buttons enable filtering by project status.
- **T1.F09.04**: Verify project deletion confirmation and API dispatch (`deleteProject(id)`).
- **T1.F09.05**: Verify "Novo Orçamento" CTA button opens `#view-project-editor` in clean creation mode.

### Feature 10: Slicer Dropzone UI
- **T1.F10.01**: Verify `#dropzone` element exists in `#view-project-editor`.
- **T1.F10.02**: Verify `#file-slicer-input` has `accept=".3mf,.gcode,.gcode.3mf"`.
- **T1.F10.03**: Verify dragover and dragleave events toggle the `.dragover` CSS class.
- **T1.F10.04**: Verify dropzone displays instructions for multi-plate 3MF and G-code.
- **T1.F10.05**: Verify dropzone click triggers `#file-slicer-input.click()`.

### Feature 11: Multi-Plate Manager
- **T1.F11.01**: Verify `#plates-container` element exists in DOM.
- **T1.F11.02**: Verify dynamic plate row contains inputs for plate name, quantity, print time, part weight, and purge weight.
- **T1.F11.03**: Verify printer selection dropdown updates plate printer and machine hourly rate.
- **T1.F11.04**: Verify filament selection dropdown updates plate filament and material cost.
- **T1.F11.05**: Verify single-plate cost pill (`#plate-cost-${idx}`) and summary text (`#plate-summary-text-${idx}`) update reactively.

### Feature 12: Bottom Add Plate Button
- **T1.F12.01**: Verify `#btn-add-plate-bottom` element exists in DOM.
- **T1.F12.02**: Verify `#btn-add-plate-bottom` has `onclick="addNewPlateRow()"`.
- **T1.F12.03**: Verify `#btn-add-plate-bottom` appears strictly **AFTER** `#plates-container` in DOM order.
- **T1.F12.04**: Verify clicking `#btn-add-plate-bottom` appends a new plate to `state.currentPlates`.
- **T1.F12.05**: Verify newly appended plate renders with default hardware configurations.

### Feature 13: BOM Insumos Manager
- **T1.F13.01**: Verify `#bom-container` element exists in DOM.
- **T1.F13.02**: Verify dynamic BOM row contains item name, category select, quantity, and unit cost.
- **T1.F13.03**: Verify BOM category select supports `Fixadores`, `Insertos`, `Eletrônica`, `Embalagem`, `Outros`.
- **T1.F13.04**: Verify BOM subtotal element (`#bom-subtotal-${idx}`) updates reactively (`qty * unit_cost`).
- **T1.F13.05**: Verify BOM row deletion (`removeBomRow(idx)`) recalculates base cost and financial summary.

### Feature 14: Labor, Overhead & Terms Inputs
- **T1.F14.01**: Verify `#proj-cad-hours` and `#proj-cad-rate` compute CAD labor cost.
- **T1.F14.02**: Verify `#proj-post-hours` and `#proj-post-rate` compute post-processing labor cost.
- **T1.F14.03**: Verify `#proj-overhead` adds fixed indirect costs to base cost.
- **T1.F14.04**: Verify `#proj-delivery-days` input exists with `type="number" step="1" min="1"`.
- **T1.F14.05**: Verify `#proj-payment-terms` and `#proj-warranty-terms` inputs exist and support custom terms.

### Feature 15: Sticky Financial Terminal
- **T1.F15.01**: Verify `#live-weight` and `#live-time` display aggregated print metrics.
- **T1.F15.02**: Verify `#live-material-cost`, `#live-machine-cost`, `#live-bom-cost`, `#live-labor-cost`, and `#live-overhead-cost` display cost components.
- **T1.F15.03**: Verify `#live-base-cost` equals sum of all 5 cost components.
- **T1.F15.04**: Verify `#live-suggested-price` adheres to `(Base Cost * (1 + margin%)) / (1 - tax%)`.
- **T1.F15.05**: Verify `#live-final-price` and `#live-net-profit` reflect discounts, taxes, and shipping in real time.

### Feature 16: Printers Catalog & Rates
- **T1.F16.01**: Verify `#printers-grid` element exists in `#view-printers`.
- **T1.F16.02**: Verify printer card displays total `machine_hourly_rate` formatted in BRL (`R$ X,XX/h`).
- **T1.F16.03**: Verify printer card breakdown shows depreciation/h, energy/h, and maintenance/h.
- **T1.F16.04**: Verify printer edit button triggers `editPrinter(id)`.
- **T1.F16.05**: Verify printer delete button triggers `deletePrinter(id)` with confirmation.

### Feature 17: Printer Modal
- **T1.F17.01**: Verify `#modal-printer` modal container exists and has `.hidden` initially.
- **T1.F17.02**: Verify `#printer-id` hidden input exists for edit vs create distinction.
- **T1.F17.03**: Verify `#printer-name` and `#printer-model` text inputs exist.
- **T1.F17.04**: Verify `#printer-cost` has `step="any"` or `step="0.01"` and `#printer-lifespan` has `step="any"`.
- **T1.F17.05**: Verify `#printer-power`, `#printer-maintenance`, and `#printer-energy` preserve required IDs and attributes.

### Feature 18: Filaments Catalog & Swatches
- **T1.F18.01**: Verify `#filaments-grid` element exists in `#view-filaments`.
- **T1.F18.02**: Verify filament card renders visual color swatch dot with `color_hex`.
- **T1.F18.03**: Verify filament card renders material pill (`badge-mat-${matLower}`).
- **T1.F18.04**: Verify filament card displays cost per gram formatted to 2 decimals (`f.cost_per_gram.toFixed(2)`).
- **T1.F18.05**: Verify filament card includes duplicate action button (`duplicateFilament(id)`).

### Feature 19: Filament Modal & Hex Picker
- **T1.F19.01**: Verify `#modal-filament` modal container exists and has `.hidden` initially.
- **T1.F19.02**: Verify `#filament-color-hex` input exists with `type="color"`.
- **T1.F19.03**: Verify `#filament-name` text input **DOES NOT EXIST** in modal.
- **T1.F19.04**: Verify dynamic preview text (`#filament-preview-text`) updates to `${material} ${color} - ${brand}`.
- **T1.F19.05**: Verify `#filament-weight` has `step="any"` and `#filament-price` has `step="any"` or `step="0.01"`.

### Feature 20: Workshop Settings View
- **T1.F20.01**: Verify `#form-settings` form container exists in `#view-settings`.
- **T1.F20.02**: Verify workshop identity inputs exist: `#pref-company`, `#pref-fullname`, `#pref-phone`, `#pref-pix`.
- **T1.F20.03**: Verify default economic rate inputs: `#pref-energy`, `#pref-margin`, `#pref-tax`, `#pref-failure`, `#pref-cad-rate`, `#pref-post-rate`.
- **T1.F20.04**: Verify default commercial terms inputs: `#pref-payment-terms`, `#pref-warranty-terms`.
- **T1.F20.05**: Verify submitting `#form-settings` invokes `handleSavePreferences(event)` and updates user state.

### Feature 21: Auth Modal & Registration
- **T1.F21.01**: Verify `#auth-modal` exists with frosted dark backdrop (`bg-black/80 backdrop-blur-sm`).
- **T1.F21.02**: Verify `#tab-login-btn` and `#tab-register-btn` switch between `#form-login` and `#form-register`.
- **T1.F21.03**: Verify `#form-login` inputs: `#login-email` and `#login-password`.
- **T1.F21.04**: Verify `#form-register` inputs: `#reg-name`, `#reg-company`, `#reg-email`, `#reg-password`.
- **T1.F21.05**: Verify clean initial state banner on registration (`Conta Inicial Limpa`).

### Feature 22: PDF Web Viewer Screen
- **T1.F22.01**: Verify `frontend/preview.html` exists and loads cleanly via `/static/preview.html`.
- **T1.F22.02**: Verify `#pdf-frame` iframe exists for document rendering.
- **T1.F22.03**: Verify `#btn-download` button exists with download action.
- **T1.F22.04**: Verify `#btn-print` button exists with print action.
- **T1.F22.05**: Verify `#error-state` container exists with `#error-title` and `#error-msg` for failure handling.

### Feature 23: DOM IDs & Numeric Constraints
- **T1.F23.01**: Verify all 117 cataloged static DOM IDs are present in `frontend/index.html`.
- **T1.F23.02**: Verify no duplicate ID attributes exist in `frontend/index.html`.
- **T1.F23.03**: Verify universal numeric rule: no numeric input has `min="1"` combined with `step > 1`.
- **T1.F23.04**: Verify `#filament-weight` and `#printer-lifespan` accept 1000 and 5000 without stepMismatch.
- **T1.F23.05**: Verify `#filament-price` and `#printer-cost` accept decimal values without stepMismatch.

### Feature 24: Script Order & Integrations
- **T1.F24.01**: Verify script sequence in `frontend/index.html`: `api.js` -> `gcode.js` -> `threemf.js` -> `app.js`.
- **T1.F24.02**: Verify `parsers/gcode.js` is loaded strictly **BEFORE** `parsers/threemf.js`.
- **T1.F24.03**: Verify `focusin` and `focusout` event handlers enable dynamic inputmode/type toggle.
- **T1.F24.04**: Verify `beforeinput` and `keydown` event listeners capture comma decimal entry.
- **T1.F24.05**: Verify `normalizeNumericInputs()` is called prior to payload dispatch.

### Feature 25: Full Test Suite Verification
- **T1.F25.01**: Verify all 16 tests in `tests/test_frontend_inputs.py` pass cleanly.
- **T1.F25.02**: Verify all 20 tests in `tests/test_api.py` pass cleanly.
- **T1.F25.03**: Verify all 8 tests in `tests/test_engine.py` pass cleanly.
- **T1.F25.04**: Verify all 17 tests in `tests/test_parsers.py` pass cleanly.
- **T1.F25.05**: Verify baseline test count of 61 passed tests is maintained with zero regressions.

### Feature 26: Adversarial Hardening
- **T1.F26.01**: Verify browser headless comma typing preserves values during input (`56,50`).
- **T1.F26.02**: Verify Brazilian thousand separators with comma (`1.200,50` -> `1200.50`).
- **T1.F26.03**: Verify currency prefixed string normalization (`R$ 3.499,90` -> `3499.90`).
- **T1.F26.04**: Verify empty strings and None values safely fall back to designated default values.
- **T1.F26.05**: Verify non-numeric input strings safely resolve without throwing uncaught JS exceptions.

---

## 3. Tier 2: Boundary & Corner Cases

>= 5 boundary tests per feature area targeting mathematical edge conditions, null coalescing, overflow, and format conversions.

### Area A: Zero Rates & Nullish Coalescing (Null vs Zero Safety)
- **T2.A.01**: `tax_rate_percent = 0.0` must stay `0.0%` (must not fall back to `6.0%` via logical OR).
- **T2.A.02**: `profit_margin_percent = 0.0` must stay `0.0%` (must not fall back to `30.0%`).
- **T2.A.03**: `custom_printer_hourly_rate = 0.0` must stay `0.0` (nullish check `== null`).
- **T2.A.04**: `custom_filament_cost_per_g = 0.0` must stay `0.0` (free material).
- **T2.A.05**: `cad_hours = 0` and `post_hours = 0` must produce `total_labor_cost = 0.0`.

### Area B: Division by Zero & Arithmetic Boundary Guards
- **T2.B.01**: `lifespan_hours = 0.0` on printer must yield `depreciation_per_hour = 0.0` without ZeroDivisionError.
- **T2.B.02**: `spool_weight_g = 0.0` on filament must yield `cost_per_gram = 0.0` without ZeroDivisionError.
- **T2.B.03**: `base_cost = 0.0` must yield `suggested_price = 0.0` and `effective_profit_margin_percent = 0.0`.
- **T2.B.04**: `tax_rate_percent = 99.0` (maximum boundary) must yield `tax_divisor = 0.01` without divide-by-zero.
- **T2.B.05**: `discount_percent = 100.0` (100% discount) must produce `subtotal_after_discount = 0.0` and `final_price = shipping_cost`.

### Area C: Extreme & Non-Standard Number Formats
- **T2.C.01**: Multi-period and comma strings: `1.234.567,89` parsed to `1234567.89`.
- **T2.C.02**: Spaces and currency prefix: `  R$  56,50  ` parsed to `56.50`.
- **T2.C.03**: Trailing dot values during typing (`56.`) preserved through `inputMode="decimal"`.
- **T2.C.04**: Negative inputs clamped to `0.0` by backend engine (`max(0.0, val)`).
- **T2.C.05**: Very small decimal costs (`cost_per_gram = 0.0001`) rounded without underflow.

### Area D: Input Validity & HTML5 Step Validation
- **T2.D.01**: Spool weight of exactly 1000g must not trigger HTML5 stepMismatch.
- **T2.D.02**: Spool weight of 750g and 2500g must not trigger HTML5 stepMismatch.
- **T2.D.03**: Printer lifespan of exactly 5000h must not trigger HTML5 stepMismatch.
- **T2.D.04**: Decimal prices (e.g. 89.90, 3499.99) must not trigger HTML5 stepMismatch.
- **T2.D.05**: Absence of `step > 1` combined with `min="1"` across all numeric inputs in `index.html`.

### Area E: API Authentication & Resource Boundaries
- **T2.E.01**: Unauthenticated API requests return HTTP 401 Unauthorized.
- **T2.E.02**: Malformed or expired JWT tokens return HTTP 401 Unauthorized.
- **T2.E.03**: Non-existent resource IDs (projects, printers, filaments) return HTTP 404 Not Found.
- **T2.E.04**: Missing required registration fields return HTTP 422 Unprocessable Entity.
- **T2.E.05**: Duplicate email registration returns HTTP 400 Bad Request with clear message.

---

## 4. Tier 3: Cross-Feature Combinations

Pairwise and multi-module interaction testing to verify that state updates and calculations flow seamlessly across features.

### Combination Matrix

| Combination ID | Integrated Features | Primary Verification Focus |
|---|---|---|
| **T3.C01** | Multi-Plate + BOM + Labor + Tax + Margin + Discount + Shipping | Full 7-stage financial formula parity between `engine.py` and `app.js` |
| **T3.C02** | Catalog Printer/Filament vs Custom Per-Plate Overrides | Plate 1 with catalog entities, Plate 2 with custom rates, correct subtotaling |
| **T3.C03** | Filament Duplicate -> Catalog Update -> Plate Selection | Duplicating a filament, changing color, and assigning new filament to a project plate |
| **T3.C04** | Workshop Defaults -> New Project Inheritance -> Custom Override | Setting workshop defaults in Settings, opening New Project, checking placeholder vs override |
| **T3.C05** | Multi-tenant Isolation (User A vs User B) | Total separation of projects, printers, filaments, and PDF downloads between tenants |
| **T3.C06** | Slicer Dropzone Parsing -> Multi-Plate Population -> Live Recalc | Dropping multi-plate 3MF file dynamically populates plates container and triggers live summary |
| **T3.C07** | Search Filter + Status Chips Interaction | Filtering projects list by search query while simultaneously filtering by status chip |
| **T3.C08** | Project Update -> Dashboard Operational Counters Update | Creating/updating/deleting project instantly updates dashboard stat counters |

---

## 5. Tier 4: Real-World Application Scenarios

End-to-end simulations of actual production workflows representing real print shop operations.

### Scenario 1: Industrial Job (3 Plates, BOM Fasteners, CAD/Post Labor, Custom Shipping & PDF)
- **Workflow**:
  1. User registers new workshop "Engenharia 3D Industrial".
  2. Registers Bambu Lab X1-Carbon (R$ 9.500, 5000h, 250W, R$ 0.85/kWh, R$ 2.50/h manutenção).
  3. Registers Filaments: ABS Preto (R$ 130/kg) and PA-CF Fibra de Carbono (R$ 280/kg).
  4. Creates Project "Gabarito Industrial":
     - Plate 1: 1x Base Estrutural, 4.5h, 180g ABS, 10% falha, Bambu X1C.
     - Plate 2: 2x Garras Móveis, 2.0h, 60g PA-CF, 5% falha, Bambu X1C.
     - Plate 3: 4x Pinos Guia, 0.8h, 25g ABS, 0% falha, Bambu X1C.
     - BOM Item 1: 8x Parafusos M4x16 Inox (R$ 0.65/un).
     - BOM Item 2: 4x Insertos de Latão M4 (R$ 1.20/un).
     - Labor: 2.5h CAD a R$ 80/h; 1.0h Pós-processamento a R$ 40/h.
     - Overhead: R$ 35,00.
     - Margin: 35%; Tax: 6%; Discount: 5%; Shipping: R$ 42,00.
  5. Save project and download Client PDF Quote (`/api/projects/{id}/pdf?type=client`).
  6. Download Technical Production Order (`/api/projects/{id}/pdf?type=technical`).
- **Assertion**: Validate exact financial calculations, HTTP 200 responses, PDF headers, and PDF binary integrity.

### Scenario 2: Zero-Tax Micro-enterprise (MEI / Hobbyist Miniature)
- **Workflow**:
  1. MEI Artisan registers account.
  2. Creates Ender 3 V2 (R$ 1.600, 4000h, 120W, R$ 0.80/kWh, R$ 1.00/h).
  3. Sets workshop default tax = 0%, margin = 50%.
  4. Creates Project "Miniatura Colecionável":
     - 1 Plate: 1x Dragão Articulado, 6.0h, 85g PLA Seda, 0% falha.
     - No BOM, no labor, no discount, no shipping.
     - Payment terms: "100% via PIX na aprovação".
     - Delivery days: 2 dias úteis.
  5. Verify tax amount is exactly R$ 0.00 and net profit equals margin markup.
  6. Verify PDF generation preserves 0% tax and PIX terms.

### Scenario 3: Bulk Commercial Production Order (10x Plate Quantity, Volume Discount)
- **Workflow**:
  1. Print farm manager registers account.
  2. Creates project "Chaveiros Promocionais":
     - Plate 1: Quantity = 10, print_time = 3.0h, weight = 120g PLA.
     - Total print time = 30.0h, total weight = 1200g.
     - Commercial discount = 15%.
     - Delivery days = 10.
  3. Verify quantity scaling in cost engine and live summary.
  4. Verify discount deduction and final price.

### Scenario 4: Filament Inventory Management & Hex Swatch Workflow
- **Workflow**:
  1. User registers 3 filaments: PLA Branco (#FFFFFF), PLA Preto (#000000), PETG Azul (#0066CC).
  2. Duplicates PETG Azul to create PETG Laranja:
     - Color changed to "Laranja", hex code changed to `#FF6600`.
     - Brand and spool specifications retained.
  3. Verify generated name is `PETG Laranja - [Brand]`.
  4. Verify grid renders new swatch with background `#FF6600`.

### Scenario 5: Multi-Tenant Data Isolation & Session Lifecycle
- **Workflow**:
  1. User A (Alice) registers and creates 2 printers, 3 filaments, 2 projects.
  2. User B (Bob) registers and receives an initially clean environment (0 printers, 0 filaments, 0 projects).
  3. Bob queries `/api/projects`, `/api/printers`, `/api/filaments` -> all return empty arrays.
  4. Bob attempts to access Alice's project by ID -> receives HTTP 404 Not Found.
  5. Bob attempts to download Alice's PDF quote -> receives HTTP 404 Not Found.
  6. Alice logs back in with valid credentials -> retrieves all her original assets.

---

## 6. Test Runner Configuration & Execution

### Commands
```bash
# Execute the complete E2E redesign test suite
python -m pytest tests/test_e2e_redesign.py -v

# Execute complete application test suite (existing + redesign)
python -m pytest -v

# Execute specific tier tests
python -m pytest tests/test_e2e_redesign.py -k "TestTier1" -v
python -m pytest tests/test_e2e_redesign.py -k "TestTier2" -v
python -m pytest tests/test_e2e_redesign.py -k "TestTier3" -v
python -m pytest tests/test_e2e_redesign.py -k "TestTier4" -v
```

### Exit Criteria
- **Zero test failures** (`61 existing + 35+ redesign E2E tests = 96+ tests passing`).
- **Zero console warnings or errors** during DOM parsing and input event simulation.
- **100% adherence** to contract invariants (117 DOM IDs, script order, step attributes).
