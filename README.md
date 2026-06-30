# FitAI Coach

AI-powered fitness coaching web application with workout tracking, smart nutrition logging (Indian food database + Gemini fallback), body metrics, recovery tracking, and personalized AI coaching.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  Dashboard │ Workouts │ Diet │ Body │ Recovery │ AI Coach    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JWT)
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│  Auth │ Goals │ Workouts │ Diet │ Body │ Recovery │ Coach   │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Nutrition   │  │ Analytics    │  │ Gemini AI Service   │ │
│  │ Service     │  │ Service      │  │ (coach + fallback)  │ │
│  │ (local DB   │  │              │  │                     │ │
│  │  first)     │  │              │  │                     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    └─────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Tailwind CSS v4, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose + bcrypt) |
| AI | Google Gemini API |

## Database Schema

- **users** — authentication and profile
- **fitness_goals** — goal type, body fat/weight/strength/targets
- **workouts** → **workout_exercises** → **exercise_sets** — nested workout logging
- **diet_logs** → **diet_entries** — plain-English food with macro breakdown
- **food_items** — local Indian food database with aliases (40+ items)
- **body_metrics** — weight, body fat %, waist, progress photos
- **recovery_logs** — sleep, water, steps
- **coaching_insights** — AI-generated daily/weekly feedback

## Nutrition Strategy

When a user logs `"2 rotis + dal + 150g paneer"`:

1. **Parse** input into segments (`2 rotis`, `dal`, `150g paneer`)
2. **Match** each segment against `food_items` by name and aliases
3. **Scale** nutrition by quantity/unit from the database
4. **Fallback** to Gemini API only for unrecognized foods
5. **Store** breakdown with source tag (`database` or `gemini`)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login, get JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/goals` | Set fitness goal |
| GET | `/api/goals/active` | Active goal |
| POST | `/api/workouts` | Log workout |
| GET | `/api/workouts` | List workouts |
| POST | `/api/diet/log` | Log food (plain English) |
| GET | `/api/diet/logs` | Diet history |
| POST | `/api/body/metrics` | Log body metrics |
| POST | `/api/recovery/log` | Log recovery |
| GET | `/api/coach/dashboard` | Dashboard stats |
| GET | `/api/coach/charts` | Chart data |
| POST | `/api/coach/analyze` | Run AI analysis |
| GET | `/api/coach/insights` | Past insights |

## Quick Start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `CORS_ORIGINS` | Allowed frontend origins |

## Folder Structure

```
Fitness/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   ├── schemas.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   │   ├── nutrition.py    # Local DB + Gemini fallback
│   │   │   ├── gemini.py       # AI coaching + food estimation
│   │   │   └── analytics.py    # Dashboard & chart data
│   │   └── seed/
│   │       └── foods.py        # 40+ Indian food items
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/
        ├── context/
        ├── lib/
        └── pages/
```

## Security Notes

- Never commit `.env` files with API keys
- Change `SECRET_KEY` in production
- Use HTTPS in production
- The Gemini API key should be stored as an environment variable only
