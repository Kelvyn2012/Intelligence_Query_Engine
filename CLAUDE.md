# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run migrations and dev server
python manage.py migrate
python manage.py runserver

# Run all tests
python manage.py test api

# Run a single test class or method
python manage.py test api.tests.ProfileCreateTests
python manage.py test api.tests.ProfileCreateTests.test_create_profile_success
```

## Architecture

**Django project**: `genderize_project/` (settings, root URLs, wsgi)  
**API app**: `api/` (models, views, serializers, services, exceptions, tests)

### Request flow

`views.py` → `services.py` → external APIs (Genderize, Agify, Nationalize)

- **ProfileAggregatorService** (`api/services.py`): calls three external APIs concurrently via `ThreadPoolExecutor(max_workers=3)` to fetch gender, age, and nationality data for a given name. Returns a dict used to build the `Profile` record.
- **Views** (`api/views.py`): thin — validate input, call the service, delegate to serializers. POST is idempotent (returns existing record on duplicate name); race conditions handled by catching `IntegrityError`.
- **Custom exceptions** (`api/exceptions.py`): `ExternalAPIException` (upstream failure) and `InvalidProfileDataException` (unusable data per assessment rules).

### Data model

`Profile` uses UUID7 as primary key. `name` is unique and stored lowercase. Key fields: `gender`, `gender_probability`, `age`, `age_group` (child/teenager/adult/senior), `country_id`, `country_probability`.

### Serializers

- `ProfileSerializer` — full detail (all fields, ISO timestamp)
- `ProfileListSerializer` — summary (id, name, gender, age, age_group, country_id)

### URL layout

| Method | Path | View |
|--------|------|------|
| GET, POST | `/api/profiles` | `ProfileView` |
| GET, DELETE | `/api/profiles/<uuid:id>` | `ProfileDetailView` |

GET `/api/profiles` supports query filters: `gender`, `country_id`, `age_group`.

## Environment

Copy `.env` for local dev. Key vars:

```
DEBUG=True
SECRET_KEY=...
DATABASE_URL=postgresql://...   # Neon in prod; omit to fall back to SQLite
```

Production uses Gunicorn + WhiteNoise (static files). Deployment via `Procfile` runs `collectstatic` and `migrate` on release.
