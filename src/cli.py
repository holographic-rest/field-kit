#!/usr/bin/env python3
"""
Field-Kit v0.1 CLI

Headless CLI for executing the Golden Flow without a GUI.

Commands:
- init: Initialize store, create Network and Episode 0
- tutorial:start: Log tutorial.started event
- item:create: Create an Item (Q by default)
- suggestions:show: Present bond suggestions (events-only)
- bond:create: Create a draft Bond
- bond:run: Run a Bond (success path)
- holologue:run: Run Holologue on selected items
- ledger:open: Open ledger view and print objects/events
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List

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
    Store, get_store, reset_store,
    # Events
    EventLogger, get_logger,
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

        Events logged:
        - bond.suggestions.presented
        """
        self._require_init()

        # Generate 4 suggestions based on the item
        item = self.store.get_item(item_id)
        if not item:
            print(f"Error: Item {item_id} not found.")
            sys.exit(1)

        # Standard suggestions (per Demo Golden Flow)
        suggestions = [
            {"prompt_text": "Propose a minimal experiment to probe this.", "intent_type": "experiment"},
            {"prompt_text": "List 3 assumptions this depends on.", "intent_type": "clarifies"},
            {"prompt_text": "Write a 5-bullet decision note based on this.", "intent_type": "grounds_in"},
            {"prompt_text": "Expand this into a concrete plan with steps.", "intent_type": "expands"},
        ]

        # Log event (events-only; no Bond created)
        self.logger.bond_suggestions_presented(
            self._network_id, self._episode_id,
            item_id=item_id, suggestions=suggestions,
        )

        print(f"Suggestions presented for item {item_id}:")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s['prompt_text']}")

        return suggestions

    def cmd_bond_create(
        self,
        input_item_ids: List[str],
        prompt_text: str,
        intent_type: Optional[str] = None,
    ):
        """
        Create a draft Bond.

        Events logged:
        - bond.draft_created
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

        # Log event
        self.logger.bond_draft_created(
            self._network_id, self._episode_id,
            bond_id=bond_id,
            input_item_ids=input_item_ids,
            prompt_text=prompt_text,
        )

        # Commit
        self.logger.store_commit(self._network_id, self._episode_id)

        print(f"Bond draft created: {bond_id}")
        print(f"  Inputs: {input_item_ids}")
        print(f"  Prompt: {prompt_text}")
        return bond_id

    def cmd_bond_run(self, bond_id: str, output_type: str = "M"):
        """
        Run a Bond (success path).

        Events logged:
        - bond.run_requested
        - credits.delta (-10 for bond_run_spend)
        - bond.executed
        - credits.delta (+3 for bond_executed_reward)
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

        # Create output item
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
    ):
        """
        Run Holologue on selected items.

        Events logged:
        - holologue.run_requested
        - credits.delta (-20 for holologue_run_spend)
        - holologue.completed
        - credits.delta (+5 for holologue_completed_reward)
        - bond.proposals.presented (optional)
        - store.commit
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

        # Create output item
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

        # Emit proposals (events-only)
        proposals = [
            {"prompt_text": "Expand this plan into a detailed checklist.", "intent_type": "expands"},
            {"prompt_text": "Ground this in measurable metrics.", "intent_type": "grounds_in"},
            {"prompt_text": "Clarify the assumptions this depends on.", "intent_type": "clarifies"},
            {"prompt_text": "Fork two variants: fastest vs most rigorous.", "intent_type": "forks"},
        ]
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
        print("  Proposals presented (events-only)")
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
        )
    elif args.command == "bond:run":
        cli.cmd_bond_run(args.bond_id, output_type=args.output_type)
    elif args.command == "holologue:run":
        cli.cmd_holologue_run(selected_item_ids=args.items, artifact_kind=args.kind)
    elif args.command == "ledger:open":
        cli.cmd_ledger_open()


if __name__ == "__main__":
    main()
