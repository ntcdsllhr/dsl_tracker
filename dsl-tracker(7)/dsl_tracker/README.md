# DSL Customer Technical Records

A field-technician-focused system for tracking **technical** information on
DSL government subscribers in Lahore: customer/contact details, DSL service
configuration, and physical copper-pair infrastructure. Deliberately **excludes
all billing/financial data** — this is a technical reference tool, not a
billing system.

Built with Django + Django REST Framework on the backend and Svelte + Vite on
the frontend, ready to deploy on PythonAnywhere with MySQL (free tier) or
PostgreSQL (paid tier).

## What's included

- **Data-integrity business rules**, enforced at the database level (not just
  the UI): customer User IDs must be unique, modem serial numbers must be
  unique, and each port on a given MSAG card can only be assigned to one DSL
  service at a time. Ports are validated to the real-world range of a 64-port
  line card (0–63) — assigning port 64 or -1 is rejected with a clear error.
- **MSAG-centric reporting**: the dashboard leads with **Customers by MSAG**
  and a **card capacity** view (used/64 ports per card, with a visual fill
  bar that turns amber at 75% and red at 100%) — geography (city/region) is
  still filterable but is no longer the primary lens, since MSAG/card is
  what actually matters for provisioning and fault-finding. The customer
  list can also be **sorted by MSAG or by port number** (low-to-high or
  high-to-low) for working through a cabinet or card in physical order.
- **Weekly / 15-day / monthly reports**: a dedicated reporting endpoint and
  UI toggle on the Activity page — total events, new customers, faults
  reported/resolved, and created/updated counts for whichever period you
  pick, plus who was most active in that window.
- **Fault / Complaint history** for every customer — a lean ticket (fault
  description, status, assigned technician, resolution notes) with a
  self-managing `resolved_at` timestamp. Reported and resolved right from the
  customer's page, with an open-fault ⚠ badge on the customer list and a
  "Faults only" filter for quick triage. Every status change is captured by
  the same audit trail as everything else, so it shows up automatically in
  both that customer's History tab and the org-wide Activity feed — no
  separate tracking system to maintain.
- **Dashboard** with summary tiles and Chart.js visualizations: DSL line status
  breakdown, copper pair condition, a 7-day change counter, and a Recent
  Activity widget — backed by a single aggregated `GET /api/dashboard/stats/`
  endpoint so it stays fast regardless of dataset size.
- **Full audit trail / change history**: every create, update, and delete on
  a customer, their DSL service, copper pair, or complaint is logged with a
  field-level diff (old → new) and a human-readable summary. Each customer's
  detail page has a **History** tab showing their complete timeline.
- **Activity & Reporting page**: an org-wide, filterable feed of every change
  across the system (by record type, action, actor, date range, free-text
  search), a 14-day activity trend chart, action/entity totals, and the
  periodic report described above.
- **Customer search/list** with free-text search and status/city filters.
- **Customer detail/edit** covering customer → DSL service → copper pair →
  fault history in one screen.
- A sidebar/bottom-nav layout (desktop sidebar, phone bottom tab bar) with a
  cohesive teal/navy visual theme.
- **Phone-optimized throughout**: bottom tab bar navigation, tap-friendly
  card lists in place of cramped tables, single-column forms, and iOS
  zoom-on-focus fixes.

## Why these fields

The data model (see `backend/customers/models.py`) is informed by the
reference CRM screenshots supplied for this project — region/city/exchange
groupings, MSAG identifiers, and phone/address search patterns a technician
already relies on — but re-scoped to a lean technical record:

- **Customer**: name, department, address, city, contact info, subscriber
  ID/tax/dept codes. No account balance, invoices, or payment data.
- **DSLService**: package, technology (ADSL2+/VDSL2/SHDSL), MSAG + card/port,
  IP, modem serial, line status.
- **CopperPair**: cabinet code, pair number, binder group, distribution
  point, cable length, physical condition, notes.

## Project layout

```
dsl_tracker/
├── backend/            Django project (API + admin + serves built frontend)
│   ├── dsltracker/     settings, root urls, wsgi
│   ├── customers/      models, serializers, views, filters, admin, seed command
│   └── requirements.txt
├── frontend/            Svelte + Vite app (technician UI)
│   └── src/
│       ├── App.svelte
│       ├── lib/api.js   fetch client with token auth
│       └── components/  Login, CustomerList, CustomerDetail
└── deploy/
    └── pythonanywhere.md   full deployment walkthrough
```

## Local development

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults to SQLite, DEBUG=True
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data     # optional sample records
python manage.py runserver
```

Want MySQL locally instead of SQLite (closer to production, matching
PythonAnywhere's free tier)? Run
`docker compose up -d` from the repo root, then set `DATABASE_URL` in
`backend/.env` per the comment at the top of `docker-compose.yml`.

Run the test suite (59 tests covering auth, CRUD, search/filtering, MSAG/
port sorting, the full activity-logging audit trail, fault/complaint
lifecycle tracking, the port/user-ID/modem-serial business rules, MSAG
capacity reporting, the periodic report endpoint, and a guardrail that
fails if any billing/financial field ever appears in an API response):

```bash
python manage.py test customers
```

API is now at `http://127.0.0.1:8000/api/`, admin at `/admin/`.

Get an auth token for the frontend to use:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -d "username=<you>&password=<your password>"
```

(The Svelte login screen does this for you automatically — the curl above is
just for quick API testing.)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` requests
to Django on port 8000 (see `vite.config.js`), so both need to be running.

## API overview

All endpoints require a DRF token (`Authorization: Token <token>`), obtained
from `POST /api/auth/token/`.

| Endpoint | Purpose |
|---|---|
| `GET /api/customers/` | List/search customers. Supports `?search=`, `?status=`, `?city=`, `?region=`, `?phone=`, `?user_id=`, `?msag=`, `?pair_number=`, `?is_active=` |
| `GET /api/customers/<id>/history/` | Full audit trail for one customer — their profile, DSL service, copper pair, and complaint changes, newest first |
| `GET /api/complaints/` | Fault/complaint tickets. Supports `?customer=`, `?status=` (`OPEN`/`IN_PROGRESS`/`RESOLVED`/`IRRELEVANT`) |
| `POST /api/complaints/`, `PATCH /api/complaints/<id>/` | Report a fault / update its status, assignee, or resolution notes. `resolved_at` is set and cleared automatically based on `status` — no need to send it. |
| `GET /api/customers/?has_open_complaint=true` | Filter the customer list to only those with an open or in-progress fault |
| `GET /api/dashboard/stats/` | Aggregated counts for the dashboard: totals, status/technology/condition breakdowns, customers by city/region, recent activity |
| `GET /api/activity/` | Org-wide, filterable activity feed. Supports `?customer=`, `?entity_type=` (`CUSTOMER`/`DSL_SERVICE`/`COPPER_PAIR`), `?action=` (`CREATED`/`UPDATED`/`DELETED`), `?actor=`, `?created_after=`, `?created_before=`, `?search=`. Read-only — audit logs can't be edited or deleted via the API. |
| `GET /api/activity/stats/` | Reporting aggregates: total events, action/entity breakdowns, 14-day daily trend, top actors |
| `GET /api/activity/report/?period=weekly\|fortnightly\|monthly` | Periodic business report for the chosen window: new customers, faults opened/resolved, created/updated counts, top actors |
| `GET /api/customers/<id>/` | Full nested record (customer + DSL service + copper pair) |
| `POST /api/customers/` | Create a customer |
| `PATCH /api/customers/<id>/` | Update customer fields |
| `DELETE /api/customers/<id>/` | Delete a customer (cascades to DSL service + pair) |
| `POST /api/dsl-services/`, `PATCH /api/dsl-services/<id>/` | Create/update a customer's DSL service |
| `POST /api/copper-pairs/`, `PATCH /api/copper-pairs/<id>/` | Create/update a DSL service's copper pair |
| `GET /api/regions/`, `/api/cities/`, `/api/exchanges/`, `/api/msags/` | Lookup data for filters/forms |

## Upgrading an existing deployment

Migration `0004` changes `msag_port` from free text (e.g. `"P12"`) to a real
integer (0–63) and adds uniqueness constraints on `user_id`, `modem_serial`,
and port-per-card. If you already have DSL service records from before this
update, `python manage.py migrate` will fail trying to convert old
non-numeric port values — the simplest fix is to flush and reseed demo data
(`python manage.py seed_data --flush`) or, for real production data, update
existing rows to plain integers before migrating.

## Deploying

See [`deploy/pythonanywhere.md`](deploy/pythonanywhere.md) for the full
step-by-step PythonAnywhere + MySQL walkthrough (database setup,
environment variables, building the frontend into the Django app, WSGI
config, and redeploy instructions). If you're replacing an existing site on
the same PythonAnywhere account, start with that guide's **Section 0** —
it covers backing up and removing the old web app so the new one can take
over the domain.

## Notes on the boilerplate reference

This was scaffolded as a focused Django + DRF + Svelte project rather than a
literal clone of the full `django-boilerplate` / SaaS Pegasus template, since
that template bundles a lot of SaaS-specific scaffolding (billing, teams,
Stripe) that's explicitly out of scope here. If you'd like the full
boilerplate's auth/teams/allauth conventions layered on top of these models,
the `customers` app can be dropped straight into a `django-boilerplate`
checkout with no changes — it has no dependency on this project's specific
`dsltracker` settings module beyond `INSTALLED_APPS`.
