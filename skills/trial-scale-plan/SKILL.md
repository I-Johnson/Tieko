---
name: trial-scale-plan
description: Plan how this immune-cell analysis should evolve for more data, recurring ingestion, concurrent users, additional trials, stronger reliability, or regulated use. Use for architecture and system-design questions; do not implement unless separately requested.
---

# Trial scale plan

Read `SCALING.md` and the current pipeline entrypoints before planning. Preserve
the existing simple architecture until a named constraint justifies migration.

## Define the pressure

Quantify data volume and growth, ingestion frequency, concurrent readers and
writers, latency, analysis runtime, availability, recovery targets, governance,
and budget. If values are unknown, state assumptions and show which decision
would change at each threshold.

## Produce a staged plan

For each stage, include:

1. The measured trigger and present bottleneck.
2. The smallest architecture change that relieves it.
3. Data migration and compatibility strategy.
4. Validation, observability, security, and rollback.
5. Operational cost and new failure modes.

Compare credible alternatives for material choices. Address data ingestion,
storage, schema evolution, analytical execution, serving, dashboard behavior,
security, governance, deployment, monitoring, and statistics. Separate immediate
hardening from later platform changes.

## Guardrails

- Do not propose microservices merely because the system may grow.
- Do not conflate row count with concurrency or latency.
- Do not put long-running analysis in the Streamlit request path.
- Do not make regulatory claims without identifying the applicable workflow and stakeholders.
- Do not describe the current significance test as a predictive model.

End with a concise interview explanation that defends the current choices and
names the evidence that would trigger the next migration.
