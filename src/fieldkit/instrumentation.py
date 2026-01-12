"""
Field-Kit v0.1 Debug Instrumentation (Sprint S01)

Provides stats and diagnostics for debugging pipeline behavior:
- Branching factor: Average choices at each decision point
- Suggestion entropy: Diversity of suggestions offered
- Vault write rate: Events/commits per time window
- Backtrack detector: Identify undo/redo patterns

Usage:
    from fieldkit.instrumentation import compute_stats_from_events

    stats = compute_stats_from_events(events)
    print(stats)

See: CLI command `python3 src/cli.py debug:stats` for interactive use.
"""

from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)


def compute_branching_factor(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute branching factor from suggestion events.

    Branching factor = average number of choices presented at decision points.

    Args:
        events: List of event dicts

    Returns:
        Dict with branching factor stats
    """
    suggestion_events = [
        e for e in events
        if e.get("name") in ("bond.suggestions.presented", "bond.proposals.presented")
    ]

    if not suggestion_events:
        return {
            "branching_factor": 0.0,
            "decision_points": 0,
            "total_choices": 0,
        }

    total_choices = 0
    for e in suggestion_events:
        suggestions = e.get("refs", {}).get("suggestions", [])
        total_choices += len(suggestions)

    bf = total_choices / len(suggestion_events)

    return {
        "branching_factor": round(bf, 2),
        "decision_points": len(suggestion_events),
        "total_choices": total_choices,
    }


def compute_suggestion_entropy(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute entropy of suggestion intents.

    Higher entropy = more diverse suggestion types offered.
    Entropy = -sum(p * log2(p)) for each intent type.

    Args:
        events: List of event dicts

    Returns:
        Dict with entropy stats
    """
    suggestion_events = [
        e for e in events
        if e.get("name") in ("bond.suggestions.presented", "bond.proposals.presented")
    ]

    if not suggestion_events:
        return {
            "entropy": 0.0,
            "intent_distribution": {},
            "total_suggestions": 0,
        }

    # Count intent types
    intent_counts: Counter = Counter()
    for e in suggestion_events:
        suggestions = e.get("refs", {}).get("suggestions", [])
        for s in suggestions:
            intent = s.get("intent_type", "unknown")
            intent_counts[intent] += 1

    total = sum(intent_counts.values())
    if total == 0:
        return {
            "entropy": 0.0,
            "intent_distribution": {},
            "total_suggestions": 0,
        }

    # Compute Shannon entropy
    entropy = 0.0
    distribution = {}
    for intent, count in intent_counts.items():
        p = count / total
        distribution[intent] = round(p, 3)
        if p > 0:
            entropy -= p * math.log2(p)

    return {
        "entropy": round(entropy, 3),
        "max_entropy": round(math.log2(len(intent_counts)) if intent_counts else 0, 3),
        "intent_distribution": distribution,
        "total_suggestions": total,
    }


def compute_write_rate(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute vault write rate (events and commits over time).

    Args:
        events: List of event dicts with "ts" timestamps

    Returns:
        Dict with write rate stats
    """
    if not events:
        return {
            "total_events": 0,
            "total_commits": 0,
            "events_per_minute": 0.0,
            "commits_per_minute": 0.0,
            "duration_seconds": 0,
        }

    # Parse timestamps
    timestamps = []
    for e in events:
        ts = e.get("ts")
        if ts:
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = ts
                timestamps.append(dt)
            except (ValueError, TypeError):
                pass

    if len(timestamps) < 2:
        return {
            "total_events": len(events),
            "total_commits": sum(1 for e in events if e.get("name") == "store.commit"),
            "events_per_minute": 0.0,
            "commits_per_minute": 0.0,
            "duration_seconds": 0,
        }

    # Sort and compute duration
    timestamps.sort()
    duration = (timestamps[-1] - timestamps[0]).total_seconds()

    total_commits = sum(1 for e in events if e.get("name") == "store.commit")

    if duration > 0:
        epm = (len(events) / duration) * 60
        cpm = (total_commits / duration) * 60
    else:
        epm = 0.0
        cpm = 0.0

    return {
        "total_events": len(events),
        "total_commits": total_commits,
        "events_per_minute": round(epm, 2),
        "commits_per_minute": round(cpm, 2),
        "duration_seconds": round(duration, 2),
    }


def detect_backtracks(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect potential backtrack patterns (undo/redo, repeated failures).

    Backtracks indicate user confusion or system issues.

    Args:
        events: List of event dicts

    Returns:
        Dict with backtrack detection results
    """
    # Look for patterns indicating backtracks:
    # 1. item.deleted following item.created (quick delete)
    # 2. bond.run_requested without bond.executed (failed bonds)
    # 3. Multiple identical suggestions (stuck in loop)

    backtracks = []

    # Check for unexecuted bonds (run requested but not executed)
    run_requests = [e for e in events if e.get("name") == "bond.run_requested"]
    executions = [e for e in events if e.get("name") == "bond.executed"]
    executed_bond_ids = {e.get("refs", {}).get("bond_id") for e in executions}

    for rr in run_requests:
        bond_id = rr.get("refs", {}).get("bond_id")
        if bond_id and bond_id not in executed_bond_ids:
            backtracks.append({
                "type": "unexecuted_bond",
                "bond_id": bond_id,
                "ts": rr.get("ts"),
            })

    # Check for quick deletes (item deleted within same session as created)
    item_creates = {
        e.get("refs", {}).get("item_id"): e.get("ts")
        for e in events if e.get("name") == "item.created"
    }
    item_deletes = [e for e in events if e.get("name") == "item.deleted"]
    for d in item_deletes:
        item_id = d.get("refs", {}).get("item_id")
        if item_id in item_creates:
            backtracks.append({
                "type": "quick_delete",
                "item_id": item_id,
                "ts": d.get("ts"),
            })

    return {
        "backtrack_count": len(backtracks),
        "backtracks": backtracks[:10],  # Limit to first 10
        "has_backtracks": len(backtracks) > 0,
    }


def compute_credits_trajectory(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute credits balance trajectory from delta events.

    Args:
        events: List of event dicts

    Returns:
        Dict with credits stats
    """
    credit_events = [e for e in events if e.get("name") == "credits.delta"]

    if not credit_events:
        return {
            "initial_balance": 0,
            "final_balance": 0,
            "total_deltas": 0,
            "net_change": 0,
            "trajectory": [],
        }

    # Track running balance - credits data is in refs, not payload
    balance = 0
    trajectory = []
    for e in credit_events:
        refs = e.get("refs", {})
        delta = refs.get("delta", 0)
        balance += delta
        trajectory.append({
            "delta": delta,
            "balance": balance,
            "reason": refs.get("reason", "unknown"),
        })

    return {
        "initial_balance": trajectory[0]["balance"] - trajectory[0]["delta"] if trajectory else 0,
        "final_balance": balance,
        "total_deltas": len(credit_events),
        "net_change": balance - (trajectory[0]["balance"] - trajectory[0]["delta"]) if trajectory else 0,
        "trajectory": trajectory,
    }


def compute_stats_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute all stats from event list.

    Args:
        events: List of event dicts

    Returns:
        Comprehensive stats dict
    """
    event_counts = Counter(e.get("name", "unknown") for e in events)

    return {
        "event_count": len(events),
        "event_types": dict(event_counts),
        "branching": compute_branching_factor(events),
        "entropy": compute_suggestion_entropy(events),
        "write_rate": compute_write_rate(events),
        "backtracks": detect_backtracks(events),
        "credits": compute_credits_trajectory(events),
    }


def format_stats_report(stats: Dict[str, Any]) -> str:
    """
    Format stats as human-readable report.

    Args:
        stats: Stats dict from compute_stats_from_events

    Returns:
        Formatted string report
    """
    lines = [
        "=" * 60,
        "FIELD-KIT DEBUG STATS",
        "=" * 60,
        "",
        f"Total Events: {stats['event_count']}",
        "",
        "Event Types:",
    ]

    for name, count in sorted(stats["event_types"].items()):
        lines.append(f"  {name}: {count}")

    lines.extend([
        "",
        "--- Branching Factor ---",
        f"  Decision points: {stats['branching']['decision_points']}",
        f"  Total choices: {stats['branching']['total_choices']}",
        f"  Avg branching: {stats['branching']['branching_factor']}",
        "",
        "--- Suggestion Entropy ---",
        f"  Entropy: {stats['entropy']['entropy']} (max: {stats['entropy'].get('max_entropy', 'N/A')})",
        f"  Total suggestions: {stats['entropy']['total_suggestions']}",
        "  Distribution:",
    ])

    for intent, prob in stats["entropy"]["intent_distribution"].items():
        lines.append(f"    {intent}: {prob}")

    lines.extend([
        "",
        "--- Write Rate ---",
        f"  Duration: {stats['write_rate']['duration_seconds']}s",
        f"  Events/min: {stats['write_rate']['events_per_minute']}",
        f"  Commits/min: {stats['write_rate']['commits_per_minute']}",
        "",
        "--- Backtracks ---",
        f"  Count: {stats['backtracks']['backtrack_count']}",
        f"  Has backtracks: {stats['backtracks']['has_backtracks']}",
        "",
        "--- Credits ---",
        f"  Initial: {stats['credits']['initial_balance']}",
        f"  Final: {stats['credits']['final_balance']}",
        f"  Net change: {stats['credits']['net_change']}",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)
