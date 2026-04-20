# Intelligence Query Engine

**Insighta Labs** demographic intelligence API — Stage 2 backend.

A production-ready Django REST Framework service that seeds, stores, and
queries 2026 demographic profiles with filtering, sorting, pagination, and
natural language search.

---

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 |
| Framework | Django 4.x + Django REST Framework |
| Database | PostgreSQL (Neon in production, local fallback) |
| Deployment | Gunicorn + WhiteNoise on Render/Railway |

---

## Setup

### 1 · Clone and create virtualenv

```bash
git clone git@github.com:Kelvyn2012/Intelligence_Query_Engine.git
cd Intelligence_Query_Engine
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2 · Environment variables

Create `.env` in the project root:

```dotenv
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=*
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

`DATABASE_URL` is the only required production variable.
Without it Django falls back to a local PostgreSQL connection using
`POSTGRES_DB`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

### 3 · Run migrations

```bash
python manage.py migrate
```

### 4 · Seed the database

```bash
python manage.py seed_profiles
```

The command is **idempotent** — re-running it will skip any profiles already
present and never create duplicates.

```bash
# Force a clean reseed (drops all existing profiles first)
python manage.py seed_profiles --clear
```

### 5 · Start development server

```bash
python manage.py runserver
```

### 6 · Run tests

```bash
python manage.py test api                          # all 67 tests
python manage.py test api.tests.NLParserTests      # parser only
python manage.py test api.tests.ProfileListTests   # filter/sort/pagination
python manage.py test api.tests.ProfileSearchTests # search endpoint
```

---

## API Reference

Base URL: `/api`

---

### `GET /api/profiles`

Returns a paginated, filtered, sorted list of profiles.

#### Filter parameters

| Parameter | Type | Example | Description |
|---|---|---|---|
| `gender` | string | `male` | `male` or `female` |
| `age_group` | string | `adult` | `child`, `teenager`, `adult`, `senior` |
| `country_id` | string | `NG` | ISO 3166-1 alpha-2 code |
| `min_age` | integer | `25` | Minimum age (inclusive) |
| `max_age` | integer | `60` | Maximum age (inclusive) |
| `min_gender_probability` | float | `0.8` | Gender confidence floor (0–1) |
| `min_country_probability` | float | `0.3` | Country confidence floor (0–1) |

All filters are **combinable** — every supplied condition must be satisfied.

#### Sort parameters

| Parameter | Values | Default |
|---|---|---|
| `sort_by` | `age`, `created_at`, `gender_probability` | `-created_at` |
| `order` | `asc`, `desc` | `asc` |

#### Pagination parameters

| Parameter | Default | Max |
|---|---|---|
| `page` | `1` | — |
| `limit` | `10` | `50` |

#### Response shape

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "data": [
    {
      "id": "0196c3f4-b8d0-7e2f-a1e5-2b3c4d5e6f70",
      "name": "Awino Hassan",
      "gender": "female",
      "gender_probability": 0.66,
      "age": 68,
      "age_group": "senior",
      "country_id": "TZ",
      "country_name": "Tanzania",
      "country_probability": 0.6,
      "created_at": "2025-10-01T12:00:00Z"
    }
  ]
}
```

#### Sample queries

```
GET /api/profiles?gender=male&country_id=NG&min_age=25
GET /api/profiles?age_group=adult&sort_by=age&order=desc&page=2&limit=20
GET /api/profiles?min_gender_probability=0.9&min_country_probability=0.5
GET /api/profiles?gender=female&age_group=teenager&country_id=KE
```

---

### `GET /api/profiles/search?q=<query>`

Natural language query endpoint.  
**Rule-based parsing only** — no AI, no LLMs.

Supports the same `page` / `limit` pagination parameters.

#### Supported query patterns

| Natural language query | Filters applied |
|---|---|
| `"young males"` | `gender=male`, `min_age=16`, `max_age=24` |
| `"females above 30"` | `gender=female`, `min_age=30` |
| `"people from angola"` | `country_id=AO` |
| `"adult males from kenya"` | `gender=male`, `age_group=adult`, `country_id=KE` |
| `"male and female teenagers above 17"` | `age_group=teenager`, `min_age=17` |
| `"seniors from nigeria"` | `age_group=senior`, `country_id=NG` |
| `"women under 25"` | `gender=female`, `max_age=25` |
| `"men older than 40"` | `gender=male`, `min_age=40` |
| `"children from ghana"` | `age_group=child`, `country_id=GH` |
| `"adults aged 30 to 50"` | `min_age=30`, `max_age=50` |

#### Parser rules

- **Gender tokens**: `male/males/men/man` → `male`; `female/females/women/woman` → `female`
- **Both genders together** (e.g. `"male and female"`) → no gender filter applied
- **`"young"`** → `min_age=16`, `max_age=24` (`"young"` is not a stored age group)
- **Age phrases**:
  - `above X` / `older than X` / `over X` → `min_age=X`
  - `below X` / `under X` / `younger than X` → `max_age=X`
  - `between X and Y` / `aged X to Y` → `min_age=X, max_age=Y`
- **Age groups**: `child/children/kid(s)`, `teenager/teen(s)`, `adult(s)`, `senior(s)/elderly`
- **Countries**: resolved by name or common alias (`usa`, `uk`, `britain`, `ivory coast`, `drc`, etc.)

#### Unrecognised query response

```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

### `GET /api/profiles/<uuid>`

Retrieve a single profile by UUID.

**200 OK**
```json
{ "status": "success", "data": { ... } }
```

**404 Not Found**
```json
{ "status": "error", "message": "Profile not found" }
```

---

### `DELETE /api/profiles/<uuid>`

Deletes a profile. Returns `204 No Content` on success, `404` if not found.

---

### `POST /api/profiles`

Creates a profile by name using external API aggregation
(Genderize + Agify + Nationalize).

```json
{ "name": "amara" }
```

**Idempotent** — returns `200` with existing data if the name already exists.

---

## Error responses

All error responses follow a consistent envelope:

```json
{ "status": "error", "message": "<description>" }
```

| Condition | HTTP status |
|---|---|
| Missing or empty required parameter | `400 Bad Request` |
| Invalid parameter type / out-of-range value | `422 Unprocessable Entity` |
| Resource not found | `404 Not Found` |
| External API unreachable | `502 Bad Gateway` |
| Unexpected server error | `500 Internal Server Error` |

---

## Database schema

```
profiles
├── id                  UUID v7, primary key
├── name                VARCHAR(255), unique, indexed
├── gender              VARCHAR(10), indexed
├── gender_probability  FLOAT, indexed
├── sample_size         INT, nullable
├── age                 INT, indexed
├── age_group           VARCHAR(10), indexed
├── country_id          VARCHAR(10), indexed
├── country_name        VARCHAR(100)
├── country_probability FLOAT, indexed
└── created_at          TIMESTAMPTZ auto, indexed
```

**Composite indexes**: `(gender, age_group)`, `(gender, country_id)`,
`(country_id, age_group)`, `(age, gender)`.

---

## Deployment

```
# Procfile (Render / Railway)
release: python manage.py collectstatic --noinput && python manage.py migrate
web:     gunicorn genderize_project.wsgi --bind 0.0.0.0:$PORT --log-level debug --capture-output
```

After first deploy, seed via the service shell:

```bash
python manage.py seed_profiles
```

---

## Project layout

```
api/
├── countries.py              ISO code ↔ name mapping + NLP lookup table
├── filters.py                Filter/sort/validate query params
├── models.py                 Profile model (UUID v7, indexed fields)
├── pagination.py             Custom paginator (exact response shape)
├── parser.py                 Rule-based NLP query parser
├── serializers.py            ProfileSerializer / ProfileListSerializer
├── services.py               External API aggregation service
├── views.py                  ProfileView / ProfileDetailView / ProfileSearchView
├── urls.py                   URL routing
├── tests.py                  67 unit + integration tests
├── fixtures/
│   └── seed_profiles.json    2026 seed profiles
└── management/commands/
    └── seed_profiles.py      Idempotent seed command (--clear flag)
```
