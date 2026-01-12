"""
Field-Kit v0.1 Complexity Metrics (Sprint S06)

Implements Coffee Automaton-inspired complexity measurement for detecting
"soup" (everything linked to everything, ungrounded suggestions).

Key concepts:
- Apparent complexity: gzip size of coarse-grained snapshot
- Branching factor: Average suggestion count per decision point
- Duplicate rate: Near-duplicate detection by title/body hash
- Suggestion entropy: Distribution sharpness of suggestion types

All metrics are deterministic and use only stdlib (no external deps).
"""

import gzip
import json
import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple


def gzip_bytes(obj: Any) -> int:
    """
    Compress an object to JSON and return gzip size in bytes.

    This is a practical proxy for Kolmogorov complexity.
    Higher = more complex/structured; lower = simpler/more compressible.
    """
    json_str = json.dumps(obj, sort_keys=True, default=str)
    compressed = gzip.compress(json_str.encode('utf-8'))
    return len(compressed)


def coarse_grain_snapshot(data_dir: Path) -> Dict[str, Any]:
    """
    Create a coarse-grained snapshot of the Field state.

    This is the "macrostate" used for apparent complexity measurement.
    Collapses raw data into summary statistics and histograms.

    Returns:
        Dict with counts, type distributions, graph stats
    """
    data_dir = Path(data_dir)
    snapshot = {
        "counts": {},
        "item_types": {},
        "event_types": {},
        "bond_stats": {},
        "suggestion_stats": {},
        "graph_stats": {},
    }

    # Count items by type
    items_file = data_dir / "items.jsonl"
    items = []
    if items_file.exists():
        with open(items_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    items.append(item)

    snapshot["counts"]["items"] = len(items)
    type_counts = Counter(item.get("type", "Q") for item in items)
    snapshot["item_types"] = dict(type_counts)

    # Count bonds
    bonds_file = data_dir / "bonds.jsonl"
    bonds = []
    if bonds_file.exists():
        with open(bonds_file) as f:
            for line in f:
                if line.strip():
                    bond = json.loads(line)
                    bonds.append(bond)

    # De-duplicate bonds (keep executed versions)
    executed_bonds = [b for b in bonds if b.get("status") == "executed"]
    snapshot["counts"]["bonds"] = len(executed_bonds)
    snapshot["counts"]["draft_bonds"] = len([b for b in bonds if b.get("status") == "draft"])

    # Bond type distribution (inferred from prompt)
    bond_types = Counter()
    for bond in executed_bonds:
        prompt = (bond.get("prompt_text") or "").lower()
        if "precise" in prompt or "conditions" in prompt or "clarif" in prompt:
            bond_types["clarify"] += 1
        elif "checklist" in prompt or "steps" in prompt or "concrete" in prompt:
            bond_types["concretize"] += 1
        elif "map" in prompt or "flow" in prompt or "connect" in prompt:
            bond_types["connect"] += 1
        elif "test" in prompt or "falsif" in prompt or "verify" in prompt:
            bond_types["test"] += 1
        else:
            bond_types["other"] += 1
    snapshot["bond_stats"]["type_distribution"] = dict(bond_types)

    # Count events
    events_file = data_dir / "qdpi_events.jsonl"
    if not events_file.exists():
        events_file = data_dir / "events.jsonl"

    events = []
    if events_file.exists():
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    events.append(event)

    snapshot["counts"]["events"] = len(events)
    event_types = Counter(event.get("name", "unknown") for event in events)
    snapshot["event_types"] = dict(event_types)

    # Suggestion stats from events
    suggestion_events = [e for e in events if e.get("name") == "bond.suggestions.presented"]
    total_suggestions = 0
    suggestion_intents = Counter()
    for evt in suggestion_events:
        suggestions = evt.get("refs", {}).get("suggestions", [])
        total_suggestions += len(suggestions)
        for s in suggestions:
            intent = s.get("intent_type") or s.get("intent") or "unknown"
            suggestion_intents[intent] += 1

    snapshot["suggestion_stats"]["total_presented"] = total_suggestions
    snapshot["suggestion_stats"]["intent_distribution"] = dict(suggestion_intents)
    snapshot["suggestion_stats"]["presentation_count"] = len(suggestion_events)

    # Graph stats
    if executed_bonds:
        # Compute degree histogram
        node_degrees: Dict[str, int] = {}
        for bond in executed_bonds:
            input_ids = bond.get("input_item_ids", [])
            output_id = bond.get("output_item_id")
            for iid in input_ids:
                node_degrees[iid] = node_degrees.get(iid, 0) + 1
            if output_id:
                node_degrees[output_id] = node_degrees.get(output_id, 0) + 1

        degrees = list(node_degrees.values())
        if degrees:
            snapshot["graph_stats"]["avg_degree"] = sum(degrees) / len(degrees)
            snapshot["graph_stats"]["max_degree"] = max(degrees)
            snapshot["graph_stats"]["min_degree"] = min(degrees)
            snapshot["graph_stats"]["connected_nodes"] = len(node_degrees)
        else:
            snapshot["graph_stats"]["avg_degree"] = 0
            snapshot["graph_stats"]["max_degree"] = 0
            snapshot["graph_stats"]["min_degree"] = 0
            snapshot["graph_stats"]["connected_nodes"] = 0
    else:
        snapshot["graph_stats"]["avg_degree"] = 0
        snapshot["graph_stats"]["max_degree"] = 0
        snapshot["graph_stats"]["min_degree"] = 0
        snapshot["graph_stats"]["connected_nodes"] = 0

    # Orphan rate (items not in any bond)
    connected_item_ids: Set[str] = set()
    for bond in executed_bonds:
        connected_item_ids.update(bond.get("input_item_ids", []))
        if bond.get("output_item_id"):
            connected_item_ids.add(bond["output_item_id"])

    all_item_ids = set(item.get("id") for item in items)
    orphan_ids = all_item_ids - connected_item_ids
    snapshot["graph_stats"]["orphan_count"] = len(orphan_ids)
    snapshot["graph_stats"]["orphan_rate"] = len(orphan_ids) / len(all_item_ids) if all_item_ids else 0

    return snapshot


def apparent_complexity(data_dir: Path) -> int:
    """
    Compute apparent complexity as gzip bytes of coarse-grained snapshot.

    This is the core metric from the Coffee Automaton paper:
    "Coarse-grain first, then measure complexity."

    Returns:
        Complexity in bytes (higher = more complex structure)
    """
    snapshot = coarse_grain_snapshot(data_dir)
    return gzip_bytes(snapshot)


def branching_factor_from_events(data_dir: Path) -> float:
    """
    Compute average branching factor from suggestion events.

    Branching factor = total suggestions presented / decision points

    High branching suggests healthy exploration.
    Very high branching may indicate soup (too many options).

    Returns:
        Average branching factor (0 if no data)
    """
    data_dir = Path(data_dir)
    events_file = data_dir / "qdpi_events.jsonl"
    if not events_file.exists():
        events_file = data_dir / "events.jsonl"
    if not events_file.exists():
        return 0.0

    decision_points = 0
    total_choices = 0

    with open(events_file) as f:
        for line in f:
            if line.strip():
                event = json.loads(line)
                name = event.get("name", "")

                if name == "bond.suggestions.presented":
                    suggestions = event.get("refs", {}).get("suggestions", [])
                    decision_points += 1
                    total_choices += len(suggestions)
                elif name == "bond.proposals.presented":
                    proposals = event.get("refs", {}).get("proposals", [])
                    decision_points += 1
                    total_choices += len(proposals)

    if decision_points == 0:
        return 0.0

    return total_choices / decision_points


def duplicate_rate(data_dir: Path) -> Tuple[float, int]:
    """
    Compute near-duplicate rate among items.

    Uses title prefix hashing for cheap detection.
    High duplicate rate suggests poor curation.

    Returns:
        Tuple of (duplicate_rate, duplicate_count)
    """
    data_dir = Path(data_dir)
    items_file = data_dir / "items.jsonl"

    if not items_file.exists():
        return 0.0, 0

    items = []
    with open(items_file) as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    if len(items) < 2:
        return 0.0, 0

    # Hash by normalized title prefix (first 50 chars)
    title_hashes: Dict[str, List[str]] = {}
    for item in items:
        title = (item.get("title") or "").lower().strip()[:50]
        h = hashlib.md5(title.encode()).hexdigest()[:8]
        if h not in title_hashes:
            title_hashes[h] = []
        title_hashes[h].append(item.get("id", ""))

    # Count duplicates (groups with >1 item)
    duplicate_count = 0
    for ids in title_hashes.values():
        if len(ids) > 1:
            duplicate_count += len(ids) - 1  # Extra items beyond first

    rate = duplicate_count / len(items) if items else 0
    return rate, duplicate_count


def suggestion_entropy_from_events(data_dir: Path) -> Tuple[float, float]:
    """
    Compute entropy of suggestion intent distribution.

    Low entropy = suggestions are concentrated on few intents (may be good or bad).
    High entropy = suggestions are spread evenly (max diversity).
    Max entropy for 4 intents = log2(4) = 2.0 bits.

    Returns:
        Tuple of (entropy, max_entropy)
    """
    data_dir = Path(data_dir)
    events_file = data_dir / "qdpi_events.jsonl"
    if not events_file.exists():
        events_file = data_dir / "events.jsonl"
    if not events_file.exists():
        return 0.0, 0.0

    intent_counts: Counter = Counter()
    total = 0

    with open(events_file) as f:
        for line in f:
            if line.strip():
                event = json.loads(line)
                if event.get("name") == "bond.suggestions.presented":
                    suggestions = event.get("refs", {}).get("suggestions", [])
                    for s in suggestions:
                        intent = s.get("intent_type") or s.get("intent") or "unknown"
                        intent_counts[intent] += 1
                        total += 1

    if total == 0:
        return 0.0, 0.0

    # Compute Shannon entropy
    entropy = 0.0
    for count in intent_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    # Max entropy for observed number of intents
    n_intents = len(intent_counts)
    max_entropy = math.log2(n_intents) if n_intents > 0 else 0.0

    return entropy, max_entropy


def hubness_score(data_dir: Path, top_n: int = 3) -> Tuple[float, List[str]]:
    """
    Compute hubness: fraction of edges touching top-N nodes.

    High hubness = few nodes dominate connections (soup indicator).
    Healthy graphs have distributed connectivity.

    Returns:
        Tuple of (hubness_fraction, top_node_ids)
    """
    data_dir = Path(data_dir)
    bonds_file = data_dir / "bonds.jsonl"

    if not bonds_file.exists():
        return 0.0, []

    bonds = []
    with open(bonds_file) as f:
        for line in f:
            if line.strip():
                bond = json.loads(line)
                if bond.get("status") == "executed":
                    bonds.append(bond)

    if not bonds:
        return 0.0, []

    # Count node appearances
    node_counts: Counter = Counter()
    total_edges = 0
    for bond in bonds:
        input_ids = bond.get("input_item_ids", [])
        output_id = bond.get("output_item_id")
        for iid in input_ids:
            node_counts[iid] += 1
            total_edges += 1
        if output_id:
            node_counts[output_id] += 1
            total_edges += 1

    if total_edges == 0:
        return 0.0, []

    # Get top-N nodes
    top_nodes = node_counts.most_common(top_n)
    top_node_ids = [node_id for node_id, _ in top_nodes]
    top_edge_count = sum(count for _, count in top_nodes)

    hubness = top_edge_count / total_edges
    return hubness, top_node_ids


def compute_all_metrics(data_dir: Path) -> Dict[str, Any]:
    """
    Compute all complexity metrics for a data directory.

    Returns a comprehensive metrics dict suitable for governance decisions.
    """
    data_dir = Path(data_dir)

    # Get the snapshot first
    snapshot = coarse_grain_snapshot(data_dir)

    # Compute derived metrics
    complexity = gzip_bytes(snapshot)
    branching = branching_factor_from_events(data_dir)
    dup_rate, dup_count = duplicate_rate(data_dir)
    entropy, max_entropy = suggestion_entropy_from_events(data_dir)
    hubness, top_hubs = hubness_score(data_dir)

    return {
        "snapshot": snapshot,
        "apparent_complexity": complexity,
        "branching_factor": round(branching, 2),
        "duplicate_rate": round(dup_rate, 4),
        "duplicate_count": dup_count,
        "suggestion_entropy": round(entropy, 4),
        "max_entropy": round(max_entropy, 4),
        "entropy_ratio": round(entropy / max_entropy, 4) if max_entropy > 0 else 0,
        "hubness": round(hubness, 4),
        "top_hubs": top_hubs,
        # Derived indicators
        "is_soupy": _is_soupy(snapshot, hubness, dup_rate),
        "is_sparse": _is_sparse(snapshot),
    }


def _is_soupy(snapshot: Dict[str, Any], hubness: float, dup_rate: float) -> bool:
    """
    Heuristic check for "soup" state.

    Soup indicators:
    - High hubness (few nodes dominate)
    - High duplicate rate
    - High orphan rate
    - Very high avg degree
    """
    graph_stats = snapshot.get("graph_stats", {})
    avg_degree = graph_stats.get("avg_degree", 0)
    orphan_rate = graph_stats.get("orphan_rate", 0)

    # Conservative thresholds
    if hubness > 0.6:  # Top 3 nodes have >60% of edges
        return True
    if dup_rate > 0.2:  # >20% duplicates
        return True
    if orphan_rate > 0.5 and snapshot["counts"].get("items", 0) > 5:
        return True  # Many orphans with enough items
    if avg_degree > 5:  # Average node in >5 bonds
        return True

    return False


def _is_sparse(snapshot: Dict[str, Any]) -> bool:
    """
    Check if the graph is too sparse (not enough connections).

    Sparse = few bonds relative to items.
    """
    counts = snapshot.get("counts", {})
    items = counts.get("items", 0)
    bonds = counts.get("bonds", 0)

    if items < 2:
        return False  # Not enough data

    # Expect at least 0.3 bonds per item
    bond_ratio = bonds / items if items > 0 else 0
    return bond_ratio < 0.3


def format_metrics_report(metrics: Dict[str, Any]) -> str:
    """
    Format metrics as a human-readable report.
    """
    lines = [
        "=" * 60,
        "COMPLEXITY METRICS REPORT",
        "=" * 60,
        "",
    ]

    # Counts
    snapshot = metrics.get("snapshot", {})
    counts = snapshot.get("counts", {})
    lines.append("--- Counts ---")
    lines.append(f"  Items: {counts.get('items', 0)}")
    lines.append(f"  Bonds (executed): {counts.get('bonds', 0)}")
    lines.append(f"  Bonds (draft): {counts.get('draft_bonds', 0)}")
    lines.append(f"  Events: {counts.get('events', 0)}")
    lines.append("")

    # Item types
    item_types = snapshot.get("item_types", {})
    if item_types:
        lines.append("--- Item Types ---")
        for t, count in sorted(item_types.items()):
            lines.append(f"  {t}: {count}")
        lines.append("")

    # Complexity metrics
    lines.append("--- Complexity Metrics ---")
    lines.append(f"  Apparent Complexity: {metrics.get('apparent_complexity', 0)} bytes")
    lines.append(f"  Branching Factor: {metrics.get('branching_factor', 0)}")
    lines.append(f"  Suggestion Entropy: {metrics.get('suggestion_entropy', 0):.3f} / {metrics.get('max_entropy', 0):.3f}")
    lines.append(f"  Entropy Ratio: {metrics.get('entropy_ratio', 0):.2%}")
    lines.append("")

    # Graph stats
    graph_stats = snapshot.get("graph_stats", {})
    lines.append("--- Graph Stats ---")
    lines.append(f"  Avg Degree: {graph_stats.get('avg_degree', 0):.2f}")
    lines.append(f"  Max Degree: {graph_stats.get('max_degree', 0)}")
    lines.append(f"  Connected Nodes: {graph_stats.get('connected_nodes', 0)}")
    lines.append(f"  Orphan Rate: {graph_stats.get('orphan_rate', 0):.2%}")
    lines.append("")

    # Health indicators
    lines.append("--- Health Indicators ---")
    lines.append(f"  Hubness: {metrics.get('hubness', 0):.2%}")
    lines.append(f"  Duplicate Rate: {metrics.get('duplicate_rate', 0):.2%} ({metrics.get('duplicate_count', 0)} items)")
    lines.append(f"  Is Soupy: {metrics.get('is_soupy', False)}")
    lines.append(f"  Is Sparse: {metrics.get('is_sparse', False)}")
    lines.append("")

    # Top hubs
    top_hubs = metrics.get("top_hubs", [])
    if top_hubs:
        lines.append("--- Top Hub Nodes ---")
        for hub in top_hubs[:3]:
            lines.append(f"  {hub}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
