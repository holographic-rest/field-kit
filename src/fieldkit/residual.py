"""
Field-Kit v0.1 Residual Module Architecture (Sprint S01)

Implements residual/identity module pattern for safe incremental upgrades.
Inspired by ResNet architecture: each module can be an identity function (delta=0)
or propose small changes (delta) that are added to input state.

Key properties:
- precheck(): Validate and normalize before transformation
- propose_delta(): Generate delta (can be empty dict for identity)
- apply(): state_out = state_in + delta (residual addition)

This architecture enables:
- Gradient-like debugging (trace what each module changed)
- Safe rollback (remove module = identity)
- Incremental upgrades (add modules without breaking existing flow)

See: docs/architecture/ARCHITECTURE_RESIDUAL.md for full design notes.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResidualTrace:
    """Trace record for a single module invocation."""
    module_name: str
    prechecked_state_hash: str
    delta: Dict[str, Any]
    confidence: float
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_name": self.module_name,
            "prechecked_state_hash": self.prechecked_state_hash,
            "delta": self.delta,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


def _hash_state(state: Dict[str, Any]) -> str:
    """Compute deterministic hash of state dict for tracing."""
    serialized = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


class ResidualModule(ABC):
    """
    Base class for residual modules.

    Each module implements the residual pattern:
    - precheck(): Validate/normalize input state
    - propose_delta(): Return delta to add (can be empty)
    - apply(): Combine state + delta

    Subclasses must implement precheck() and propose_delta().
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self._last_trace: Optional[ResidualTrace] = None

    @abstractmethod
    def precheck(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize input state before transformation.

        Args:
            state: Input state dict

        Returns:
            Validated/normalized state (may be same or modified copy)

        Raises:
            ValueError: If state fails validation
        """
        pass

    @abstractmethod
    def propose_delta(self, prechecked_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Propose delta to add to state.

        Args:
            prechecked_state: State that passed precheck()

        Returns:
            Delta dict to merge (empty dict = identity/no-op)
        """
        pass

    def apply(self, state: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply delta to state: state_out = state_in + delta.

        Default implementation does shallow merge. Override for
        custom merge semantics (e.g., deep merge, list append).

        Args:
            state: Original state
            delta: Delta from propose_delta()

        Returns:
            New state with delta applied
        """
        return {**state, **delta}

    def run(
        self,
        state: Dict[str, Any],
        confidence: float = 1.0,
    ) -> tuple[Dict[str, Any], ResidualTrace]:
        """
        Execute full residual pipeline: precheck → propose_delta → apply.

        Args:
            state: Input state
            confidence: Module confidence score (for tracing)

        Returns:
            Tuple of (output_state, trace)
        """
        # Step 1: Precheck
        prechecked = self.precheck(state)
        state_hash = _hash_state(prechecked)

        # Step 2: Propose delta
        delta = self.propose_delta(prechecked)

        # Step 3: Apply
        output = self.apply(prechecked, delta)

        # Create trace
        trace = ResidualTrace(
            module_name=self.name,
            prechecked_state_hash=state_hash,
            delta=delta,
            confidence=confidence,
        )
        self._last_trace = trace

        # Log if delta is non-empty
        if delta:
            logger.debug(
                f"[{self.name}] delta applied: {len(delta)} keys, hash={state_hash}"
            )

        return output, trace


class IdentityModule(ResidualModule):
    """
    Identity module - passes state through unchanged.

    Useful for:
    - Placeholder in pipeline
    - Debugging (verify state at a point)
    - Disabling a module without removing it
    """

    def precheck(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    def propose_delta(self, prechecked_state: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # Identity = no change


class ResidualPipeline:
    """
    Chain of ResidualModules executed in sequence.

    Each module's output becomes the next module's input.
    Collects traces from all modules for debugging.
    """

    def __init__(self, modules: Optional[List[ResidualModule]] = None):
        self.modules: List[ResidualModule] = modules or []
        self._traces: List[ResidualTrace] = []

    def add(self, module: ResidualModule) -> "ResidualPipeline":
        """Add module to pipeline (fluent API)."""
        self.modules.append(module)
        return self

    def run(self, state: Dict[str, Any]) -> tuple[Dict[str, Any], List[ResidualTrace]]:
        """
        Execute all modules in sequence.

        Args:
            state: Initial state

        Returns:
            Tuple of (final_state, list_of_traces)
        """
        self._traces = []
        current = state

        for module in self.modules:
            current, trace = module.run(current)
            self._traces.append(trace)

        return current, self._traces

    @property
    def traces(self) -> List[ResidualTrace]:
        """Get traces from last run."""
        return self._traces

    def summary(self) -> Dict[str, Any]:
        """Get summary of last pipeline run."""
        if not self._traces:
            return {"status": "not_run"}

        non_identity = [t for t in self._traces if t.delta]
        return {
            "modules_count": len(self.modules),
            "modules_with_delta": len(non_identity),
            "total_keys_changed": sum(len(t.delta) for t in self._traces),
            "module_names": [m.name for m in self.modules],
            "traces": [t.to_dict() for t in self._traces],
        }
