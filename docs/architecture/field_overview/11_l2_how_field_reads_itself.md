PAGE 11 – Layer 2: What This Layer Does

Title: L2 – Field Intelligence: How the Field Reads Itself

What this layer does

This is the Gibsey Index + Field Engine logic: how the field reads its own memory.

Corpus/Page Service + Vault Service produce raw text + metadata.

Chunkers (sliding/semantic) + document hierarchies turn them into retrieval units.

Metadata enrichment tags each chunk with:

Character(s), QDPI direction (Q/M/D/H), HPU, time, user, experiment, public/private, etc.

Index Service (vector store + search engine + graph) supports:

Hybrid search (semantic + lexical).

Graph-based retrieval (pages ↔ characters ↔ symbols ↔ Vault entries).

Recursive retrieval (first get core scenes, then related commentary).

The Field Engine / Orchestrator then:

Expands queries, launches multi-query retrieval.

Uses MMR to gather a diverse chorus (multiple characters, text types).

Packs context into a limited window (primary + Vault + analysis) and mitigates lost-in-the-middle.

Applies adaptive retrieval based on:

Question type (definitional vs personal vs structural).

User role (student vs researcher vs Brennan).

Experiment configuration.

Question answered: Given everything the field knows, what should we read to respond right now?