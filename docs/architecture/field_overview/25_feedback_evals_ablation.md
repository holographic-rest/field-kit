PAGE 25 – Learning & Research Feedback Loops (Part 1)

Title: FEEDBACK – Evals & Ablation

9. Learning and Research Feedback Loops

The field is not static; it learns about how it is learning.

From Evals (Layer 4) → RAG & Models (Layers 2 & 1)

If evals show systematic issues (e.g., missing key context), we:

Adjust retrieval strategies (more graph search, more Vault, etc.).

Tune rerankers with PyTorch on positive/negative examples.

From Ablation Testing (Layer 2) → Architecture (Layer 3)

Running the same question with different context sources reveals:

Which data sources are actually crucial.

Where to invest in better indexing/sharding and where to simplify.