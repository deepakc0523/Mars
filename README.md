# MARS — Multi-Agent Reasoning & Adaptive Response System

> **Hackathon Project** · Theme: *Interruptible Real-time Agents*

---

## What Is MARS?

MARS is a real-time incident-response agent that maintains a continuously
updated **world state**. When an incident occurs, MARS:

1. Detects the anomaly and fires an **interrupt**
2. **Preserves** its current execution state
3. **Re-evaluates** whether the active plan is still valid
4. **Replans** if needed, using a Llama-powered planner agent
5. Has the plan independently **verified** by a Gemini Flash verifier agent
6. Passes the plan through a **safety gate** checking reversibility
7. **Executes** the plan step by step with live world-state updates

At any point in this loop, a human operator (or another monitoring event)
can **interrupt** MARS — it will pause, preserve state, and restart the
IPRRVSЕ cycle with the new information.

---

## Theme: Interruptible Real-time Agents

Traditional automation scripts run to completion or fail. MARS is designed
around **interruptibility as a first-class feature**:

- Every phase transition is an explicit, named state
- State is always preserved before any potentially invalidating operation
- Replanning is fast because the world state is continuously maintained
- Human interruptions are just another event type in the pipeline

---

## Architecture: IPRRVSЕ Loop

```
INTERRUPT → PRESERVE → RE-EVALUATE → REPLAN → VERIFY → SAFETY → EXECUTE
    ▲                                                                │
    └────────────────────── (interrupt at any point) ───────────────┘
```

### Unified Event Pipeline

> Text and speech use the **exact same backend event pipeline**.
> Speech-to-text produces the same `Event` objects that text input produces.
> There is no separate agent logic for voice vs text.

```
Human text ──┐
Voice (STT) ─┼──► Event ──► EventBus ──► Agent Loop
System alert ┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python · FastAPI · asyncio · WebSockets |
| Database | SQLite |
| Planner LLM | Groq / Llama 3.3 70B |
| Verifier LLM | Google Gemini 1.5 Flash |
| RAG | ChromaDB · sentence-transformers |
| Anomaly detection | scikit-learn Isolation Forest |
| Voice | Browser Web Speech API (STT + TTS) |
| Decision ledger | SQLite · SHA-256 hash chain |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · Recharts |

---

## Current Implementation Status

| Component | Status |
|-----------|--------|
| Monorepo structure | ✅ Complete |
| FastAPI application factory | ✅ Complete |
| `GET /health` endpoint | ✅ Complete |
| Configuration module (env-based) | ✅ Complete |
| Structured logging | ✅ Complete |
| Pydantic models (Event, Plan, WorldState) | ✅ Complete |
| EventBus (unified pub/sub pipeline) | ✅ Complete |
| Event factory helpers | ✅ Complete |
| StateManager | ✅ Complete |
| Abstract agent / tool / safety / ledger / RAG interfaces | ✅ Complete |
| Next.js 14 frontend structure | ✅ Complete |
| TypeScript types (mirrors backend models) | ✅ Complete |
| API client (`lib/api.ts`) | ✅ Complete |
| WebSocket client + hook | ✅ Complete |
| Backend tests (pytest) | ✅ Complete |
| PlannerAgent (Groq/Llama) | 🔲 Planned |
| VerifierAgent (Gemini Flash) | 🔲 Planned |
| SafetyGate implementation | 🔲 Planned |
| Ledger (SQLite + SHA-256) | 🔲 Planned |
| RAG / ChromaDB integration | 🔲 Planned |
| Anomaly detection (Isolation Forest) | 🔲 Planned |
| WebSocket endpoints | 🔲 Planned |
| Voice interface | 🔲 Planned |
| Dashboard / Recharts | 🔲 Planned |
| Scenario simulation runner | 🔲 Planned |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp ../.env.example .env

# Start the server
uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
# → http://localhost:8000/health
```

### Backend Tests

```bash
cd backend
pip install pytest httpx
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local  # edit NEXT_PUBLIC_API_URL if needed
npm run dev
# → http://localhost:3000
```

---

## Repository Structure

```
MARS/
  backend/          # Python FastAPI backend
  frontend/         # Next.js TypeScript frontend
  data/
    scenarios/      # Incident scenario definitions
    runbooks/       # Operational runbooks (future RAG input)
    postmortems/    # Past incident analyses (future RAG input)
  docs/
    architecture/   # System architecture documentation
    api/            # API reference
    demo/           # Demo guide
  scripts/          # Operational tooling (future)
  tests/            # Integration tests (future)
  .env.example      # Environment variable template
  docker-compose.yml
```

---

## Documentation

- [Architecture](docs/architecture/README.md)
- [API Reference](docs/api/README.md)
- [Demo Guide](docs/demo/README.md)
- [Primary Scenario](data/scenarios/payment_api_degradation.md)
