"""
Field-Kit v0.1 Graph Propagation (Sprint S05)

Implements MPNN-style message passing for graph-aware reranking.

Key concepts:
- Message passing: Aggregate neighbor information to improve node representations
- Graph distance: Use topological distance as a scoring feature
- Residual update: Combine new representations with original (from S01)

This is a deterministic v0.1; later versions can train on click data.
"""

import json
import math
from collections import deque
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field


# Bond type embeddings (simple one-hot style)
BOND_TYPE_WEIGHTS = {
    "clarify": 0.9,
    "clarifies": 0.9,
    "concretize": 0.85,
    "grounds_in": 0.85,
    "connect": 0.8,
    "bridges": 0.8,
    "test": 0.7,
    "expands": 0.75,
    "derives_from": 0.8,
    "default": 0.5,
}


@dataclass
class NodeState:
    """
    State of a node in the graph.

    Contains embedding and metadata for message passing.
    """
    item_id: str
    embedding: List[float]  # Simple feature vector
    recency: float = 0.0    # Recency score (0-1)
    node_type: str = "Q"    # Q/M/D/H
    updated: bool = False   # Has been updated by message passing

    def to_simple_embedding(self) -> List[float]:
        """Get embedding with recency added."""
        return self.embedding + [self.recency]


@dataclass
class Edge:
    """An edge in the bond graph."""
    source_id: str
    target_id: str
    bond_type: str = "default"
    weight: float = 1.0


class BondGraph:
    """
    The bond graph connecting items.

    Nodes = Items
    Edges = Bonds (input_item_ids -> output_item_id)
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else None
        self._nodes: Dict[str, NodeState] = {}
        self._edges: List[Edge] = []
        self._adjacency: Dict[str, List[str]] = {}  # item_id -> neighbors
        self._reverse_adjacency: Dict[str, List[str]] = {}  # item_id -> predecessors

        if self.data_dir:
            self._load_graph()

    def _load_graph(self):
        """Load graph from items.jsonl and bonds.jsonl."""
        # Load items as nodes
        items_file = self.data_dir / "items.jsonl"
        if items_file.exists():
            with open(items_file) as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        item_id = item.get("id", "")
                        if item_id:
                            # Create simple embedding from item features
                            embedding = self._item_to_embedding(item)
                            recency = self._compute_recency(item)
                            self._nodes[item_id] = NodeState(
                                item_id=item_id,
                                embedding=embedding,
                                recency=recency,
                                node_type=item.get("type", "Q"),
                            )

        # Load bonds as edges
        bonds_file = self.data_dir / "bonds.jsonl"
        if bonds_file.exists():
            with open(bonds_file) as f:
                for line in f:
                    if line.strip():
                        bond = json.loads(line)
                        if bond.get("status") == "executed":
                            output_id = bond.get("output_item_id")
                            input_ids = bond.get("input_item_ids", [])
                            bond_type = self._infer_bond_type(bond)

                            if output_id:
                                for input_id in input_ids:
                                    edge = Edge(
                                        source_id=input_id,
                                        target_id=output_id,
                                        bond_type=bond_type,
                                        weight=BOND_TYPE_WEIGHTS.get(bond_type, 0.5),
                                    )
                                    self._edges.append(edge)

                                    # Build adjacency
                                    if input_id not in self._adjacency:
                                        self._adjacency[input_id] = []
                                    self._adjacency[input_id].append(output_id)

                                    if output_id not in self._reverse_adjacency:
                                        self._reverse_adjacency[output_id] = []
                                    self._reverse_adjacency[output_id].append(input_id)

    def _item_to_embedding(self, item: Dict[str, Any]) -> List[float]:
        """
        Create simple feature embedding from item.

        Features:
        - Type one-hot (Q, M, D, H)
        - Title length (normalized)
        - Body length (normalized)
        - Has handles
        """
        type_map = {"Q": [1, 0, 0, 0], "M": [0, 1, 0, 0], "D": [0, 0, 1, 0], "H": [0, 0, 0, 1]}
        type_vec = type_map.get(item.get("type", "Q"), [1, 0, 0, 0])

        title = item.get("title") or ""
        body = item.get("body") or ""
        handles = item.get("handles") or []

        title_len = min(len(title) / 100.0, 1.0)
        body_len = min(len(body) / 1000.0, 1.0)
        has_handles = 1.0 if handles else 0.0

        return type_vec + [title_len, body_len, has_handles]

    def _compute_recency(self, item: Dict[str, Any]) -> float:
        """Compute recency score (simple: based on created_at if available)."""
        # For now, return 0.5 (neutral)
        # Future: parse created_at and compute decay
        return 0.5

    def _infer_bond_type(self, bond: Dict[str, Any]) -> str:
        """Infer bond type from prompt text."""
        prompt = (bond.get("prompt_text") or "").lower()

        if "precise" in prompt or "conditions" in prompt:
            return "clarify"
        elif "checklist" in prompt or "steps" in prompt:
            return "concretize"
        elif "map" in prompt or "flow" in prompt:
            return "connect"
        elif "test" in prompt or "falsif" in prompt:
            return "test"
        else:
            return "default"

    def get_node(self, item_id: str) -> Optional[NodeState]:
        """Get node state by ID."""
        return self._nodes.get(item_id)

    def get_neighbors(self, item_id: str, direction: str = "both") -> List[str]:
        """
        Get neighbors of a node.

        Args:
            item_id: Node ID
            direction: "out" (successors), "in" (predecessors), or "both"

        Returns:
            List of neighbor item IDs
        """
        neighbors = []
        if direction in ("out", "both"):
            neighbors.extend(self._adjacency.get(item_id, []))
        if direction in ("in", "both"):
            neighbors.extend(self._reverse_adjacency.get(item_id, []))
        return list(set(neighbors))

    def compute_graph_distance(
        self,
        source_id: str,
        target_id: str,
        max_distance: int = 10,
    ) -> int:
        """
        Compute shortest path distance between two nodes.

        Uses BFS for unweighted shortest path.

        Args:
            source_id: Starting node
            target_id: Target node
            max_distance: Maximum distance to search

        Returns:
            Distance (0 if same node, -1 if unreachable)
        """
        if source_id == target_id:
            return 0

        if source_id not in self._nodes or target_id not in self._nodes:
            return -1

        # BFS
        visited = {source_id}
        queue = deque([(source_id, 0)])

        while queue:
            current, dist = queue.popleft()

            if dist >= max_distance:
                continue

            for neighbor in self.get_neighbors(current, "both"):
                if neighbor == target_id:
                    return dist + 1

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return -1  # Unreachable

    def get_all_distances_from(
        self,
        source_id: str,
        max_distance: int = 10,
    ) -> Dict[str, int]:
        """
        Compute distances from source to all reachable nodes.

        Returns:
            Dict mapping item_id -> distance
        """
        if source_id not in self._nodes:
            return {}

        distances = {source_id: 0}
        queue = deque([(source_id, 0)])

        while queue:
            current, dist = queue.popleft()

            if dist >= max_distance:
                continue

            for neighbor in self.get_neighbors(current, "both"):
                if neighbor not in distances:
                    distances[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))

        return distances


def compute_messages(
    graph: BondGraph,
    node_ids: List[str],
) -> Dict[str, List[float]]:
    """
    Compute messages for each node from its neighbors.

    Message = sum of (neighbor_embedding * edge_weight * recency)

    Args:
        graph: The bond graph
        node_ids: Nodes to compute messages for

    Returns:
        Dict mapping node_id -> aggregated message vector
    """
    messages = {}

    for node_id in node_ids:
        node = graph.get_node(node_id)
        if not node:
            continue

        message = [0.0] * len(node.embedding)
        neighbor_count = 0

        for neighbor_id in graph.get_neighbors(node_id, "both"):
            neighbor = graph.get_node(neighbor_id)
            if neighbor:
                # Weight by recency
                weight = neighbor.recency * 0.5 + 0.5

                # Add weighted embedding
                for i, val in enumerate(neighbor.embedding):
                    message[i] += val * weight

                neighbor_count += 1

        # Normalize
        if neighbor_count > 0:
            message = [m / neighbor_count for m in message]

        messages[node_id] = message

    return messages


def update_nodes(
    graph: BondGraph,
    node_ids: List[str],
    messages: Dict[str, List[float]],
    residual_weight: float = 0.5,
) -> Dict[str, List[float]]:
    """
    Update node embeddings with residual connection.

    new_embedding = residual_weight * original + (1 - residual_weight) * message

    Args:
        graph: The bond graph
        node_ids: Nodes to update
        messages: Messages for each node
        residual_weight: Weight for original embedding (higher = more conservative)

    Returns:
        Dict mapping node_id -> updated embedding
    """
    updated = {}

    for node_id in node_ids:
        node = graph.get_node(node_id)
        if not node:
            continue

        original = node.embedding
        message = messages.get(node_id, original)

        if len(message) != len(original):
            # Dimension mismatch, skip update
            updated[node_id] = original
            continue

        # Residual update
        new_embedding = []
        for orig, msg in zip(original, message):
            new_val = residual_weight * orig + (1 - residual_weight) * msg
            new_embedding.append(new_val)

        updated[node_id] = new_embedding
        node.embedding = new_embedding
        node.updated = True

    return updated


def message_passing_step(
    graph: BondGraph,
    node_ids: Optional[List[str]] = None,
    T: int = 2,
    residual_weight: float = 0.5,
) -> Dict[str, List[float]]:
    """
    Run T rounds of message passing.

    Each round:
    1. Compute messages from neighbors
    2. Update nodes with residual connection

    Args:
        graph: The bond graph
        node_ids: Nodes to propagate (default: all)
        T: Number of rounds
        residual_weight: Weight for residual connection

    Returns:
        Dict mapping node_id -> final embedding
    """
    if node_ids is None:
        node_ids = list(graph._nodes.keys())

    final_embeddings = {}

    for t in range(T):
        messages = compute_messages(graph, node_ids)
        updated = update_nodes(graph, node_ids, messages, residual_weight)
        final_embeddings.update(updated)

    return final_embeddings


def score_with_graph_features(
    subject_id: str,
    candidate_ids: List[str],
    graph: BondGraph,
    run_propagation: bool = True,
    T: int = 2,
) -> Dict[str, Dict[str, Any]]:
    """
    Score candidates using graph features.

    Features computed:
    - graph_distance: Shortest path from subject to candidate
    - embedding_similarity: Cosine similarity of (propagated) embeddings
    - neighborhood_overlap: Jaccard similarity of neighbor sets

    Args:
        subject_id: Current/subject item ID
        candidate_ids: IDs of candidate items
        graph: The bond graph
        run_propagation: Whether to run message passing first
        T: Rounds of message passing

    Returns:
        Dict mapping candidate_id -> {distance, similarity, overlap, score}
    """
    all_ids = [subject_id] + candidate_ids

    # Run message passing if requested
    if run_propagation:
        message_passing_step(graph, all_ids, T=T)

    # Get subject info
    subject_node = graph.get_node(subject_id)
    subject_neighbors = set(graph.get_neighbors(subject_id, "both"))

    # Compute distances
    distances = graph.get_all_distances_from(subject_id)

    results = {}

    for cand_id in candidate_ids:
        cand_node = graph.get_node(cand_id)
        cand_neighbors = set(graph.get_neighbors(cand_id, "both"))

        # Graph distance
        dist = distances.get(cand_id, -1)

        # Embedding similarity
        similarity = 0.0
        if subject_node and cand_node:
            similarity = _cosine_similarity(
                subject_node.embedding,
                cand_node.embedding
            )

        # Neighborhood overlap (Jaccard)
        overlap = 0.0
        if subject_neighbors or cand_neighbors:
            intersection = len(subject_neighbors & cand_neighbors)
            union = len(subject_neighbors | cand_neighbors)
            overlap = intersection / union if union > 0 else 0.0

        # Compute combined score
        # Distance: closer is better (decay with distance)
        if dist == -1:
            dist_score = 0.1  # Unreachable: low score
        elif dist == 0:
            dist_score = 1.0  # Same node
        else:
            dist_score = 1.0 / (1.0 + dist)  # Decay with distance

        # Combined score
        score = 0.4 * dist_score + 0.4 * (similarity + 1.0) / 2.0 + 0.2 * overlap

        results[cand_id] = {
            "graph_distance": dist,
            "embedding_similarity": similarity,
            "neighborhood_overlap": overlap,
            "graph_score": score,
        }

    return results


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2) or not vec1:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class GraphReranker:
    """
    Reranks candidates using graph propagation.

    Usage:
        reranker = GraphReranker(data_dir)
        reranked = reranker.rerank(subject_id, candidates)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        propagation_rounds: int = 2,
        graph_weight: float = 0.3,
    ):
        """
        Initialize the reranker.

        Args:
            data_dir: Path to data directory with items/bonds
            propagation_rounds: Number of message passing rounds
            graph_weight: Weight for graph score vs original score
        """
        self.data_dir = Path(data_dir) if data_dir else None
        self.propagation_rounds = propagation_rounds
        self.graph_weight = graph_weight
        self._graph: Optional[BondGraph] = None

    def _ensure_graph(self):
        """Lazy load the graph."""
        if self._graph is None and self.data_dir:
            self._graph = BondGraph(self.data_dir)

    def rerank(
        self,
        subject_id: str,
        candidates: List[Any],
        use_propagation: bool = True,
    ) -> List[Any]:
        """
        Rerank candidates using graph features.

        Args:
            subject_id: Current item ID
            candidates: List of Candidate objects
            use_propagation: Whether to use message passing

        Returns:
            Candidates with updated scores and graph_distance
        """
        from .candidate_set import Candidate

        self._ensure_graph()

        if not self._graph or not candidates:
            return candidates

        # Get candidate IDs
        candidate_ids = []
        for c in candidates:
            if hasattr(c, 'target_id') and c.target_id:
                candidate_ids.append(c.target_id)
            elif hasattr(c, 'candidate_id'):
                # No target, use subject as reference
                pass

        # If no target IDs, compute distances anyway (best effort)
        if not candidate_ids:
            # Assign graph distances based on subject's neighborhood
            distances = self._graph.get_all_distances_from(subject_id)
            for c in candidates:
                c.graph_distance = 1  # Default to 1-hop for suggestions
            return candidates

        # Score with graph features
        scores = score_with_graph_features(
            subject_id,
            candidate_ids,
            self._graph,
            run_propagation=use_propagation,
            T=self.propagation_rounds,
        )

        # Update candidates
        for c in candidates:
            target = getattr(c, 'target_id', None)
            if target and target in scores:
                graph_info = scores[target]
                c.graph_distance = graph_info.get("graph_distance", -1)

                # Blend scores
                original_score = getattr(c, 'score', 0.5)
                graph_score = graph_info.get("graph_score", 0.5)
                c.score = (
                    (1 - self.graph_weight) * original_score +
                    self.graph_weight * graph_score
                )

        return candidates

    def get_graph_distance(self, source_id: str, target_id: str) -> int:
        """Get graph distance between two items."""
        self._ensure_graph()
        if not self._graph:
            return -1
        return self._graph.compute_graph_distance(source_id, target_id)

    def get_neighborhood(self, item_id: str, hops: int = 1) -> List[str]:
        """Get items within N hops of given item."""
        self._ensure_graph()
        if not self._graph:
            return []

        distances = self._graph.get_all_distances_from(item_id, max_distance=hops)
        return [k for k, v in distances.items() if 0 < v <= hops]
