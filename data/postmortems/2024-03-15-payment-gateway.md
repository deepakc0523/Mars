# Postmortem: Payment Gateway Outage — 2024-03-15

## Summary
A misconfigured rate-limit policy on the Stripe gateway caused a 23-minute
partial outage affecting 34% of checkout attempts.

## Timeline
| Time (UTC) | Event |
|------------ |-------|
| 14:02 | Stripe deploys rate-limit config change |
| 14:04 | Error rate rises to 12%; anomaly detector fires |
| 14:07 | On-call engineer acknowledges alert |
| 14:11 | Engineer manually enables circuit breaker |
| 14:18 | Fallback provider active; error rate falls to 2% |
| 14:25 | Stripe reverts config change; gateway recovers |
| 14:27 | Circuit breaker closed; normal traffic restored |

## Root Cause
A Stripe configuration change inadvertently applied a 100 req/s rate limit
to our merchant account, lower than our peak traffic of ~350 req/s.

## Impact
- 34% of checkout attempts failed (returned 429 errors)
- Estimated revenue impact: $42,000
- 0 data loss events

## Lessons Learned
1. Rate-limit alerts should fire before user impact (proactive, not reactive)
2. Circuit breaker half-open recovery took too long (manual process)
3. Fallback provider onboarding was not tested under load

## Action Items
1. Add Stripe rate-limit quota monitoring
2. Automate circuit breaker half-open recovery
3. Load-test fallback provider monthly

## Relevance to MARS
This incident is the primary demonstration scenario for MARS. The 7-minute
gap between anomaly detection and engineer action (14:04 → 14:11) is exactly
the window where MARS's autonomous response loop would act.
