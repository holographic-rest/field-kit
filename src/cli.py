#!/usr/bin/env python3
"""
Field-Kit v0.1 CLI

Headless CLI for executing the Golden Flow without a GUI.

Commands:
- init: Initialize store, create Network and Episode 0
- tutorial:start: Log tutorial.started event
- item:create: Create an Item (Q by default)
- item:archive: Archive an Item
- suggestions:show: Present bond suggestions (events-only)
- bond:create: Create a draft Bond
- bond:run: Run a Bond (success path)
- holologue:run: Run Holologue on selected items
- ledger:open: Open ledger view and print objects/events
- curate:item:add: Add an Item to curated list
- curate:item:remove: Remove an Item from curated list
- curate:bond:add: Add a Bond to curated list
- curate:bond:remove: Remove a Bond from curated list
- curated:view: View curated projection (canon)
- export:episode: Export full Episode JSON
- export:curated: Export curated projection JSON
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from fieldkit import (
    # Schemas
    Network, Episode, Item, Bond,
    Vec3, ActorRef,
    ItemProvenanceUser, ItemProvenanceBond, ItemProvenanceHolologue,
    # ID generators
    generate_network_id, generate_episode_id, generate_item_id,
    generate_bond_id, now_iso,
    # Actors
    SYSTEM_ACTOR, USER_ACTOR,
    # Store
    Store, get_store, reset_store, dict_to_item, dict_to_episode,
    # Events
    EventLogger, get_logger,
    # Spin Recipes
    generate_suggestions_for_item,
    generate_proposals_for_holologue,
)


class FieldKitCLI:
    """Field-Kit v0.1 CLI implementation."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.store = get_store(data_dir)
        self.logger = EventLogger(self.store)
        self._credits_balance = 0
        self._network_id: Optional[str] = None
        self._episode_id: Optional[str] = None

    def _load_context(self):
        """Load the current network and episode from store."""
        networks = self.store.load_networks()
        if networks:
            self._network_id = networks[0]["id"]
            episodes = self.store.load_episodes({"network_id": self._network_id})
            if episodes:
                # Get the active episode (most recent)
                self._episode_id = episodes[-1]["id"]
                # Load credits balance
                self._credits_balance = self.store.compute_credits_balance(self._episode_id)

    def _require_init(self):
        """Ensure the store is initialized."""
        if not self.store.is_initialized():
            print("Error: Store not initialized. Run 'init' first.")
            sys.exit(1)
        self._load_context()

    # === Credits helpers ===

    def _log_credits(
        self,
        delta: int,
        reason: str,
        item_id: Optional[str] = None,
        bond_id: Optional[str] = None,
        output_item_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ):
        """Log a credits.delta event."""
        self._credits_balance += delta
        self.logger.credits_delta(
            network_id=self._network_id,
            episode_id=self._episode_id,
            delta=delta,
            balance_after=self._credits_balance,
            reason=reason,
            item_id=item_id,
            bond_id=bond_id,
            output_item_id=output_item_id,
            event_id=event_id,
        )

    # === Commands ===

    def cmd_init(self):
        """
        Initialize the store: create Network, Episode 0, seed credits.

        Events logged:
        - app.first_run.started
        - episode.created
        - credits.delta (seed +100)
        - store.commit
        """
        if self.store.is_initialized():
            print("Store already initialized.")
            self._load_context()
            print(f"  Network: {self._network_id}")
            print(f"  Episode: {self._episode_id}")
            print(f"  Credits: {self._credits_balance}")
            return

        # Create Network
        network_id = generate_network_id()
        episode_id = generate_episode_id()
        now = now_iso()

        network = Network(
            id=network_id,
            scope="private",
            title="My Field",
            description="Local Blank Field workspace",
            root_episode_id=episode_id,
            active_episode_id=episode_id,
            created_by="system",
            created_by_actor=SYSTEM_ACTOR,
            created_at=now,
            updated_at=now,
        )
        self.store.upsert_network(network)

        # Create Episode 0
        episode = Episode(
            id=episode_id,
            network_id=network_id,
            scope="private",
            title="Session 0",
            ordinal=0,
            status="active",
            started_at=now,
            last_active_at=now,
            created_by="system",
            created_by_actor=SYSTEM_ACTOR,
            created_at=now,
            updated_at=now,
        )
        self.store.upsert_episode(episode)

        # Set context
        self._network_id = network_id
        self._episode_id = episode_id
        self._credits_balance = 0

        # Log events
        self.logger.app_first_run_started(network_id, episode_id)
        self.logger.episode_created(network_id, episode_id, "Session 0", ordinal=0)

        # Seed credits
        self._log_credits(delta=100, reason="seed")

        # Commit
        self.logger.store_commit(network_id, episode_id)

        print("Store initialized.")
        print(f"  Network: {network_id}")
        print(f"  Episode: {episode_id} (Session 0)")
        print(f"  Credits: {self._credits_balance}")

    def cmd_tutorial_start(self):
        """Log tutorial.started event."""
        self._require_init()

        self.logger.tutorial_started(self._network_id, self._episode_id)

        print("Tutorial started.")

    def cmd_item_create(
        self,
        title: str = "My Field Item",
        body: Optional[str] = None,
        item_type: str = "Q",
    ):
        """
        Create an Item (Q by default).

        Events logged:
        - item.created
        - credits.delta (+1 for item_created)
        - store.commit
        """
        self._require_init()

        item_id = generate_item_id()
        now = now_iso()

        item = Item(
            id=item_id,
            network_id=self._network_id,
            episode_id=self._episode_id,
            scope="private",
            type=item_type,
            title=title,
            body=body,
            position=Vec3(x=0, y=0, z=0),
            provenance=ItemProvenanceUser(created_by="user"),
            created_at=now,
            updated_at=now,
            created_by_actor=USER_ACTOR,
        )
        self.store.upsert_item(item)

        # Log events
        self.logger.item_created(
            self._network_id, self._episode_id,
            item_id=item_id, item_type=item_type, title=title,
        )

        # Credits reward
        self._log_credits(delta=1, reason="item_created", item_id=item_id)

        # Commit
        self.logger.store_commit(self._network_id, self._episode_id)

        print(f"Item created: {item_id}")
        print(f"  Type: {item_type}")
        print(f"  Title: {title}")
        print(f"  Credits: {self._credits_balance}")
        return item_id

    def cmd_suggestions_show(self, item_id: str):
        """
        Show bond suggestions for an item (events-only; no Bond created).

        Uses Spin Recipes to generate exactly 4 content-shaped suggestions
        with anchor phrase from the Item title.

        Events logged:
        - bond.suggestions.presented
        """
        self._require_init()

        # Get the item
        item = self.store.get_item(item_id)
        if not item:
            print(f"Error: Item {item_id} not found.")
            sys.exit(1)

        # Generate 4 suggestions using Spin Recipes
        suggestions = generate_suggestions_for_item(
            item_title=item["title"],
            item_body=item.get("body"),
        )

        # Log event (events-only; no Bond created)
        self.logger.bond_suggestions_presented(
            self._network_id, self._episode_id,
            item_id=item_id, suggestions=suggestions,
        )

        print(f"Suggestions presented for item {item_id}:")
        for i, s in enumerate(suggestions, 1):
            recipe_id = s.get("recipe_id", "unknown")
            print(f"  {i}. [{recipe_id}] {s['prompt_text']}")

        return suggestions

    def cmd_bond_create(
        self,
        input_item_ids: List[str],
        prompt_text: str,
        intent_type: Optional[str] = None,
        recipe_id: Optional[str] = None,
    ):
        """
        Create a draft Bond.

        Events logged:
        - bond.draft_created (with optional recipe_id in refs)
        - store.commit
        """
        self._require_init()

        # Verify all input items exist
        for item_id in input_item_ids:
            if not self.store.get_item(item_id):
                print(f"Error: Item {item_id} not found.")
                sys.exit(1)

        bond_id = generate_bond_id()
        now = now_iso()

        bond = Bond(
            id=bond_id,
            network_id=self._network_id,
            episode_id=self._episode_id,
            scope="private",
            input_item_ids=input_item_ids,
            prompt_text=prompt_text,
            intent_type=intent_type,
            status="draft",
            output_item_id=None,
            created_by="user",
            created_by_actor=USER_ACTOR,
            created_at=now,
            updated_at=now,
        )
        self.store.upsert_bond(bond)

        # Log event (with optional recipe_id in refs)
        self.logger.bond_draft_created(
            self._network_id, self._episode_id,
            bond_id=bond_id,
            input_item_ids=input_item_ids,
            prompt_text=prompt_text,
            origin=recipe_id,  # recipe_id goes in origin field per spec
        )

        # Commit
        self.logger.store_commit(self._network_id, self._episode_id)

        print(f"Bond draft created: {bond_id}")
        print(f"  Inputs: {input_item_ids}")
        print(f"  Prompt: {prompt_text}")
        if recipe_id:
            print(f"  Recipe: {recipe_id}")
        return bond_id

    def cmd_bond_run(
        self,
        bond_id: str,
        output_type: str = "M",
        force_fail: bool = False,
        fail_reason: str = "forced_failure",
    ):
        """
        Run a Bond (success or failure path).

        Success path events:
        - bond.run_requested
        - credits.delta (-10 for bond_run_spend)
        - bond.executed
        - credits.delta (+3 for bond_executed_reward)
        - store.commit

        Failure path events (force_fail=True):
        - bond.run_requested
        - credits.delta (-10 for bond_run_spend)
        - bond.execution_failed
        - credits.delta (+10 for bond_run_refund)
        - store.commit
        """
        self._require_init()

        bond_dict = self.store.get_bond(bond_id)
        if not bond_dict:
            print(f"Error: Bond {bond_id} not found.")
            sys.exit(1)

        if bond_dict["status"] == "executed":
            print(f"Error: Bond {bond_id} already executed.")
            sys.exit(1)

        # Log run requested
        self.logger.bond_run_requested(
            self._network_id, self._episode_id,
            bond_id=bond_id,
        )

        # Spend credits
        self._log_credits(delta=-10, reason="bond_run_spend", bond_id=bond_id)

        # Check for forced failure
        if force_fail:
            now = now_iso()

            # Set last_error on Bond (keep status=draft, no output_item_id)
            from fieldkit.schemas import ErrorInfo
            bond_dict["last_error"] = ErrorInfo(
                message=fail_reason,
                at=now,
                code="FORCED_FAILURE",
            ).to_dict()
            bond_dict["updated_at"] = now

            # Re-save the bond
            from fieldkit.store_jsonl import dict_to_bond
            bond = dict_to_bond(bond_dict)
            self.store.upsert_bond(bond)

            # Log execution_failed
            self.logger.bond_execution_failed(
                self._network_id, self._episode_id,
                bond_id=bond_id,
                reason=fail_reason,
            )

            # Refund credits
            self._log_credits(delta=10, reason="bond_run_refund", bond_id=bond_id)

            # Commit
            self.logger.store_commit(self._network_id, self._episode_id)

            print(f"Bond execution failed: {bond_id}")
            print(f"  Reason: {fail_reason}")
            print(f"  Credits: {self._credits_balance} (refunded)")
            return None

        # Success path: Create output item
        output_item_id = generate_item_id()
        now = now_iso()

        # Generate output content based on prompt
        output_title = f"Output from Bond {bond_id[:12]}..."
        output_body = f"Generated content for prompt: {bond_dict['prompt_text']}"

        output_item = Item(
            id=output_item_id,
            network_id=self._network_id,
            episode_id=self._episode_id,
            scope="private",
            type=output_type,
            title=output_title,
            body=output_body,
            position=Vec3(x=1.4, y=0.2, z=0),
            provenance=ItemProvenanceBond(
                bond_id=bond_id,
                input_item_ids=bond_dict["input_item_ids"],
            ),
            created_at=now,
            updated_at=now,
            created_by_actor=SYSTEM_ACTOR,
        )
        self.store.upsert_item(output_item)

        # Update bond to executed
        bond_dict["status"] = "executed"
        bond_dict["output_item_id"] = output_item_id
        bond_dict["executed_at"] = now
        bond_dict["execution_count"] = (bond_dict.get("execution_count") or 0) + 1
        bond_dict["updated_at"] = now

        # Re-save the bond
        from fieldkit.store_jsonl import dict_to_bond
        bond = dict_to_bond(bond_dict)
        self.store.upsert_bond(bond)

        # Log executed
        self.logger.bond_executed(
            self._network_id, self._episode_id,
            bond_id=bond_id,
            input_item_ids=bond_dict["input_item_ids"],
            output_item_id=output_item_id,
            execution_count=bond_dict["execution_count"],
        )

        # Reward credits
        self._log_credits(
            delta=3, reason="bond_executed_reward",
            bond_id=bond_id, output_item_id=output_item_id,
        )

        # Commit
        self.logger.store_commit(self._network_id, self._episode_id)

        print(f"Bond executed: {bond_id}")
        print(f"  Output Item: {output_item_id} (type={output_type})")
        print(f"  Credits: {self._credits_balance}")
        return output_item_id

    def cmd_holologue_run(
        self,
        selected_item_ids: List[str],
        artifact_kind: str = "plan",
        force_fail: bool = False,
        fail_reason: str = "forced_failure",
    ):
        """
        Run Holologue on selected items.

        Success path events:
        - holologue.run_requested
        - credits.delta (-20 for holologue_run_spend)
        - holologue.completed
        - credits.delta (+5 for holologue_completed_reward)
        - bond.proposals.presented (optional)
        - store.commit

        Failure path events (force_fail=True):
        - holologue.run_requested
        - credits.delta (-20 for holologue_run_spend)
        - holologue.failed
        - credits.delta (+20 for holologue_run_refund)
        - store.commit

        Validation failure (< 2 items):
        - holologue.validation_failed (no spend, no refund)
        """
        self._require_init()

        # Validate: need at least 2 items
        if len(selected_item_ids) < 2:
            self.logger.holologue_validation_failed(
                self._network_id, self._episode_id,
                reason="selection_too_small",
            )
            print("Error: Holologue requires at least 2 items.")
            sys.exit(1)

        # Verify all items exist
        for item_id in selected_item_ids:
            if not self.store.get_item(item_id):
                self.logger.holologue_validation_failed(
                    self._network_id, self._episode_id,
                    reason="item_not_found",
                )
                print(f"Error: Item {item_id} not found.")
                sys.exit(1)

        # Log run requested
        run_event = self.logger.holologue_run_requested(
            self._network_id, self._episode_id,
            selected_item_ids=selected_item_ids,
            artifact_kind=artifact_kind,
        )

        # Spend credits
        self._log_credits(
            delta=-20, reason="holologue_run_spend",
            event_id=run_event.id,
        )

        # Check for forced failure
        if force_fail:
            # Log holologue.failed
            self.logger.holologue_failed(
                self._network_id, self._episode_id,
                reason=fail_reason,
            )

            # Refund credits
            self._log_credits(
                delta=20, reason="holologue_run_refund",
                event_id=run_event.id,
            )

            # Commit
            self.logger.store_commit(self._network_id, self._episode_id)

            print(f"Holologue failed:")
            print(f"  Reason: {fail_reason}")
            print(f"  Credits: {self._credits_balance} (refunded)")
            return None

        # Success path: Create output item
        output_item_id = generate_item_id()
        now = now_iso()

        output_title = f"Holologue artifact ({artifact_kind})"
        output_body = f"Generated {artifact_kind} from {len(selected_item_ids)} items."

        # Need to create holologue.completed event first to get its ID for provenance
        # This matches the spec requirement that provenance.holologue_event_id references
        # the completion event ID

        # Create output item with placeholder event ID (we'll update this)
        completed_event = self.logger.holologue_completed(
            self._network_id, self._episode_id,
            selected_item_ids=selected_item_ids,
            output_item_id=output_item_id,
            artifact_kind=artifact_kind,
        )

        output_item = Item(
            id=output_item_id,
            network_id=self._network_id,
            episode_id=self._episode_id,
            scope="private",
            type="H",
            title=output_title,
            body=output_body,
            position=Vec3(x=0.6, y=-1.0, z=0),
            provenance=ItemProvenanceHolologue(
                holologue_event_id=completed_event.id,
                selected_item_ids=selected_item_ids,
                artifact_kind=artifact_kind,
            ),
            created_at=now,
            updated_at=now,
            created_by_actor=SYSTEM_ACTOR,
        )
        self.store.upsert_item(output_item)

        # Reward credits
        self._log_credits(
            delta=5, reason="holologue_completed_reward",
            output_item_id=output_item_id,
        )

        # Emit proposals using Spin Recipes (events-only)
        proposals = generate_proposals_for_holologue(
            holologue_output_title=output_title,
            holologue_output_body=output_body,
        )
        self.logger.bond_proposals_presented(
            self._network_id, self._episode_id,
            source_output_item_id=output_item_id,
            suggestions=proposals,
        )

        # Commit
        self.logger.store_commit(self._network_id, self._episode_id)

        print(f"Holologue completed: {output_item_id}")
        print(f"  Artifact kind: {artifact_kind}")
        print(f"  Selected items: {len(selected_item_ids)}")
        print(f"  Credits: {self._credits_balance}")
        print("  Proposals presented (events-only):")
        for i, p in enumerate(proposals, 1):
            recipe_id = p.get("recipe_id", "unknown")
            print(f"    {i}. [{recipe_id}] {p['prompt_text'][:50]}...")
        return output_item_id

    def cmd_ledger_open(self):
        """
        Open ledger view and print objects/events.

        Events logged:
        - ledger.opened
        """
        self._require_init()

        # Log ledger opened
        self.logger.ledger_opened(self._network_id, self._episode_id)

        # Load all data
        networks = self.store.load_networks()
        episodes = self.store.load_episodes()
        items = self.store.load_items()
        bonds = self.store.load_bonds()
        events = self.store.load_events(episode_id=self._episode_id)

        print("=" * 60)
        print("LEDGER VIEW")
        print("=" * 60)

        print("\n--- Objects ---")
        print(f"Networks: {len(networks)}")
        print(f"Episodes: {len(episodes)}")
        print(f"Items: {len(items)}")
        for item in items:
            print(f"  - {item['id']}: type={item['type']}, title={item['title'][:30]}...")
        print(f"Bonds: {len(bonds)}")
        for bond in bonds:
            print(f"  - {bond['id']}: status={bond['status']}, output_item_id={bond.get('output_item_id')}")

        print("\n--- Events ---")
        print(f"Total events: {len(events)}")
        for event in events:
            print(f"  {event['seq']:3d}. {event['name']:<30} (qdpi={event['qdpi']}, dir={event['direction']})")

        print("\n--- Credits ---")
        credits_events = [e for e in events if e["name"] == "credits.delta"]
        print(f"Credits events: {len(credits_events)}")
        for ce in credits_events:
            refs = ce["refs"]
            print(f"  seq={ce['seq']}: delta={refs['delta']:+d}, balance={refs['balance_after']}, reason={refs['reason']}")

        print(f"\nFinal Credits Balance: {self._credits_balance}")
        print("=" * 60)

    # === Item Archive ===

    def cmd_item_archive(self, item_id: str):
        """
        Archive an Item.

        Events logged:
        - store.commit
        """
        self._require_init()

        item_dict = self.store.get_item(item_id)
        if not item_dict:
            print(f"Error: Item {item_id} not found.")
            sys.exit(1)

        if item_dict.get("archived_at"):
            print(f"Item {item_id} is already archived.")
            return

        # Update item
        now = now_iso()
        item_dict["archived_at"] = now
        item_dict["updated_at"] = now

        item = dict_to_item(item_dict)
        self.store.upsert_item(item)

        # Commit (no episode.curated_* events per spec)
        self.logger.store_commit(self._network_id, self._episode_id, refs={"item_id": item_id})

        print(f"Item archived: {item_id}")

    # === Curation Commands ===

    def _get_episode_object(self) -> Tuple[dict, Episode]:
        """Get current episode dict and object."""
        episode_dict = self.store.get_episode(self._episode_id)
        if not episode_dict:
            print(f"Error: Episode {self._episode_id} not found.")
            sys.exit(1)
        return episode_dict, dict_to_episode(episode_dict)

    def _save_episode_curation(self, episode: Episode, modified_ids: List[str] = None):
        """Save episode after curation change and log store.commit."""
        episode.updated_at = now_iso()
        self.store.upsert_episode(episode)

        # Log store.commit (NOT episode.curated_* events per spec requirement)
        refs = {"episode_id": self._episode_id}
        if modified_ids:
            refs["modified_ids"] = modified_ids
        self.logger.store_commit(self._network_id, self._episode_id, refs=refs)

    def cmd_curate_item_add(self, item_id: str):
        """
        Add an Item to the curated list.

        Rules (from Canon Policy):
        - Uniqueness: no duplicates
        - Referential validity: must exist in same network + episode
        - Order: append to end
        """
        self._require_init()

        # Verify item exists
        item_dict = self.store.get_item(item_id)
        if not item_dict:
            print(f"Warning: Item {item_id} not found. Refusing to add.")
            return False

        # Verify same network + episode
        if item_dict["network_id"] != self._network_id:
            print(f"Warning: Item {item_id} belongs to different network. Refusing to add.")
            return False
        if item_dict["episode_id"] != self._episode_id:
            print(f"Warning: Item {item_id} belongs to different episode. Refusing to add.")
            return False

        # Get episode
        episode_dict, episode = self._get_episode_object()

        # Initialize curated list if needed
        if episode.curated_item_ids is None:
            episode.curated_item_ids = []

        # Check for duplicates
        if item_id in episode.curated_item_ids:
            print(f"Item {item_id} already curated.")
            return False

        # Append to end (preserve order)
        episode.curated_item_ids.append(item_id)

        # Save
        self._save_episode_curation(episode, modified_ids=[item_id])

        print(f"Item {item_id} added to curated list.")
        return True

    def cmd_curate_item_remove(self, item_id: str):
        """Remove an Item from the curated list."""
        self._require_init()

        episode_dict, episode = self._get_episode_object()

        if episode.curated_item_ids is None or item_id not in episode.curated_item_ids:
            print(f"Item {item_id} not in curated list.")
            return False

        episode.curated_item_ids.remove(item_id)

        # Save
        self._save_episode_curation(episode, modified_ids=[item_id])

        print(f"Item {item_id} removed from curated list.")
        return True

    def cmd_curate_bond_add(self, bond_id: str):
        """
        Add a Bond to the curated list.

        Rules:
        - Draft bonds allowed if explicitly curated, but warn
        """
        self._require_init()

        # Verify bond exists
        bond_dict = self.store.get_bond(bond_id)
        if not bond_dict:
            print(f"Warning: Bond {bond_id} not found. Refusing to add.")
            return False

        # Verify same network + episode
        if bond_dict["network_id"] != self._network_id:
            print(f"Warning: Bond {bond_id} belongs to different network. Refusing to add.")
            return False
        if bond_dict["episode_id"] != self._episode_id:
            print(f"Warning: Bond {bond_id} belongs to different episode. Refusing to add.")
            return False

        # Warn if draft
        if bond_dict["status"] == "draft":
            print(f"Warning: Bond {bond_id} is a draft. Curating anyway as explicitly requested.")

        # Get episode
        episode_dict, episode = self._get_episode_object()

        # Initialize curated list if needed
        if episode.curated_bond_ids is None:
            episode.curated_bond_ids = []

        # Check for duplicates
        if bond_id in episode.curated_bond_ids:
            print(f"Bond {bond_id} already curated.")
            return False

        # Append to end (preserve order)
        episode.curated_bond_ids.append(bond_id)

        # Save
        self._save_episode_curation(episode, modified_ids=[bond_id])

        print(f"Bond {bond_id} added to curated list.")
        return True

    def cmd_curate_bond_remove(self, bond_id: str):
        """Remove a Bond from the curated list."""
        self._require_init()

        episode_dict, episode = self._get_episode_object()

        if episode.curated_bond_ids is None or bond_id not in episode.curated_bond_ids:
            print(f"Bond {bond_id} not in curated list.")
            return False

        episode.curated_bond_ids.remove(bond_id)

        # Save
        self._save_episode_curation(episode, modified_ids=[bond_id])

        print(f"Bond {bond_id} removed from curated list.")
        return True

    # === Curated Projection (Canon) ===

    def compute_curated_projection(self) -> Dict[str, Any]:
        """
        Compute the curated projection (canon) for the current episode.

        Returns:
        {
            "curated_items": [...],  # resolved, ordered, filtered
            "curated_bonds": [...],  # resolved, ordered, filtered
            "warnings": [...]        # list of warning messages
        }

        Projection algorithm (from Canon Policy):
        1. Start with curated lists (preserve order)
        2. Filter to: exists + same network_id + episode_id + not archived
        3. Warn on missing, archived, wrong scope IDs
        4. Draft bonds appear only if explicitly listed (warn)
        """
        self._require_init()

        episode_dict = self.store.get_episode(self._episode_id)
        if not episode_dict:
            return {"curated_items": [], "curated_bonds": [], "warnings": ["Episode not found"]}

        curated_item_ids = episode_dict.get("curated_item_ids") or []
        curated_bond_ids = episode_dict.get("curated_bond_ids") or []

        curated_items = []
        curated_bonds = []
        warnings = []

        # Process curated items
        for item_id in curated_item_ids:
            item = self.store.get_item(item_id)

            if not item:
                warnings.append(f"Item {item_id}: not found (ignored)")
                continue

            if item["network_id"] != self._network_id:
                warnings.append(f"Item {item_id}: wrong network (ignored)")
                continue

            if item["episode_id"] != self._episode_id:
                warnings.append(f"Item {item_id}: wrong episode (ignored)")
                continue

            if item.get("archived_at"):
                warnings.append(f"Item {item_id}: archived (filtered from projection)")
                continue

            curated_items.append(item)

        # Process curated bonds
        for bond_id in curated_bond_ids:
            bond = self.store.get_bond(bond_id)

            if not bond:
                warnings.append(f"Bond {bond_id}: not found (ignored)")
                continue

            if bond["network_id"] != self._network_id:
                warnings.append(f"Bond {bond_id}: wrong network (ignored)")
                continue

            if bond["episode_id"] != self._episode_id:
                warnings.append(f"Bond {bond_id}: wrong episode (ignored)")
                continue

            if bond.get("archived_at"):
                warnings.append(f"Bond {bond_id}: archived (filtered from projection)")
                continue

            # Draft bonds are allowed if explicitly curated, but warn
            if bond["status"] == "draft":
                warnings.append(f"Bond {bond_id}: is a draft (included as explicitly curated)")

            curated_bonds.append(bond)

        return {
            "curated_items": curated_items,
            "curated_bonds": curated_bonds,
            "warnings": warnings,
        }

    def _get_lineage_badge(self, item: dict) -> str:
        """Get lineage badge string for an item based on provenance."""
        prov = item.get("provenance", {})
        created_by = prov.get("created_by", "user")

        if created_by == "bond":
            bond_id = prov.get("bond_id", "unknown")
            n_inputs = len(prov.get("input_item_ids", []))
            return f"Derived from Bond {bond_id[:16]}... (from {n_inputs} input{'s' if n_inputs != 1 else ''})"

        elif created_by == "holologue":
            n_items = len(prov.get("selected_item_ids", []))
            kind = prov.get("artifact_kind", "unknown")
            return f"Holologue artifact (from {n_items} items) · kind={kind}"

        else:
            return f"Created by {created_by}"

    def cmd_curated_view(self):
        """
        Display the curated projection (canon) view.

        This is the CLI equivalent of "Ledger → Curated (Canon Projection)" tab.
        """
        self._require_init()

        projection = self.compute_curated_projection()

        print("=" * 60)
        print("CURATED PROJECTION (CANON)")
        print("=" * 60)

        # Curated Items
        print("\n--- Curated Items (ordered) ---")
        items = projection["curated_items"]
        if not items:
            print("  (none)")
        else:
            for i, item in enumerate(items, 1):
                lineage = self._get_lineage_badge(item)
                print(f"  {i}. {item['id']}")
                print(f"     Type: {item['type']}, Title: {item['title'][:40]}...")
                print(f"     Lineage: {lineage}")

        # Curated Bonds
        print("\n--- Curated Bonds (ordered) ---")
        bonds = projection["curated_bonds"]
        if not bonds:
            print("  (none)")
        else:
            for i, bond in enumerate(bonds, 1):
                status_marker = " [DRAFT]" if bond["status"] == "draft" else ""
                print(f"  {i}. {bond['id']}{status_marker}")
                print(f"     Status: {bond['status']}, Output: {bond.get('output_item_id', 'none')}")
                print(f"     Prompt: {bond['prompt_text'][:40]}...")

        # Warnings
        print("\n--- Warnings ---")
        warnings = projection["warnings"]
        if not warnings:
            print("  (none)")
        else:
            for w in warnings:
                print(f"  ! {w}")

        print("\n" + "=" * 60)
        return projection

    # === Export Commands ===

    def _get_default_export_dir(self) -> Path:
        """Get default export directory."""
        return self.store.data_dir.parent / "outputs"

    def cmd_export_episode(self, output_path: Optional[Path] = None) -> Path:
        """
        Export full Episode JSON.

        Includes: network, episode, items, bonds, events, derived credits balance
        """
        self._require_init()

        # Determine output path
        if output_path is None:
            export_dir = self._get_default_export_dir()
            export_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = export_dir / f"export_episode_{ts}.json"

        # Gather data
        network = self.store.get_network(self._network_id)
        episode = self.store.get_episode(self._episode_id)
        items = self.store.load_items({"episode_id": self._episode_id})
        bonds = self.store.load_bonds({"episode_id": self._episode_id})
        events = self.store.load_events(episode_id=self._episode_id)
        credits_balance = self.store.compute_credits_balance(self._episode_id)

        export_data = {
            "export_type": "episode",
            "exported_at": now_iso(),
            "network": network,
            "episode": episode,
            "items": items,
            "bonds": bonds,
            "qdpi_events": events,
            "derived": {
                "credits_balance": credits_balance,
                "item_count": len(items),
                "bond_count": len(bonds),
                "event_count": len(events),
            },
        }

        # Write to file
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"Episode exported to: {output_path}")
        return output_path

    def cmd_export_curated(self, output_path: Optional[Path] = None) -> Path:
        """
        Export curated projection JSON.

        Includes: episode_id, network_id, raw curated lists, resolved items/bonds, warnings
        """
        self._require_init()

        # Determine output path
        if output_path is None:
            export_dir = self._get_default_export_dir()
            export_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = export_dir / f"export_curated_{ts}.json"

        # Get episode for raw lists
        episode = self.store.get_episode(self._episode_id)

        # Compute projection
        projection = self.compute_curated_projection()

        export_data = {
            "export_type": "curated_projection",
            "exported_at": now_iso(),
            "network_id": self._network_id,
            "episode_id": self._episode_id,
            "curated_item_ids": episode.get("curated_item_ids") or [],
            "curated_bond_ids": episode.get("curated_bond_ids") or [],
            "curated_items": projection["curated_items"],
            "curated_bonds": projection["curated_bonds"],
            "warnings": projection["warnings"],
        }

        # Write to file
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"Curated projection exported to: {output_path}")
        return output_path


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Field-Kit v0.1 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=None,
        help="Data directory (default: prototype/data/)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    subparsers.add_parser("init", help="Initialize store")

    # tutorial:start
    subparsers.add_parser("tutorial:start", help="Start tutorial")

    # item:create
    p_item = subparsers.add_parser("item:create", help="Create an item")
    p_item.add_argument("--title", "-t", default="My Field Item", help="Item title")
    p_item.add_argument("--body", "-b", default=None, help="Item body")
    p_item.add_argument("--type", default="Q", choices=["Q", "M", "D", "H"], help="Item type")

    # suggestions:show
    p_sug = subparsers.add_parser("suggestions:show", help="Show bond suggestions")
    p_sug.add_argument("item_id", help="Item ID to show suggestions for")

    # bond:create
    p_bond = subparsers.add_parser("bond:create", help="Create a bond draft")
    p_bond.add_argument("--inputs", "-i", nargs="+", required=True, help="Input item IDs")
    p_bond.add_argument("--prompt", "-p", required=True, help="Prompt text")
    p_bond.add_argument("--intent", default=None, help="Intent type")
    p_bond.add_argument("--recipe", "-r", default=None, help="Recipe ID (from Spin Recipes)")

    # bond:run
    p_run = subparsers.add_parser("bond:run", help="Run a bond")
    p_run.add_argument("bond_id", help="Bond ID to run")
    p_run.add_argument("--output-type", "-o", default="M", choices=["M", "D"], help="Output item type")

    # holologue:run
    p_holo = subparsers.add_parser("holologue:run", help="Run holologue")
    p_holo.add_argument("--items", "-i", nargs="+", required=True, help="Selected item IDs")
    p_holo.add_argument("--kind", "-k", default="plan", help="Artifact kind")

    # ledger:open
    subparsers.add_parser("ledger:open", help="Open ledger view")

    # item:archive
    p_archive = subparsers.add_parser("item:archive", help="Archive an item")
    p_archive.add_argument("item_id", help="Item ID to archive")

    # curate:item:add
    p_curate_item_add = subparsers.add_parser("curate:item:add", help="Add item to curated list")
    p_curate_item_add.add_argument("item_id", help="Item ID to curate")

    # curate:item:remove
    p_curate_item_rm = subparsers.add_parser("curate:item:remove", help="Remove item from curated list")
    p_curate_item_rm.add_argument("item_id", help="Item ID to uncurate")

    # curate:bond:add
    p_curate_bond_add = subparsers.add_parser("curate:bond:add", help="Add bond to curated list")
    p_curate_bond_add.add_argument("bond_id", help="Bond ID to curate")

    # curate:bond:remove
    p_curate_bond_rm = subparsers.add_parser("curate:bond:remove", help="Remove bond from curated list")
    p_curate_bond_rm.add_argument("bond_id", help="Bond ID to uncurate")

    # curated:view
    subparsers.add_parser("curated:view", help="View curated projection (canon)")

    # export:episode
    p_export_ep = subparsers.add_parser("export:episode", help="Export full episode JSON")
    p_export_ep.add_argument("--output", "-o", type=Path, default=None, help="Output file path")

    # export:curated
    p_export_cur = subparsers.add_parser("export:curated", help="Export curated projection JSON")
    p_export_cur.add_argument("--output", "-o", type=Path, default=None, help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = FieldKitCLI(args.data_dir)

    if args.command == "init":
        cli.cmd_init()
    elif args.command == "tutorial:start":
        cli.cmd_tutorial_start()
    elif args.command == "item:create":
        cli.cmd_item_create(title=args.title, body=args.body, item_type=args.type)
    elif args.command == "suggestions:show":
        cli.cmd_suggestions_show(args.item_id)
    elif args.command == "bond:create":
        cli.cmd_bond_create(
            input_item_ids=args.inputs,
            prompt_text=args.prompt,
            intent_type=args.intent,
            recipe_id=args.recipe,
        )
    elif args.command == "bond:run":
        cli.cmd_bond_run(args.bond_id, output_type=args.output_type)
    elif args.command == "holologue:run":
        cli.cmd_holologue_run(selected_item_ids=args.items, artifact_kind=args.kind)
    elif args.command == "ledger:open":
        cli.cmd_ledger_open()
    elif args.command == "item:archive":
        cli.cmd_item_archive(args.item_id)
    elif args.command == "curate:item:add":
        cli.cmd_curate_item_add(args.item_id)
    elif args.command == "curate:item:remove":
        cli.cmd_curate_item_remove(args.item_id)
    elif args.command == "curate:bond:add":
        cli.cmd_curate_bond_add(args.bond_id)
    elif args.command == "curate:bond:remove":
        cli.cmd_curate_bond_remove(args.bond_id)
    elif args.command == "curated:view":
        cli.cmd_curated_view()
    elif args.command == "export:episode":
        cli.cmd_export_episode(args.output)
    elif args.command == "export:curated":
        cli.cmd_export_curated(args.output)


if __name__ == "__main__":
    main()
