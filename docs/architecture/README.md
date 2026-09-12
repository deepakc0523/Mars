# MARS Architecture

## Overview

MARS is structured as a **monorepo** with a clear separation between:

- **Backend** — Python/FastAPI async API server and agent runtime
- **Frontend** — Next.js TypeScript dashboard
- **Data** — Scenarios, runbooks, and postmortems for RAG
- **Docs** — Architecture and API documentation
- **Scripts** — Operational tooling

---

## Core Architectural Principle: Unified Event Pipeline

> **Text and speech must use the exact same backend event pipeline.**
> Speech is only an interface layer. Speech-to-text produces the same
> `Event` objects that text input produces. Text and speech must never
> have separate agent logic.

All inputs — human text, voice transcripts, monitoring alerts, and
system events — are converted to an `Event` object and published to
the `EventBus`. The agent loop subscribes to the bus and reacts to
events regardless of their origin.

```
Human text ──────┐
Voice (STT) ─────┼──► Event(event_type, source, payload) ──► EventBus ──► Agent Loop
Anomaly detector ┘
```

---

## The MARS Agent Loop: IPRRVSЕ

The agent loop follows this cycle when an interrupt arrives:

```
INTERRUPT → PRESERVE → RE-EVALUATE → REPLAN → VERIFY → SAFETY → EXECUTE
```

| Phase | Description |
|-------|-------------|
| **INTERRUPT** | An event arrives that may invalidate the current plan |
| **PRESERVE** | The current execution state and world-state snapshot are saved |
| **RE-EVALUATE** | The planner determines whether the active plan is still valid |
| **REPLAN** | If invalid, the planner generates a new plan |
| **VERIFY** | An independent verifier agent checks the plan for correctness |
| **SAFETY** | A safety gate checks reversibility and blast radius |
| **EXECUTE** | Plan steps are executed sequentially with live state updates |

If re-evaluation determines the current plan is still valid, execution
resumes from the preserved state without replanning.

---

## Component Map

### Backend (`backend/`)

```
backend/
  app/
    core/           # Config, logging, exceptions — no business logic
    models/         # Canonical Pydantic models (Event, Plan, WorldState, …)
    events/         # EventBus (pub/sub) + Event factory helpers
    state/          # StateManager — world-state lifecycle
    agents/         # BaseAgent ABC; future: PlannerAgent, VerifierAgent
    tools/          # BaseTool ABC; future: callable tool implementations
    safety/         # BaseSafetyGate ABC; future: rule-based safety gate
    ledger/         # BaseLedger ABC; future: SQLite SHA-256 chain
    rag/            # BaseRetriever ABC; future: ChromaDB integration
    api/            # FastAPI application factory + routers
  tests/            # pytest test suite
  main.py           # Entry point
  requirements.txt  # Pinned production dependencies
```

**Key design decisions:**

1. **Abstract base classes now** — Every component that will use AI or
   external services is represented by an ABC in the foundation phase.
   This forces explicit contracts before any AI code is written.

2. **Singletons via module globals** — `event_bus` and `state_manager`
   are module-level singletons. This avoids FastAPI dependency injection
   complexity until it is needed.

3. **No circular imports** — `models` has no imports from any other app
   package. `events` imports only from `models`. `state` imports only
   from `models`. `agents` imports from `models`, `events`, `state`.

### Frontend (`frontend/`)

```
frontend/
  app/              # Next.js App Router pages and layouts
  components/       # Reusable React components (future)
  lib/              # api.ts (HTTP client), websocket.ts (WS client)
  hooks/            # React hooks: useWebSocket (future: useWorldState, …)
  types/            # TypeScript types mirroring backend Pydantic models
```

**Key design decisions:**

1. **Types mirror backend models** — `frontend/types/mars.ts` is kept
   in sync with `backend/app/models/models.py`. No code generation is
   used in the foundation phase; manual sync is acceptable for a hackathon.

2. **WebSocket-ready** — `lib/websocket.ts` and `hooks/useWebSocket.ts`
   are implemented but not yet connected to a real endpoint. When the
   backend WebSocket router is added, no frontend code changes are needed.

---

## Data Flow (Future State)

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│  Input (text/voice) ──► API / WebSocket              │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP / WebSocket
┌─────────────────────▼───────────────────────────────┐
│                    Backend                           │
│                                                      │
│  FastAPI ──► EventBus ──► StateManager               │
│                 │                                    │
│                 ▼                                    │
│         Agent Loop (IPRRVSЕ)                         │
│           │         │                               │
│           ▼         ▼                               │
│      PlannerAgent  VerifierAgent                    │
│       (Groq LLM)   (Gemini Flash)                   │
│           │                                         │
│           ▼                                         │
│      SafetyGate ──► Ledger (SQLite + SHA-256)        │
│           │                                         │
│           ▼                                         │
│      ToolExecutor ◄── RAG (ChromaDB)                │
└─────────────────────────────────────────────────────┘
```

---

## Technology Rationale

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend API | FastAPI | Async-first, Pydantic-native, excellent WebSocket support |
| Async runtime | asyncio | Single-threaded co-operative multitasking; ideal for I/O-bound agent work |
| Planner LLM | Groq/Llama | Low-latency inference; critical for real-time response |
| Verifier LLM | Gemini Flash | Independent model family eliminates correlated failures |
| Vector store | ChromaDB | Lightweight, embeddable; no separate infrastructure |
| Anomaly detection | Isolation Forest | Unsupervised; no labelled incident data needed |
| Ledger storage | SQLite | Zero-infrastructure; SHA-256 chain provides tamper evidence |
| Frontend | Next.js 14 (App Router) | SSR + client components; excellent TypeScript support |

---

## What Is Not Yet Built

The following are planned but not implemented in the foundation phase:

- [ ] PlannerAgent (Groq/Llama integration)
- [ ] VerifierAgent (Gemini Flash integration)
- [ ] SafetyGate implementation
- [ ] Ledger implementation (SQLite + SHA-256)
- [ ] RAG / ChromaDB integration
- [ ] Anomaly detection (Isolation Forest)
- [ ] WebSocket API endpoints
- [ ] Voice interface (Web Speech API)
- [ ] Dashboard / real-time charts (Recharts)
- [ ] Scenario simulation runner
