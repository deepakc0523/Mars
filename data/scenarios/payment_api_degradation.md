# Payment API Degradation Scenario

## Overview
This scenario demonstrates MARS handling a Payment API degradation incident
in a production e-commerce environment.

## Initial Conditions
- Payment API error rate: normal baseline < 0.5%
- P99 latency: normal baseline < 500ms
- Affected service: `payment-service` → external gateway `stripe-gateway`

## Incident Trigger
Anomaly detection fires when:
- Error rate rises above 5% for > 2 minutes
- P99 latency exceeds 2000ms

## Expected MARS Response
1. **INTERRUPT**: Anomaly event injected into event pipeline
2. **PRESERVE**: Current world state snapshot saved
3. **RE-EVALUATE**: Planner checks whether active plan (if any) is still valid
4. **REPLAN**: Planner generates a new incident-response plan
5. **VERIFY**: Verifier agent independently assesses the plan
6. **SAFETY**: Safety gate checks plan steps for reversibility
7. **EXECUTE**: Steps executed with live world-state updates

## Planned Steps (illustrative, not implemented yet)
1. Check payment service health endpoint
2. Retrieve recent error logs
3. Query relevant runbooks from RAG
4. Enable circuit breaker on payment-service
5. Route traffic to fallback payment provider
6. Monitor error rate for recovery
7. Notify on-call engineer

## Interruption Scenarios
- Human operator sends "switch to PayPal fallback immediately"
- Monitoring detects error rate is falling (recovery in progress)
- New anomaly detected on a different service

## Success Criteria
- Error rate returns below 1% within 5 minutes
- No data loss
- All decisions recorded in ledger
- Plan accepted by safety gate without human override
