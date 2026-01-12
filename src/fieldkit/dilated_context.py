"""
Field-Kit v0.1 Dilated Context Sampler (Sprint S04)

Implements multi-scale context aggregation using dilated sampling.

Key insight from research:
- Local scale: immediate neighborhood (subject item, recent events)
- Mid scale: dilation steps back (2, 4, 8, 16 events)
- Far scale: farther history (16+ events back)

This provides systematic context coverage without losing resolution.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass


# Dilation schedule: offsets into event history
# Negative values = events before current position
DILATION_OFFSETS = [-1, -2, -4, -8, -16, -32]

# Scale thresholds
# local: offset 0 (subject item itself)
# mid: offsets -1 to -8
# far: offsets -16 and beyond
MID_THRESHOLD = -8
FAR_THRESHOLD = -16


def offset_to_scale(offset: int) -> str:
    """Convert dilation offset to scale label."""
    if offset == 0:
        return "local"
    elif offset >= FAR_THRESHOLD:
        return "mid"
    else:
        return "far"


@dataclass
class ContextItem:
    """An item sampled from context with its metadata."""
    item_id: str
    title: str
    body: Optional[str]
    scale: str
    dilation_offset: int


@dataclass
class ContextPack:
    """A pack of context items at multiple scales."""
    local_items: List[ContextItem]
    mid_items: List[ContextItem]
    far_items: List[ContextItem]

    def all_items(self) -> List[ContextItem]:
        """Get all items across scales."""
        return self.local_items + self.mid_items + self.far_items

    def item_ids_by_scale(self) -> Dict[str, List[str]]:
        """Get item IDs grouped by scale."""
        return {
            "local": [i.item_id for i in self.local_items],
            "mid": [i.item_id for i in self.mid_items],
            "far": [i.item_id for i in self.far_items],
        }

    def scales_present(self) -> Set[str]:
        """Get which scales have items."""
        scales = set()
        if self.local_items:
            scales.add("local")
        if self.mid_items:
            scales.add("mid")
        if self.far_items:
            scales.add("far")
        return scales


class DilatedContextSampler:
    """
    Samples context at multiple scales using dilated offsets.

    Uses event history to find items at various temporal distances.
    """

    def __init__(
        self,
        data_dir: Path,
        episode_id: Optional[str] = None,
        dilation_offsets: Optional[List[int]] = None,
    ):
        self.data_dir = Path(data_dir)
        self.episode_id = episode_id
        self.dilation_offsets = dilation_offsets or DILATION_OFFSETS

        # Cache for items
        self._items_cache: Dict[str, Dict[str, Any]] = {}
        self._events_cache: Optional[List[Dict[str, Any]]] = None

    def _load_items(self) -> Dict[str, Dict[str, Any]]:
        """Load all items into cache."""
        if self._items_cache:
            return self._items_cache

        items_file = self.data_dir / "items.jsonl"
        if not items_file.exists():
            return {}

        with open(items_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    self._items_cache[item["id"]] = item

        return self._items_cache

    def _load_events(self) -> List[Dict[str, Any]]:
        """Load events chronologically."""
        if self._events_cache is not None:
            return self._events_cache

        # Try both event file names
        events_file = self.data_dir / "qdpi_events.jsonl"
        if not events_file.exists():
            events_file = self.data_dir / "events.jsonl"
        if not events_file.exists():
            self._events_cache = []
            return self._events_cache

        events = []
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    # Filter by episode if specified
                    if self.episode_id and event.get("episode_id") != self.episode_id:
                        continue
                    events.append(event)

        # Sort by sequence number
        events.sort(key=lambda e: (e.get("ts", ""), e.get("seq", 0)))
        self._events_cache = events
        return self._events_cache

    def _get_item_ids_from_event(self, event: Dict[str, Any]) -> List[str]:
        """Extract item IDs from an event."""
        refs = event.get("refs", {})
        item_ids = []

        # Direct item references
        if "item_id" in refs:
            item_ids.append(refs["item_id"])
        if "output_item_id" in refs:
            item_ids.append(refs["output_item_id"])
        if "input_item_ids" in refs:
            item_ids.extend(refs.get("input_item_ids", []))
        if "selected_item_ids" in refs:
            item_ids.extend(refs.get("selected_item_ids", []))

        return item_ids

    def _get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID."""
        items = self._load_items()
        return items.get(item_id)

    def sample(self, subject_item_id: str) -> ContextPack:
        """
        Sample context at multiple scales around a subject item.

        Args:
            subject_item_id: The item to sample context for

        Returns:
            ContextPack with local, mid, and far items
        """
        events = self._load_events()
        items = self._load_items()

        # Find position of subject item in event history
        subject_position = -1
        for i, event in enumerate(events):
            if subject_item_id in self._get_item_ids_from_event(event):
                subject_position = i
                # Keep looking to find latest mention
                continue

        if subject_position < 0:
            # Subject not found in events, return just local
            subject_item = items.get(subject_item_id)
            if subject_item:
                local = ContextItem(
                    item_id=subject_item_id,
                    title=subject_item.get("title", ""),
                    body=subject_item.get("body"),
                    scale="local",
                    dilation_offset=0,
                )
                return ContextPack(local_items=[local], mid_items=[], far_items=[])
            return ContextPack(local_items=[], mid_items=[], far_items=[])

        # Build context pack
        local_items = []
        mid_items = []
        far_items = []
        seen_ids: Set[str] = {subject_item_id}

        # Add subject item as local
        subject_item = items.get(subject_item_id)
        if subject_item:
            local_items.append(ContextItem(
                item_id=subject_item_id,
                title=subject_item.get("title", ""),
                body=subject_item.get("body"),
                scale="local",
                dilation_offset=0,
            ))

        # Sample at dilation offsets
        for offset in self.dilation_offsets:
            target_idx = subject_position + offset

            if target_idx < 0 or target_idx >= len(events):
                continue

            event = events[target_idx]
            event_item_ids = self._get_item_ids_from_event(event)

            for item_id in event_item_ids:
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                item = items.get(item_id)
                if not item:
                    continue

                scale = offset_to_scale(offset)
                context_item = ContextItem(
                    item_id=item_id,
                    title=item.get("title", ""),
                    body=item.get("body"),
                    scale=scale,
                    dilation_offset=offset,
                )

                if scale == "local":
                    local_items.append(context_item)
                elif scale == "mid":
                    mid_items.append(context_item)
                else:
                    far_items.append(context_item)

        return ContextPack(
            local_items=local_items,
            mid_items=mid_items,
            far_items=far_items,
        )

    def get_neighbors(self, item_ids: List[str]) -> List[str]:
        """
        Get 1-hop neighbors via bonds.

        Best-effort: returns empty list if bonds aren't accessible.
        """
        bonds_file = self.data_dir / "bonds.jsonl"
        if not bonds_file.exists():
            return []

        neighbors: Set[str] = set()
        try:
            with open(bonds_file) as f:
                for line in f:
                    if line.strip():
                        bond = json.loads(line)
                        input_ids = set(bond.get("input_item_ids", []))
                        output_id = bond.get("output_item_id")

                        # Check if any of our items are in this bond
                        for item_id in item_ids:
                            if item_id in input_ids:
                                # Add output as neighbor
                                if output_id:
                                    neighbors.add(output_id)
                            if item_id == output_id:
                                # Add inputs as neighbors
                                neighbors.update(input_ids)
        except Exception:
            pass

        # Remove items we already have
        return [n for n in neighbors if n not in item_ids]


def find_matching_text_in_item(
    item: Dict[str, Any],
    keywords: List[str],
    max_span_length: int = 300,
) -> Optional[Tuple[str, int, int]]:
    """
    Find a text span in an item that contains any of the keywords.

    Returns:
        Tuple of (text_span, span_start, span_end) or None if not found
    """
    title = item.get("title") or ""
    body = item.get("body") or ""
    full_text = title + "\n" + body

    if not full_text.strip():
        return None

    full_text_lower = full_text.lower()

    # Try to find a keyword
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in full_text_lower:
            # Find the position
            start_pos = full_text_lower.index(keyword_lower)

            # Extract context around the keyword
            context_start = max(0, start_pos - 50)
            context_end = min(len(full_text), start_pos + len(keyword) + 100)

            # Find sentence boundaries
            text_before = full_text[context_start:start_pos]
            text_after = full_text[start_pos:context_end]

            # Trim to sentence boundaries if possible
            if ". " in text_before:
                sentence_start = text_before.rfind(". ") + 2
                context_start = context_start + sentence_start

            if ". " in text_after[len(keyword):]:
                sentence_end = text_after.find(". ", len(keyword)) + 1
                context_end = start_pos + sentence_end

            # Extract span
            span = full_text[context_start:context_end].strip()

            # Truncate if too long
            if len(span) > max_span_length:
                span = span[:max_span_length - 3] + "..."
                context_end = context_start + max_span_length

            return (span, context_start, context_end)

    # Fallback: return first sentence or title
    if title:
        return (title[:max_span_length], 0, min(len(title), max_span_length))

    return None
