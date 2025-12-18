#!/usr/bin/env python3
"""
Field-Kit v0.1 Minimal UI

Flask-based local web UI for Field-Kit prototype.
Wraps the headless CLI logic with a web interface.

Run: python3 prototype/ui/app.py
Open: http://localhost:5001
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request

# Load .env file if present (without requiring python-dotenv)
def load_dotenv_simple():
    """Load .env file from repo root if it exists."""
    repo_root = Path(__file__).parent.parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already set (don't override environment)
                    if key and key not in os.environ:
                        os.environ[key] = value

load_dotenv_simple()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import get_store, reset_store
from fieldkit.spin_recipes import generate_suggestions_for_item, generate_proposals_for_holologue

# Get data directory from environment or use default
DATA_DIR = os.environ.get("FIELDKIT_DATA_DIR")
if DATA_DIR:
    DATA_DIR = Path(DATA_DIR)

app = Flask(__name__)


def get_cli():
    """Get a fresh CLI instance."""
    return FieldKitCLI(DATA_DIR)


# === HTML Routes ===

@app.route("/")
def index():
    """Main Field view."""
    return render_template("index.html")


# === API Routes ===

@app.route("/api/status")
def api_status():
    """Get store status."""
    cli = get_cli()
    store = cli.store
    is_init = store.is_initialized()

    result = {
        "initialized": is_init,
        "data_dir": str(store.data_dir),
    }

    if is_init:
        cli._load_context()
        result["network_id"] = cli._network_id
        result["episode_id"] = cli._episode_id
        result["credits"] = cli._credits_balance

    return jsonify(result)


@app.route("/api/init", methods=["POST"])
def api_init():
    """Initialize store."""
    cli = get_cli()
    if cli.store.is_initialized():
        cli._load_context()
        return jsonify({
            "status": "already_initialized",
            "network_id": cli._network_id,
            "episode_id": cli._episode_id,
            "credits": cli._credits_balance,
        })

    cli.cmd_init()
    return jsonify({
        "status": "initialized",
        "network_id": cli._network_id,
        "episode_id": cli._episode_id,
        "credits": cli._credits_balance,
    })


@app.route("/api/items")
def api_items():
    """Get all items for current episode."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized", "items": []})

    cli._load_context()
    items = cli.store.load_items({"episode_id": cli._episode_id})

    # Sort by created_at (oldest first, so newest at bottom)
    items.sort(key=lambda x: x["created_at"])

    return jsonify({"items": items})


@app.route("/api/items", methods=["POST"])
def api_create_item():
    """Create a new item."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    title = data.get("title", "My Field Item")
    body = data.get("body")
    item_type = data.get("type", "Q")

    item_id = cli.cmd_item_create(title=title, body=body, item_type=item_type)

    # Get the created item
    item = cli.store.get_item(item_id)

    return jsonify({
        "status": "created",
        "item": item,
        "credits": cli._credits_balance,
    })


@app.route("/api/items/<item_id>/suggestions")
def api_item_suggestions(item_id):
    """Get suggestions for an item."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item = cli.store.get_item(item_id)
    if not item:
        return jsonify({"error": "item_not_found"}), 404

    # Generate suggestions using Spin Recipes
    suggestions = generate_suggestions_for_item(
        item_title=item["title"],
        item_body=item.get("body"),
    )

    # Log event (through CLI to maintain consistency)
    cli._load_context()
    cli.logger.bond_suggestions_presented(
        cli._network_id, cli._episode_id,
        item_id=item_id, suggestions=suggestions,
    )

    return jsonify({
        "item_id": item_id,
        "suggestions": suggestions,
    })


@app.route("/api/bonds")
def api_bonds():
    """Get all bonds for current episode."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized", "bonds": []})

    cli._load_context()
    bonds = cli.store.load_bonds({"episode_id": cli._episode_id})

    return jsonify({"bonds": bonds})


@app.route("/api/bonds", methods=["POST"])
def api_create_bond():
    """Create a draft bond."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    input_item_ids = data.get("input_item_ids", [])
    prompt_text = data.get("prompt_text", "")
    intent_type = data.get("intent_type")
    recipe_id = data.get("recipe_id")

    if not input_item_ids or not prompt_text:
        return jsonify({"error": "missing_fields"}), 400

    bond_id = cli.cmd_bond_create(
        input_item_ids=input_item_ids,
        prompt_text=prompt_text,
        intent_type=intent_type,
        recipe_id=recipe_id,
    )

    bond = cli.store.get_bond(bond_id)

    return jsonify({
        "status": "created",
        "bond": bond,
    })


@app.route("/api/bonds/<bond_id>/run", methods=["POST"])
def api_run_bond(bond_id):
    """Run a bond."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    output_type = data.get("output_type", "M")

    output_item_id = cli.cmd_bond_run(bond_id, output_type=output_type)

    if output_item_id:
        output_item = cli.store.get_item(output_item_id)
        bond = cli.store.get_bond(bond_id)
        return jsonify({
            "status": "executed",
            "output_item": output_item,
            "bond": bond,
            "credits": cli._credits_balance,
        })
    else:
        bond = cli.store.get_bond(bond_id)
        return jsonify({
            "status": "failed",
            "bond": bond,
            "credits": cli._credits_balance,
        })


@app.route("/api/bonds/run-suggestion", methods=["POST"])
def api_run_suggestion():
    """Create and run a bond from a suggestion in one step.

    This provides the "one-click" UX: clicking a suggestion immediately
    creates a Bond draft + runs it + produces an M output Item.
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    input_item_ids = data.get("input_item_ids", [])
    prompt_text = data.get("prompt_text", "")
    intent_type = data.get("intent_type")
    recipe_id = data.get("recipe_id")
    output_type = data.get("output_type", "M")  # Suggestions produce M

    if not input_item_ids or not prompt_text:
        return jsonify({"error": "missing_fields"}), 400

    # Create bond draft
    bond_id = cli.cmd_bond_create(
        input_item_ids=input_item_ids,
        prompt_text=prompt_text,
        intent_type=intent_type,
        recipe_id=recipe_id,
    )

    # Run the bond
    output_item_id = cli.cmd_bond_run(bond_id, output_type=output_type)

    if output_item_id:
        output_item = cli.store.get_item(output_item_id)
        bond = cli.store.get_bond(bond_id)
        return jsonify({
            "status": "executed",
            "output_item": output_item,
            "bond": bond,
            "credits": cli._credits_balance,
        })
    else:
        bond = cli.store.get_bond(bond_id)
        return jsonify({
            "status": "failed",
            "bond": bond,
            "credits": cli._credits_balance,
        })


@app.route("/api/holologue/run", methods=["POST"])
def api_run_holologue():
    """Run holologue on selected items."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    selected_item_ids = data.get("selected_item_ids", [])
    artifact_kind = data.get("artifact_kind", "plan")

    if len(selected_item_ids) < 2:
        # Log validation failed
        cli._load_context()
        cli.logger.holologue_validation_failed(
            cli._network_id, cli._episode_id,
            reason="selection_too_small",
        )
        return jsonify({
            "status": "validation_failed",
            "error": "Holologue requires at least 2 items",
        }), 400

    output_item_id = cli.cmd_holologue_run(
        selected_item_ids=selected_item_ids,
        artifact_kind=artifact_kind,
    )

    if output_item_id:
        output_item = cli.store.get_item(output_item_id)
        # Get proposals
        proposals = generate_proposals_for_holologue(
            holologue_output_title=output_item["title"],
            holologue_output_body=output_item.get("body"),
        )
        return jsonify({
            "status": "completed",
            "output_item": output_item,
            "proposals": proposals,
            "credits": cli._credits_balance,
        })
    else:
        return jsonify({
            "status": "failed",
            "credits": cli._credits_balance,
        })


@app.route("/api/ledger")
def api_ledger():
    """Get ledger data (objects + events)."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"})

    cli._load_context()

    # Log ledger opened
    cli.logger.ledger_opened(cli._network_id, cli._episode_id)

    networks = cli.store.load_networks()
    episodes = cli.store.load_episodes()
    items = cli.store.load_items({"episode_id": cli._episode_id})
    bonds = cli.store.load_bonds({"episode_id": cli._episode_id})
    events = cli.store.load_events(episode_id=cli._episode_id)

    # Get curated projection
    projection = cli.compute_curated_projection()

    return jsonify({
        "networks": networks,
        "episodes": episodes,
        "items": items,
        "bonds": bonds,
        "events": events,
        "curated": projection,
        "credits": cli._credits_balance,
    })


@app.route("/api/credits")
def api_credits():
    """Get credits balance and events."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"balance": 0, "events": []})

    cli._load_context()
    events = cli.store.load_events(episode_id=cli._episode_id)
    credits_events = [e for e in events if e["name"] == "credits.delta"]

    return jsonify({
        "balance": cli._credits_balance,
        "events": credits_events,
    })


@app.route("/api/tutorial/start", methods=["POST"])
def api_tutorial_start():
    """Start tutorial."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    cli.cmd_tutorial_start()

    return jsonify({"status": "started"})


@app.route("/api/curate/item/<item_id>", methods=["POST"])
def api_curate_item_add(item_id):
    """Add item to curated list."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    result = cli.cmd_curate_item_add(item_id)
    projection = cli.compute_curated_projection()

    return jsonify({
        "status": "added" if result else "unchanged",
        "curated": projection,
    })


@app.route("/api/curate/item/<item_id>", methods=["DELETE"])
def api_curate_item_remove(item_id):
    """Remove item from curated list."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    result = cli.cmd_curate_item_remove(item_id)
    projection = cli.compute_curated_projection()

    return jsonify({
        "status": "removed" if result else "unchanged",
        "curated": projection,
    })


@app.route("/api/export/episode")
def api_export_episode():
    """Export full episode JSON."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    cli._load_context()

    # Gather data directly (don't write to file)
    from fieldkit import now_iso
    network = cli.store.get_network(cli._network_id)
    episode = cli.store.get_episode(cli._episode_id)
    items = cli.store.load_items({"episode_id": cli._episode_id})
    bonds = cli.store.load_bonds({"episode_id": cli._episode_id})
    events = cli.store.load_events(episode_id=cli._episode_id)

    export_data = {
        "export_type": "episode",
        "exported_at": now_iso(),
        "network": network,
        "episode": episode,
        "items": items,
        "bonds": bonds,
        "qdpi_events": events,
        "derived": {
            "credits_balance": cli._credits_balance,
            "item_count": len(items),
            "bond_count": len(bonds),
            "event_count": len(events),
        },
    }

    return jsonify(export_data)


@app.route("/api/export/curated")
def api_export_curated():
    """Export curated projection JSON."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    cli._load_context()

    from fieldkit import now_iso
    episode = cli.store.get_episode(cli._episode_id)
    projection = cli.compute_curated_projection()

    export_data = {
        "export_type": "curated_projection",
        "exported_at": now_iso(),
        "network_id": cli._network_id,
        "episode_id": cli._episode_id,
        "curated_item_ids": episode.get("curated_item_ids") or [],
        "curated_bond_ids": episode.get("curated_bond_ids") or [],
        "curated_items": projection["curated_items"],
        "curated_bonds": projection["curated_bonds"],
        "warnings": projection["warnings"],
    }

    return jsonify(export_data)


if __name__ == "__main__":
    print("=" * 60)
    print("Field-Kit v0.1 UI")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR or 'prototype/data/'}")
    print("Starting server at http://localhost:5001")
    print("=" * 60)
    app.run(host="localhost", port=5001, debug=True)
