# MARS Demo Guide

> **Foundation phase** — no interactive demo is currently available.
> This guide will be updated as components are implemented.

## Primary Demonstration

**Scenario**: Payment API Degradation Incident

See [`data/scenarios/payment_api_degradation.md`](../../data/scenarios/payment_api_degradation.md)
for the full scenario description.

## Planned Demo Flow

1. Start backend + frontend
2. Open MARS dashboard in browser
3. Inject a simulated anomaly:
   - Payment API error rate rises to 15%
   - P99 latency rises to 3500ms
4. MARS detects the anomaly and fires an INTERRUPT
5. Observe the IPRRVSЕ loop in the dashboard:
   - Phase transitions shown in real time
   - Planner generates a response plan
   - Verifier independently reviews the plan
   - Safety gate evaluates each step
   - Steps execute sequentially
6. Mid-execution, send an interruption via text or voice:
   - "Switch to the PayPal fallback immediately"
7. Observe MARS pause, preserve state, replan, and continue

## Demo Checklist

- [ ] Backend running (`uvicorn main:app`)
- [ ] Frontend running (`npm run dev`)
- [ ] Backend health check passing
- [ ] Scenario simulation script ready
- [ ] Voice input enabled (Web Speech API)
- [ ] Ledger viewer showing decision chain

## Key Talking Points

1. **Unified event pipeline** — voice and text go through identical code paths
2. **Independent verification** — two different LLM families (Groq Llama + Gemini)
3. **Interruptible at any phase** — state is preserved and replanning is fast
4. **Tamper-evident ledger** — every decision hash-chained and auditable
5. **Safety gate** — no irreversible action without verification
