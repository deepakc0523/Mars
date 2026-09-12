# Runbook: Payment Gateway Circuit Breaker

## Purpose
Safely enable the circuit breaker on the payment service to stop cascading
failures when the upstream payment gateway is degraded.

## Prerequisites
- Access to `payment-service` configuration API
- `circuit-breaker-admin` role

## Steps
1. Verify current circuit breaker state
   ```
   GET /admin/circuit-breaker/status
   ```
2. Enable circuit breaker in OPEN state (blocks all requests)
   ```
   POST /admin/circuit-breaker/open
   ```
3. Confirm fallback payment handler is active
   ```
   GET /admin/payment/fallback/status
   ```
4. Monitor error rate for 2 minutes
5. If error rate drops below 1%, set circuit breaker to HALF-OPEN
   ```
   POST /admin/circuit-breaker/half-open
   ```
6. If health checks pass for 5 minutes, close the circuit breaker
   ```
   POST /admin/circuit-breaker/close
   ```

## Rollback
To immediately close the circuit breaker (allow traffic through):
```
POST /admin/circuit-breaker/close
```

## Impact
- Revenue impact: ~100% of checkout attempts fail while OPEN
- Fallback handler serves limited payment methods (card only, no BNPL)
- Circuit breaker state is logged to the decision ledger

## Escalation
If error rate does not recover within 10 minutes, page the on-call
payment infrastructure engineer.
