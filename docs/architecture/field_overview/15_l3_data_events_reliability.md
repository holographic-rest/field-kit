PAGE 15 – Layer 3: Data, Events, and Reliability

Title: L3 – Field Architecture: Data & Reliability

Data & Events

CQRS + Event Sourcing + Kafka

QDPI events written to an append-only log (qdpi-events topic).

Read models (“Vault timelines”, “per-character maps”, “field metrics”) materialized from this log.

Other topics: vault-writes, ai-responses, metrics.

Sharding + Consistent Hashing + Horizontal Scaling

QDPI logs, Vault, and user metadata distributed across machines.

CAP & Eventual Consistency

Bonds & permissions: CP-leaning (never corrupt balances).

Search & Vault views: AP-leaning (slightly stale allowed).

Performance & Reliability

Redis

Sessions, hot state, rate limit counters, small read models.

Rate Limiting & Circuit Breakers

Protect from self-inflicted or external overload.

Map failures into narrative “field instability” messages instead of silent hangs.

Distributed Tracing

Every Q → M/D/H flow gets a trace ID; end-to-end observability.

Question answered: How does the whole field exist coherently, at scale, with controlled ways of breaking?