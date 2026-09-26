# Scenario 001 — "The Silent Semver Break"

## Plain-Language Description

A developer updates the `utility-lib` package from version `2.3.1` to `3.0.0`.
The new major version removes the `formatCurrency()` function that the payments service relies on.
Three tests fail. The build fails. Two downstream services (order-service, reporting-service)
also go red because they depend on payments-service responses.

## Why This Scenario Is Ideal for the Demo

- **Clear failure propagation**: one change → three failing services (visual cascade obvious to non-technical audience)
- **Short causal chain**: DEPENDENCY_CHANGE → IMPORT_ERROR → TEST_FAILURE → BUILD_FAILURE (4 nodes, 3 edges)
- **Unambiguous root cause**: single dependency bump, no conflating factors
- **Minimal fix**: pin `utility-lib` back to `2.3.1` in package.json + package-lock.json
- **Checkable validation**: re-running 3 tests against the pinned version all pass

## Ground Truth Labels (for benchmark measurement)

```json
{
  "root_cause_node_id": "node-dependency-change",
  "root_cause_type": "DEPENDENCY_CHANGE",
  "root_cause_description": "utility-lib bumped from 2.3.1 to 3.0.0 — formatCurrency() removed in v3",
  "fix_type": "DEPENDENCY_CHANGE",
  "fix_description": "Pin utility-lib to 2.3.1 in package.json",
  "expected_recovered_services": ["payments-service", "order-service", "reporting-service"],
  "expected_passing_tests": [
    "PaymentsService::test_format_invoice",
    "PaymentsService::test_calculate_total",
    "PaymentsService::test_generate_receipt"
  ]
}
```

## Services Affected

| Service            | Status after failure | Recovery after fix |
|--------------------|----------------------|--------------------|
| payments-service   | FAILED               | HEALTHY            |
| order-service      | DEGRADED             | HEALTHY            |
| reporting-service  | DEGRADED             | HEALTHY            |
| auth-service       | HEALTHY              | HEALTHY (unchanged)|
| api-gateway        | HEALTHY              | HEALTHY (unchanged)|
