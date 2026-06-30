# FitAI Coach — Architecture & Implementation Plan

## System Overview

FitAI Coach is a full-stack fitness coaching platform that tracks workouts, diet, body metrics, and recovery, then uses Gemini AI to deliver personalized coaching insights.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client (React SPA)                        │
│  Auth │ Onboarding │ Dashboard │ Workouts │ Diet │ Body │ Coach  │
└─────────────────────────────┬────────────────────────────────────┘
                              │ HTTPS / REST + JWT
┌─────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │ Routers  │ │ Services  │ │ Auth/JWT   │ │ SQLAlchemy ORM   │  │
│  └──────────┘ └───────────┘ └────────────┘ └──────────────────┘  │
│       │              │                                             │
│  ┌────▼────┐   ┌─────▼──────┐   ┌─────────────────────────────┐  │
│  │Nutrition│   │ Analytics  │   │ Gemini AI (fallback only)   │  │
│  │Service  │   │ Service    │   │ • Unknown food estimation   │  │
│  │Local DB │   │ Dashboard  │   │ • Daily/weekly coaching     │  │
│  │first    │   │ Charts     │   └─────────────────────────────┘  │
│  └─────────┘   └────────────┘                                    │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   PostgreSQL 16   │
                    └───────────────────┘
```

---

## Database Schema

### Entity Relationship

```
users (1) ──< fitness_goals
users (1) ──< workouts ──< workout_exercises ──< exercise_sets
users (1) ──< diet_logs ──< diet_entries >── food_items (optional FK)
users (1) ──< body_metrics
users (1) ──< recovery_logs
users (1) ──< coaching_insights
```

### Key Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | Auth & profile | email, hashed_password, full_name |
| `fitness_goals` | User targets | goal_type, target_body_fat, target_protein, target_calories |
| `workouts` | Session container | workout_date, name, duration_minutes |
| `workout_exercises` | Exercise in session | exercise_name, order_index |
| `exercise_sets` | Set details | weight_kg, reps, time_seconds, rest_seconds |
| `diet_logs` | Meal container | log_date, meal_type |
| `diet_entries` | Parsed food item | food_name, calories, protein_g, carbs_g, fat_g, source |
| `food_items` | Local Indian food DB | name, aliases (JSON), serving_size, macros |
| `body_metrics` | Progress tracking | weight_kg, body_fat_percent, waist_cm, photo_url |
| `recovery_logs` | Daily recovery | sleep_hours, water_liters, steps |
| `coaching_insights` | AI feedback | insight_type, title, content, metadata_json |

---

## Nutrition Pipeline (Local-First)

```
User input: "2 rotis + dal + 150g paneer"
        │
        ▼
   parse_food_input()
   → ["2 rotis", "dal", "150g paneer"]
        │
        ▼
   For each segment:
   ┌─────────────────────────────────────┐
   │ 1. Normalize & fuzzy match against  │
   │    food_items.name + aliases        │
   │ 2. If match → scale macros by qty   │
   │ 3. If no match → Gemini estimate    │
   └─────────────────────────────────────┘
        │
        ▼
   Store diet_entries with source tag
   (database | gemini)
```

**Benefits:** ~90% of common Indian meals hit the local DB. Gemini is only called for novel/unrecognized items, reducing cost, latency, and inconsistency.

---

## API Design

All endpoints prefixed with `/api`. JWT required except auth routes.

| Domain | Endpoints |
|--------|-----------|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| **Goals** | `POST /goals`, `GET /goals`, `GET /goals/active` |
| **Workouts** | `POST /workouts`, `GET /workouts`, `GET /workouts/{id}` |
| **Diet** | `POST /diet/log`, `GET /diet/logs` |
| **Body** | `POST /body/metrics`, `GET /body/metrics`, `POST /body/metrics/{id}/photo` |
| **Recovery** | `POST /recovery/log`, `GET /recovery/logs` |
| **Coach** | `GET /coach/dashboard`, `GET /coach/charts`, `POST /coach/analyze`, `GET /coach/insights` |

---

## AI Coach Flow

1. **Aggregate** user data (workouts, diet, metrics, recovery) via `analytics.gather_coaching_data()`
2. **Send** structured JSON to Gemini with coaching prompt
3. **Parse** response into typed insights (daily, weekly, progression, nutrition, goal_estimate)
4. **Store** in `coaching_insights` table
5. **Display** on AI Coach page with action buttons

Fallback logic provides basic insights when Gemini is unavailable.

---

## Frontend Architecture

```
src/
├── components/
│   ├── Layout.tsx          # Sidebar nav, mobile responsive
│   ├── StatCard.tsx        # Dashboard metric cards
│   └── ui/                 # Shadcn-style primitives
├── context/
│   └── AuthContext.tsx     # JWT auth state
├── lib/
│   ├── api.ts              # Typed API client
│   └── utils.ts            # cn(), formatDate()
└── pages/
    ├── LoginPage.tsx
    ├── RegisterPage.tsx
    ├── OnboardingPage.tsx  # Goal setup wizard
    ├── DashboardPage.tsx   # Stats + Recharts
    ├── WorkoutsPage.tsx
    ├── DietPage.tsx
    ├── BodyPage.tsx
    ├── RecoveryPage.tsx
    └── CoachPage.tsx
```

**Design:** Dark SaaS theme, green/indigo accent gradient, mobile-first responsive layout.

---

## Folder Structure

```
Fitness/
├── docker-compose.yml          # PostgreSQL
├── README.md
├── ARCHITECTURE.md             # This file
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py               # FastAPI app + lifespan
│       ├── config.py             # Pydantic settings
│       ├── database.py           # SQLAlchemy engine
│       ├── auth.py               # JWT + password hashing
│       ├── schemas.py            # Pydantic request/response models
│       ├── models/               # SQLAlchemy ORM models
│       ├── routers/              # API route handlers
│       ├── services/
│       │   ├── nutrition.py      # Local DB + Gemini fallback
│       │   ├── gemini.py         # AI coaching + food estimation
│       │   └── analytics.py      # Dashboard stats & charts
│       └── seed/
│           └── foods.py          # 40+ Indian food items
└── frontend/
    ├── vite.config.ts
    └── src/                      # React application
```

---

## Implementation Phases (Completed)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Backend scaffolding, models, auth | ✅ |
| 2 | Food database seed + nutrition service | ✅ |
| 3 | Workout, diet, body, recovery APIs | ✅ |
| 4 | Analytics + Gemini coaching service | ✅ |
| 5 | Frontend auth + onboarding | ✅ |
| 6 | Dashboard with charts | ✅ |
| 7 | All logging pages + AI coach page | ✅ |

---

## Production Considerations

- **Secrets:** Store `GEMINI_API_KEY` and `SECRET_KEY` in environment variables only
- **Migrations:** Add Alembic migrations for schema versioning
- **File uploads:** Move progress photos to S3/Cloud Storage
- **Rate limiting:** Add rate limits on `/coach/analyze` and Gemini fallback
- **Caching:** Cache food DB lookups in Redis for high traffic
- **Monitoring:** Add structured logging and health checks
