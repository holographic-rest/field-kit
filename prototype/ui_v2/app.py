#!/usr/bin/env python3
"""
Field-Kit v2 UI - Wrapper-styled interface

Flask-based UI with ChatGPT-like dark theme.
Reuses backend logic from fieldkit package.

Run: python3 prototype/ui_v2/app.py
Open: http://localhost:5002
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request

# Load .env file if present
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
                    if key and key not in os.environ:
                        os.environ[key] = value

load_dotenv_simple()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import get_store, reset_store
from fieldkit.spin_recipes import generate_suggestions_for_item, generate_proposals_for_holologue
from fieldkit.generation import get_generation_mode, get_last_generation_warning

# Get data directory from environment or use default
DATA_DIR = os.environ.get("FIELDKIT_DATA_DIR")
if DATA_DIR:
    DATA_DIR = Path(DATA_DIR)

# Flask app with custom template and static folders
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)


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
        "generation_mode": get_generation_mode(),  # Sprint G2: GEN indicator
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

    # Sort by created_at (oldest first)
    items.sort(key=lambda x: x["created_at"])

    return jsonify({"items": items})


@app.route("/api/items", methods=["POST"])
def api_create_item():
    """Create a new item (always Q type)."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    body = data.get("body", "")

    # Always create Q (Queue) items - this is the key change
    item_type = "Q"

    # Use first line or truncated body as title
    lines = body.strip().split('\n')
    title = lines[0][:60] if lines else "Queue Item"
    if len(lines[0]) > 60:
        title += "..."

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
    """Get suggestions for an item.

    Query params:
    - debug=true: Include debug info (candidate handles, suggestion source)
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item = cli.store.get_item(item_id)
    if not item:
        return jsonify({"error": "item_not_found"}), 404

    # Check if debug mode requested
    debug_mode = request.args.get("debug", "").lower() == "true"

    # Generate suggestions using the new suggestion engine
    suggestions = generate_suggestions_for_item(
        item_title=item["title"],
        item_body=item.get("body"),
        return_debug=debug_mode,
    )

    # Extract debug info if present
    debug_info = None
    if debug_mode and suggestions and "_debug" in suggestions[0]:
        debug_info = suggestions[0].pop("_debug")

    # Log event
    cli._load_context()
    cli.logger.bond_suggestions_presented(
        cli._network_id, cli._episode_id,
        item_id=item_id, suggestions=suggestions,
    )

    response = {
        "item_id": item_id,
        "suggestions": suggestions,
    }

    if debug_info:
        response["debug"] = debug_info

    return jsonify(response)


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

    One-click UX: clicking a suggestion creates Bond + runs it + produces M output.
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    input_item_ids = data.get("input_item_ids", [])
    prompt_text = data.get("prompt_text", "")
    intent_type = data.get("intent_type")
    recipe_id = data.get("recipe_id")
    output_type = data.get("output_type", "M")

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
        result = {
            "status": "executed",
            "output_item": output_item,
            "bond": bond,
            "credits": cli._credits_balance,
        }
        # Sprint G2: Include generation warning if any
        warning = get_last_generation_warning()
        if warning:
            result["generation_warning"] = warning
        return jsonify(result)
    else:
        bond = cli.store.get_bond(bond_id)
        return jsonify({
            "status": "failed",
            "bond": bond,
            "credits": cli._credits_balance,
        })


@app.route("/api/credits")
def api_credits():
    """Get credits balance."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"balance": 0})

    cli._load_context()
    return jsonify({"balance": cli._credits_balance})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset the store for a fresh session (ontology fix for New Session)."""
    import shutil
    from pathlib import Path

    # Reset the singleton
    reset_store()

    # Delete data files for true reset
    data_path = DATA_DIR or Path(__file__).parent.parent / "data"
    if Path(data_path).exists():
        shutil.rmtree(data_path)

    return jsonify({"status": "reset"})


@app.route("/api/ledger")
def api_ledger():
    """Get ledger data."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"})

    cli._load_context()
    cli.logger.ledger_opened(cli._network_id, cli._episode_id)

    items = cli.store.load_items({"episode_id": cli._episode_id})
    bonds = cli.store.load_bonds({"episode_id": cli._episode_id})
    events = cli.store.load_events(episode_id=cli._episode_id)

    return jsonify({
        "items": items,
        "bonds": bonds,
        "events": events,
        "credits": cli._credits_balance,
    })


if __name__ == "__main__":
    import socket

    PORT = int(os.environ.get("PORT", 5002))

    # Only check port on initial run, not on reloader restart
    # WERKZEUG_RUN_MAIN is set when Flask reloader spawns child process
    is_reloader_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if not is_reloader_process:
        # Check if port is in use before starting
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        if is_port_in_use(PORT):
            print(f"\nError: Port {PORT} is already in use.")
            print(f"\nTo fix this, run:")
            print(f"  lsof -ti:{PORT} | xargs kill -9")
            print(f"\nOr use a different port:")
            print(f"  PORT=5003 python3 prototype/ui_v2/app.py\n")
            sys.exit(1)

        print("=" * 60)
        print("Field-Kit v2 UI (Wrapper-styled)")
        print("=" * 60)
        print(f"Data directory: {DATA_DIR or 'prototype/data/'}")
        print(f"Starting server at http://localhost:{PORT}")
        print("=" * 60)

    app.run(host="localhost", port=PORT, debug=True)
