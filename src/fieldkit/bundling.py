"""
Field-Kit v0.1 Bundling Proposals (Sprint S06)

Graph-level compaction with reversibility. Bundling suggests consolidating
related items into a single bundle, but never executes - only produces proposals.

Key concepts:
- BundleProposal: Reversible proposal with constituent IDs
- Detection: Find cluster candidates by title similarity + shared bonds
- Proposals only: No automatic execution, no deletion

Bundles are "D" type items that reference their constituents.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict


@dataclass
class BundleProposal:
    """
    A proposed bundle that consolidates related items.

    Reversible: keeps constituent_ids so bundle can be "unpacked".
    """
    proposal_id: str
    bundle_title: str
    constituent_ids: List[str]  # Items to be bundled
    action: str = "bundle"
    status: str = "proposed"  # proposed | accepted | rejected | executed
    rationale: str = ""
    similarity_score: float = 0.0  # How similar are the constituents
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "bundle_title": self.bundle_title,
            "constituent_ids": self.constituent_ids,
            "action": self.action,
            "status": self.status,
            "rationale": self.rationale,
            "similarity_score": self.similarity_score,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BundleProposal":
        return cls(
            proposal_id=d["proposal_id"],
            bundle_title=d["bundle_title"],
            constituent_ids=d["constituent_ids"],
            action=d.get("action", "bundle"),
            status=d.get("status", "proposed"),
            rationale=d.get("rationale", ""),
            similarity_score=d.get("similarity_score", 0.0),
            created_at=d.get("created_at"),
        )


def propose_bundle(
    item_ids: List[str],
    bundle_title: str,
    rationale: str = "",
) -> BundleProposal:
    """
    Create a bundle proposal for the given items.

    This does NOT execute bundling - it only creates a proposal.

    Args:
        item_ids: List of item IDs to bundle
        bundle_title: Title for the proposed bundle
        rationale: Why these items should be bundled

    Returns:
        BundleProposal ready for review
    """
    from datetime import datetime

    proposal_id = f"bp_{uuid.uuid4().hex[:24].upper()}"

    return BundleProposal(
        proposal_id=proposal_id,
        bundle_title=bundle_title,
        constituent_ids=item_ids,
        action="bundle",
        status="proposed",
        rationale=rationale,
        created_at=datetime.utcnow().isoformat() + "Z",
    )


def detect_bundle_candidates(
    data_dir: Path,
    min_cluster_size: int = 2,
    max_proposals: int = 5,
) -> List[BundleProposal]:
    """
    Detect potential bundle candidates using clustering.

    Uses two signals:
    1. Title prefix similarity (items with same prefix likely related)
    2. Shared bonds (items connected to same targets)

    Args:
        data_dir: Path to data directory
        min_cluster_size: Minimum items to form a bundle
        max_proposals: Maximum number of proposals to return

    Returns:
        List of BundleProposal objects
    """
    data_dir = Path(data_dir)
    items_file = data_dir / "items.jsonl"
    bonds_file = data_dir / "bonds.jsonl"

    # Load items
    items = []
    if items_file.exists():
        with open(items_file) as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))

    if len(items) < min_cluster_size:
        return []

    # Load bonds
    bonds = []
    if bonds_file.exists():
        with open(bonds_file) as f:
            for line in f:
                if line.strip():
                    bond = json.loads(line)
                    if bond.get("status") == "executed":
                        bonds.append(bond)

    # Build item lookup
    item_by_id = {item.get("id"): item for item in items}

    # Cluster 1: Title prefix clusters
    prefix_clusters = _cluster_by_title_prefix(items)

    # Cluster 2: Bond connectivity clusters
    bond_clusters = _cluster_by_shared_bonds(items, bonds)

    # Merge clusters (union of evidence)
    all_clusters = _merge_clusters(prefix_clusters, bond_clusters)

    # Filter by minimum size and create proposals
    proposals = []
    for cluster_id, item_ids in all_clusters.items():
        if len(item_ids) >= min_cluster_size:
            # Generate bundle title from first item
            first_item = item_by_id.get(item_ids[0], {})
            first_title = first_item.get("title", "Untitled")

            # Create bundle title
            if len(item_ids) <= 3:
                bundle_title = f"Bundle: {first_title[:30]}..."
            else:
                bundle_title = f"Bundle: {len(item_ids)} related items"

            # Compute similarity score
            sim_score = _compute_cluster_similarity(item_ids, item_by_id, bonds)

            proposal = BundleProposal(
                proposal_id=f"bp_{cluster_id}",
                bundle_title=bundle_title,
                constituent_ids=item_ids,
                action="bundle",
                status="proposed",
                rationale=f"Detected {len(item_ids)} related items by title/bond similarity",
                similarity_score=sim_score,
            )
            proposals.append(proposal)

    # Sort by similarity score descending
    proposals.sort(key=lambda p: p.similarity_score, reverse=True)

    return proposals[:max_proposals]


def _cluster_by_title_prefix(items: List[Dict[str, Any]], prefix_len: int = 20) -> Dict[str, List[str]]:
    """
    Cluster items by title prefix.

    Items with the same prefix (first N chars, normalized) are grouped.
    """
    clusters: Dict[str, List[str]] = defaultdict(list)

    for item in items:
        title = (item.get("title") or "").lower().strip()
        # Normalize: take first N chars, hash for stability
        prefix = title[:prefix_len]
        prefix_hash = hashlib.md5(prefix.encode()).hexdigest()[:8]

        item_id = item.get("id")
        if item_id:
            clusters[prefix_hash].append(item_id)

    # Only keep clusters with 2+ items
    return {k: v for k, v in clusters.items() if len(v) >= 2}


def _cluster_by_shared_bonds(
    items: List[Dict[str, Any]],
    bonds: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """
    Cluster items that share bond connections.

    Items that are both inputs to the same bond, or share an output,
    are likely related.
    """
    clusters: Dict[str, List[str]] = defaultdict(list)

    # Build: for each item, what bonds is it part of?
    item_to_bonds: Dict[str, Set[str]] = defaultdict(set)
    for bond in bonds:
        bond_id = bond.get("id", "")
        input_ids = bond.get("input_item_ids", [])
        output_id = bond.get("output_item_id")

        for iid in input_ids:
            item_to_bonds[iid].add(bond_id)
        if output_id:
            item_to_bonds[output_id].add(bond_id)

    # Find items that share 2+ bonds
    item_ids = list(item_to_bonds.keys())
    for i, id1 in enumerate(item_ids):
        for id2 in item_ids[i + 1:]:
            shared = item_to_bonds[id1] & item_to_bonds[id2]
            if len(shared) >= 1:  # Share at least 1 bond
                # Create cluster key from sorted pair
                cluster_key = f"bond_{min(id1, id2)[:8]}_{max(id1, id2)[:8]}"
                if id1 not in clusters[cluster_key]:
                    clusters[cluster_key].append(id1)
                if id2 not in clusters[cluster_key]:
                    clusters[cluster_key].append(id2)

    return {k: v for k, v in clusters.items() if len(v) >= 2}


def _merge_clusters(
    clusters1: Dict[str, List[str]],
    clusters2: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Merge two cluster dicts, combining overlapping clusters.
    """
    # Simple merge: union by first item ID
    merged: Dict[str, List[str]] = {}
    all_clusters = list(clusters1.values()) + list(clusters2.values())

    # Sort clusters by size descending
    all_clusters.sort(key=len, reverse=True)

    seen_items: Set[str] = set()
    cluster_idx = 0

    for cluster in all_clusters:
        # Filter out already-seen items
        new_items = [iid for iid in cluster if iid not in seen_items]
        if len(new_items) >= 2:
            cluster_key = f"merged_{cluster_idx:03d}"
            merged[cluster_key] = new_items
            seen_items.update(new_items)
            cluster_idx += 1

    return merged


def _compute_cluster_similarity(
    item_ids: List[str],
    item_by_id: Dict[str, Dict[str, Any]],
    bonds: List[Dict[str, Any]],
) -> float:
    """
    Compute similarity score for a cluster.

    Higher score = items are more related.
    """
    if len(item_ids) < 2:
        return 0.0

    score = 0.0

    # Title similarity: check common words
    titles = []
    for iid in item_ids:
        item = item_by_id.get(iid, {})
        title = (item.get("title") or "").lower()
        titles.append(set(title.split()))

    if len(titles) >= 2:
        # Jaccard similarity of title words
        intersection = titles[0]
        union = titles[0]
        for t in titles[1:]:
            intersection = intersection & t
            union = union | t

        if union:
            jaccard = len(intersection) / len(union)
            score += jaccard * 0.5  # Title sim worth 0.5

    # Bond connectivity
    item_set = set(item_ids)
    internal_bonds = 0
    for bond in bonds:
        input_ids = set(bond.get("input_item_ids", []))
        output_id = bond.get("output_item_id")

        # Check if bond connects items within cluster
        in_cluster_inputs = input_ids & item_set
        out_in_cluster = output_id in item_set if output_id else False

        if len(in_cluster_inputs) >= 1 and out_in_cluster:
            internal_bonds += 1

    # More internal bonds = higher score
    if internal_bonds > 0:
        score += min(0.5, internal_bonds * 0.2)  # Bond connectivity worth up to 0.5

    return round(score, 3)


def apply_mdl_gate_to_proposals(
    proposals: List[BundleProposal],
    thread_model: Dict[str, Any],
    cohort_stats: Optional[Dict[str, Any]] = None,
) -> List[BundleProposal]:
    """
    Apply MDL structure-vs-noise gate to bundle proposals.

    S09: Uses MDL controls to block mega-bundles and thin-evidence bundles.

    Proposals that fail the gate are marked with:
    - blocked_by_mdl: True
    - mdl_reason: explanation

    Args:
        proposals: List of BundleProposal objects
        thread_model: Current thread context (handles, entities)
        cohort_stats: Optional stats for calibration

    Returns:
        Proposals with gate results applied
    """
    from .mdl_scoring import structure_vs_noise_gate

    for proposal in proposals:
        # Convert proposal to artifact dict for gate
        artifact = {
            "proposal_id": proposal.proposal_id,
            "title": proposal.bundle_title,
            "constituent_ids": proposal.constituent_ids,
            "rationale": proposal.rationale,
        }

        gate_result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        # Attach gate result to proposal dict representation
        proposal_dict = proposal.to_dict()
        proposal_dict["gate_result"] = gate_result

        if not gate_result["allowed"]:
            proposal_dict["blocked_by_mdl"] = True
            proposal_dict["mdl_reason"] = gate_result["reason"]

    return proposals


def format_proposals_report(proposals: List[BundleProposal]) -> str:
    """
    Format bundle proposals as human-readable report.
    """
    if not proposals:
        return "No bundle candidates detected."

    lines = [
        "=" * 60,
        "BUNDLE PROPOSALS",
        "=" * 60,
        "",
        f"Found {len(proposals)} potential bundle(s):",
        "",
    ]

    for i, proposal in enumerate(proposals, 1):
        lines.append(f"--- Proposal {i}: {proposal.proposal_id} ---")
        lines.append(f"  Title: {proposal.bundle_title}")
        lines.append(f"  Constituents: {len(proposal.constituent_ids)} items")
        for cid in proposal.constituent_ids[:5]:  # Show first 5
            lines.append(f"    - {cid}")
        if len(proposal.constituent_ids) > 5:
            lines.append(f"    ... and {len(proposal.constituent_ids) - 5} more")
        lines.append(f"  Similarity: {proposal.similarity_score:.2f}")
        lines.append(f"  Rationale: {proposal.rationale}")
        lines.append(f"  Status: {proposal.status}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Note: These are proposals only. No changes have been made.")
    lines.append("=" * 60)

    return "\n".join(lines)
