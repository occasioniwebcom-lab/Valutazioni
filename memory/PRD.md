# PRD — GameLife Valutazioni (VideogamesItalia)

## Original problem statement
Shop owner wants a light, fast mobile app: type a game title (or part of it) and get a
table of similar games from GameLife.it showing cover, prezzo nuovo, prezzo usato, and
prezzo di valutazione ("buyback" — what the shop pays). Plus: search history and a
customer "preventivo" (quote) page — minimal, small cover, personalized with the
VideogamesItalia logo, shareable online or printable. Single-user, Italian.

## Architecture
- **Frontend:** Expo Router (React Native), 3 bottom tabs — Cerca / Cronologia / Preventivo.
  Fonts: Geist + Geist Mono (prices). Clean/light "sage" theme from design_guidelines.json.
  Progressive price loading (skeleton → values) at client concurrency 3, per-row retry.
  Preventivo state persisted locally (AsyncStorage). PDF via expo-print + expo-sharing.
- **Backend:** FastAPI + Playwright (headless Chromium) scraping gamelife.it (Odoo).
  Playwright bypasses the site's Cloudflare WAF from this environment (plain HTTP is 403).
  Prices are server-rendered on a *fresh context's first load*; the site is intermittent so
  `/api/product` retries up to 3x (fresh context each) and caches to MongoDB for 24h.
- **DB (MongoDB):** `games` (url-unique price cache + history via viewed_at, soft-delete via
  deleted_at), `searches` (query log).

## Key endpoints
- `GET /api/search?q=` → fast grid list (title, url, image, priced) + merges cached prices.
- `GET /api/product?url=&title=&image=` → nuovo/usato/buyback (retry + cache), records history.
- `GET /api/history` / `DELETE /api/history` (soft clear).

## Implemented (2026-06)
- Live search returning a price table with highlighted Buyback (valutazione) pill.
- Progressive per-row price fetching with retry + 24h cache (repeat searches instant).
- Search/valuation history grouped by date; clear history (soft delete).
- Preventivo: add/remove games, customer name, total valutazione, share/print PDF with
  the VideogamesItalia logo + small covers.

## Known constraints
- Game covers are hotlinked from gamelife.it (Cloudflare) — blank when loaded from this
  datacenter IP but render on real devices / residential IPs. Logo loads everywhere.
- The source site occasionally omits price data on a request; the row shows "Riprova".

## Backlog / next
- P1: Cache game covers via Emergent Object Storage so they always render (incl. previews).
- P1: "Solo giochi" filter chip to hide accessories (amiibo/custodie) from results.
- P2: Editable/override valutazione per item in the preventivo; margin/percent controls.
- P2: Export preventivo history; multiple saved preventivi.
