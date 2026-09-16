# Task: Simplify this project into a minimal POS + inventory system for one women's clothing store

## Context

This repository (`omborxona_xisobi`) is a Django 5 + DRF + PostgreSQL backend (`back/`) and a Vue 3 + TypeScript + Pinia + Tailwind frontend (`front/`). It was built as a multi-tenant SaaS for construction-material stores. The client has now seen it and says it is **far too complex**.

The real client is **one small women's clothing store**: one shop, one stock location, one currency (UZS), a few employees. Your job is to turn this codebase into a **minimal, clean, easy-to-understand** system that does exactly what that store needs — and nothing more.

A new developer should be able to read the code and understand the whole system in one afternoon. That is the main quality bar.

## How to work

1. Create a new git branch `simplify` before changing anything. Never touch `main`.
2. Work in the phases described at the end. **At the end of every phase, stop, show me a short summary, and wait for my approval** before starting the next phase.
3. Assume there is **no production data**. You may delete old migrations and create fresh initial migrations. If you find evidence of real data (fixtures, dumps, deployment notes suggesting live use), stop and ask me first.
4. Reuse existing code where it is already simple and correct (auth, API client, design CSS, layout components, Excel export). Rewrite or delete where it is not. Do not preserve complexity just because it exists or is tested.
5. Do not add features that are not listed below. If you believe something important is missing, list it in your phase summary as a question — do not build it.

## Tech stack (keep)

- Backend: Django 5, Django REST Framework, SimpleJWT, PostgreSQL, drf-spectacular.
- Frontend: Vue 3, TypeScript, Vite, Vue Router, Pinia, Tailwind CSS, Axios.
- Add: `JsBarcode` on the frontend for rendering barcodes on labels.
- Deployment: a simple `docker-compose.yml` with `db`, `back`, `front`. Keep the backup script if it is simple.

## Remove completely

Remove these features and all related models, services, migrations, API endpoints, views, stores, tests, settings, and dependencies:

- Multi-tenancy: `tenants` app, `tenant_id` columns, PostgreSQL Row Level Security, `X-Tenant-Id` header, company switching, tenant middleware.
- Multiple warehouses, warehouse types, warehouse-level access rules, two-step transfers between warehouses, transit logic.
- `ltree` category tree and unlimited nesting. Categories become a flat list.
- Dynamic attribute definitions and JSONB attributes with live inheritance. Size and color become plain fields.
- Units of measure: `units` app, `pint`, `ProductUnit` ("1 bag = 50 kg"), unit conversion factors.
- Batches, expiry dates, FEFO allocation, stock reservations.
- FIFO cost layers (replaced by moving average cost, see below).
- Multi-currency, USD, exchange-rate history, Central Bank rate sync, Celery, Redis, Celery beat.
- Customer credit sales, credit markup, due dates, the `debts` app.
- Generic data import framework (`dataimport`), unless it is trivially small and useful for importing products from Excel — ask me.
- The separate `audit` app. The stock movement ledger and document records are the history.
- Document prefix settings, bank requisites and other tenant settings screens.
- Reference material notes about InvenTree (`promt.md`, `docs/inventree-analysis.md`, `docs/extraction-plan.md`, `NOTICE` if no InvenTree code remains). Verify that no copied code remains before deleting `NOTICE`.

## Required features

### 1. Users and roles

- JWT login (reuse existing).
- Two roles only:
  - **Admin (owner):** everything.
  - **Cashier:** POS sales, returns/exchanges, view products and stock. Cannot see purchase costs, profit, reports, suppliers, or expenses. Cannot change prices or confirm stock counts.
- Enforce permissions in the API, not only by hiding UI. Cost and profit fields must be absent from API responses for cashiers.
- Admin can create/deactivate users and reset passwords.

### 2. Catalog: products and variants

- `Category`: flat list, just a name.
- `Size` and `Color`: small reference tables managed by admin (seed defaults: XS, S, M, L, XL, XXL; and a handful of common colors). Sizes have a sort order.
- `Product` (the model/style): name, category, optional brand, optional short description, optional photo, sale price, active flag.
- `Variant` (the actual sellable item): product, size (nullable), color (nullable), SKU, barcode, optional sale-price override, `average_cost`, `stock_quantity`, `min_stock` (for low-stock alert), active flag.
- One product can have many variants. A product without sizes/colors has exactly one variant, created automatically and invisible to the user.
- **Variant matrix:** when creating or editing a product, the admin selects sizes and colors (multi-select) and the system creates every missing size × color combination. Existing variants are never deleted automatically; variants with stock or history can only be deactivated.
- The product form must show and edit **all** variants (not only the first one): a table with size, color, barcode, price override, stock, active.

### 3. Barcodes

- One barcode per variant (string, unique).
- If the item already has a factory barcode, the admin can scan or type it in.
- Otherwise the system generates an **internal EAN-13** code: prefix `200`, followed by a 9-digit zero-padded sequence, followed by a valid EAN-13 check digit. Use a database sequence or a locked counter so codes are never duplicated under concurrency.
- Scanner input: USB scanners act like a keyboard and send the code followed by Enter. Every scan field must handle this and must not submit a form.
- Lookup endpoint: `GET /api/variants/by-barcode/?code=...` (trim whitespace).

### 4. Label printing

- Print price labels from: a product page (choose quantity per variant) and a confirmed purchase (one label per received unit by default, editable before printing).
- Label size 40 × 30 mm by default (configurable width/height in mm in a simple settings file or admin setting).
- Label content: shop name (short), product name, size / color, price in UZS, barcode rendered with JsBarcode (EAN-13 format, digits below).
- Print through the browser with `@page` CSS so it works with any thermal label printer that has a driver (Xprinter, TSC, etc.). No printer-specific protocol.

### 5. Suppliers

- `Supplier`: name, phone, note.
- Outstanding balance = total of confirmed purchases − amount paid on those purchases − separate supplier payments.
- `SupplierPayment`: supplier, date, amount, note.
- Supplier page shows purchases, payments, and current balance.

### 6. Purchases (goods receiving)

- `Purchase`: number, date, supplier, status (`draft` → `confirmed`, or `cancelled`), note, total, amount paid.
- `PurchaseLine`: variant, quantity (integer), unit cost.
- Lines can be added by scanning a barcode or by searching products. While creating a purchase the admin can create a new product with its variant matrix without leaving the screen.
- Only drafts are editable.
- On confirm (in one database transaction): for each line, add a stock movement, increase `stock_quantity`, recalculate `average_cost`, then offer to print labels.
- Cancel a confirmed purchase only if enough stock remains; write reversing movements (never delete movements).

### 7. POS sales (cashier screen)

This is a dedicated fast screen, **not** a document form.

- Barcode input is always focused. Each scan adds the variant or increases quantity by 1.
- Cart shows name, size/color, quantity (editable), price, line total. Remove line button.
- Discount: optional per line or on the whole receipt, as percent or fixed amount. Admin can set a maximum discount percent that cashiers may give.
- Payment: cash, card, or mixed (cash part + card part must equal total). For cash, show change due.
- One "Complete sale" action creates and confirms the sale in one transaction, then shows the receipt.
- Selling more than available stock is blocked with a clear message.
- `Sale`: number, datetime, cashier, subtotal, discount total, total, cash amount, card amount, status (`completed`, `voided`).
- `SaleLine`: variant, quantity, unit price, discount amount, line total, **unit cost copied from `average_cost` at the moment of sale**, line cost.
- Receipt: 80 mm browser print layout with shop name, date/time, receipt number, lines, discount, total, payment split, cashier name, and a Code128 barcode of the receipt number (used for returns).
- Void: admin only, same day only, writes reversing movements. Otherwise use returns.

### 8. Returns and exchanges

- Start by scanning the receipt barcode or typing the receipt number.
- Select lines and quantities to return. Returned quantity per line cannot exceed sold quantity minus already returned quantity.
- `SaleReturn` references the original `Sale`; each `SaleReturnLine` references the original `SaleLine`.
- Stock goes back in at the **original line's unit cost** (not the sale price), and `average_cost` is recalculated with that cost.
- Refund amount per unit = the original line total ÷ original quantity (so discounts are respected). Refund method: cash or card.
- **Exchange** (for example a different size): one flow = a return plus a new sale; show the difference to pay or refund.
- Reports must subtract returns from revenue and cost of goods sold.

### 9. Stock ledger

- `StockMovement` is the single source of truth: variant, quantity change (+/−), reason (`purchase`, `purchase_cancel`, `sale`, `sale_void`, `return`, `count_adjustment`, `write_off`), reference to the source document (type + id), unit cost, user, created_at.
- Movements are never updated or deleted.
- `Variant.stock_quantity` is a cache updated **only** by one stock service function, inside the same transaction as the movement, with `select_for_update()` on the variant row.
- Provide a management command that recomputes `stock_quantity` from movements and reports any mismatch.

### 10. Stock count and write-offs

- `StockCount`: date, status (`draft` → `confirmed`), created by, note. Scope: all products or one category.
- Counting by scanning: each scan adds 1 to the counted quantity; manual correction allowed.
- Before confirming, show expected vs counted vs difference, and the difference value at average cost.
- On confirm: write `count_adjustment` movements. Shortages are losses in reports.
- `WriteOff` (damaged, lost): variant, quantity, reason text. Creates `write_off` movement; value counts as loss.

### 11. Expenses

- `Expense`: date, category (simple choices: rent, salary, utilities, other), amount, note.
- Used only to calculate net profit.

### 12. Reports (admin only)

- **Dashboard (today and this month):** revenue, number of receipts, average receipt, gross profit, low-stock count.
- **Sales report for a date range:**
  - Gross revenue, returns, net revenue, discounts given.
  - Cost of goods sold (sales cost − returns cost).
  - Gross profit = net revenue − COGS.
  - Losses (count shortages + write-offs).
  - Expenses.
  - Net profit = gross profit − losses − expenses.
  - Breakdown by payment method (cash / card), by category, by cashier.
- **Top-selling products** (by quantity and by profit) for a date range, grouped by product with a per-size/color breakdown.
- **Stock report:** current quantity per variant, stock value at average cost and at sale price, filter by category, low-stock filter.
- **Supplier balances.**
- Excel export for the sales report, stock report and stock movements (reuse the existing export helper; numbers must be written as numbers).

### 13. Fiscal receipt hook

Uzbekistan requires sales receipts to be registered with the tax system through a licensed online/virtual cash-register provider. The provider is not chosen yet.

- Create a small `FiscalProvider` interface (`register_sale`, `register_return`) with a `NullFiscalProvider` default that does nothing and logs.
- Call it after a sale or return is committed. Store the provider's response (receipt id / QR URL) on the sale or return when available.
- Do not implement any real provider.

## Money, quantities, and correctness rules

- Money: `DecimalField(max_digits=14, decimal_places=2)`, UZS only. Never use `float` for money anywhere, including the frontend (send and display as strings/formatted numbers).
- Quantities of clothing items are integers.
- Moving average cost on stock-in: `new_avg = (old_qty × old_avg + in_qty × in_cost) / (old_qty + in_qty)`. If `old_qty <= 0`, `new_avg = in_cost`. Round to 2 decimals.
- Every operation that changes stock or money runs in a single `transaction.atomic()` block.
- Confirmed documents are immutable. Corrections happen through cancel/void/return/adjustment, which write new movements.
- Document numbers are sequential per type and year, e.g. `KIR-2026-000001` (purchase), `SOT-2026-000001` (sale), `QAY-2026-000001` (return), `INV-2026-000001` (stock count).

## Target structure

Backend apps (merge or rename existing ones; keep each app small):

```
back/apps/
  core/        shared helpers: money fields, permissions, numbering, export
  accounts/    user, roles, auth endpoints
  catalog/     Category, Size, Color, Product, Variant, barcode generation
  inventory/   StockMovement, stock service, StockCount, WriteOff
  purchases/   Supplier, SupplierPayment, Purchase, PurchaseLine
  sales/       Sale, SaleLine, SaleReturn, SaleReturnLine, POS services, fiscal hook
  expenses/    Expense
  reports/     read-only report services and endpoints
```

- Business logic lives in `services.py` of each app. Views/serializers stay thin.
- Frontend pages: Login, Dashboard, POS, Returns, Products (list + form with variant matrix), Purchases, Suppliers, Stock, Stock count, Write-offs, Expenses, Reports, Users, Settings (shop name, label size, max cashier discount).
- Sidebar menu must be role-aware.
- UI language: **Uzbek (Latin script)**. Code identifiers: English. Code comments: short and in Uzbek, only where the "why" is not obvious. Remove long essay-style docstrings that explain historical design decisions or InvenTree comparisons.

## Tests

Delete tests for removed features. Keep tests focused on money and stock correctness. Required test scenarios (pytest or Django TestCase):

1. Creating a product with sizes S, M, L and colors black, white produces exactly 6 variants, each with a unique and **valid** EAN-13 barcode.
2. A confirmed purchase of 5 units of each variant at 150 000 UZS gives total stock 30 and average cost 150 000.
3. A second purchase at a different cost recalculates average cost correctly.
4. Selling 2 units at 250 000 with a 10% discount stores the correct line total, unit cost, line cost, and profit.
5. Selling more than stock is rejected and nothing is written.
6. Returning 1 of those units restores stock, uses the original unit cost, refunds the discounted price, and the sales report shows reduced net revenue and COGS.
7. Cannot return more than was sold (including across multiple returns).
8. An exchange (return M, sell L) produces correct stock for both variants and the correct payment difference.
9. A stock count with a shortage writes adjustment movements and the loss appears in the report.
10. A cashier's API responses contain no cost or profit fields, and cashier requests to reports/purchases return 403.
11. The stock recompute command finds no mismatch after all of the above.
12. Two concurrent sales of the last unit: only one succeeds.

## Documentation

- Rewrite `README.md`: what the system does (one paragraph), how to run locally, how to run tests, default demo users.
- Add `docs/how-it-works.md`: one page explaining the data model, the flow purchase → stock → sale → return → reports, and the profit formulas above.
- Replace `docs/roadmap.md` with a short list of what is done and the open questions.
- Provide a `seed_demo` management command: a few categories, sizes, colors, ~10 clothing products with variants, one supplier, one purchase, several sales, one return, admin and cashier users.

## Phases

**Phase 0 — Analysis (no code changes).**
Read the whole repository. Produce a table: every existing app / major file → keep, simplify, merge into, or delete, with a one-line reason. List risks and any questions. Stop and wait.

**Phase 1 — Removal and new backend skeleton.**
Create the branch, delete removed features, restructure apps, write the new models and fresh migrations, update settings and requirements. The project must start and `manage.py check` must pass. Stop and wait.

**Phase 2 — Backend services and API.**
Catalog with variant matrix and barcode generation, inventory service, purchases, sales/POS, returns/exchanges, stock count, write-offs, expenses, reports, permissions, fiscal hook. Write the required tests; all must pass. Stop and wait.

**Phase 3 — Frontend.**
Remove unused views, stores and API modules. Build/adapt the pages listed above, POS and returns screens, label and receipt print layouts. `npm run build` and type-check must pass with no errors. Stop and wait.

**Phase 4 — Cleanup and docs.**
Remove dead code, unused dependencies (backend and frontend), and leftover settings. Seed command, README, `how-it-works.md`, docker-compose check. Give me a final summary: what was removed (with rough line counts before/after), what was built, how to demo it in 5 minutes, and open questions.
