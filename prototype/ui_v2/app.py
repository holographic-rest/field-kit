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
from fieldkit import get_store, reset_store, ItemHandle
from fieldkit.spin_recipes import generate_suggestions_for_item, generate_proposals_for_holologue
from fieldkit.generation import get_generation_mode, get_last_generation_warning
from fieldkit.hololoop_engine import generate_hololoop_options, options_to_bond_create_params
from fieldkit.hololink_pipeline import generate_hololink_options, get_handles_for_item
from fieldkit.retrieval import find_related_items, find_best_target_for_hololoop
from fieldkit.handles import extract_handles, choose_diverse_handles
from fieldkit.store_jsonl import dict_to_item

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


# === Queue Lattice: Hololoop API Routes ===

@app.route("/api/hololoop/options")
def api_hololoop_options():
    """Get 4 hololoop options for connecting two items.

    Query params:
    - item_a: ID of first Queue Item
    - item_b: ID of second Queue Item
    - debug: Include debug info (optional)
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item_a_id = request.args.get("item_a")
    item_b_id = request.args.get("item_b")
    debug_mode = request.args.get("debug", "").lower() == "true"

    if not item_a_id or not item_b_id:
        return jsonify({"error": "missing_item_ids"}), 400

    item_a = cli.store.get_item(item_a_id)
    item_b = cli.store.get_item(item_b_id)

    if not item_a:
        return jsonify({"error": "item_a_not_found"}), 404
    if not item_b:
        return jsonify({"error": "item_b_not_found"}), 404

    # Generate 4 hololoop options
    result = generate_hololoop_options(item_a, item_b, return_debug=debug_mode)

    # Log event
    cli._load_context()
    cli.logger.bond_suggestions_presented(
        cli._network_id, cli._episode_id,
        item_id=item_a_id,
        suggestions=[
            {
                "option_index": opt["option_index"],
                "relation_type": opt["relation_type"],
                "link_text_forward": opt["link_text_forward"],
                "link_text_return": opt["link_text_return"],
            }
            for opt in result["options"]
        ],
    )

    return jsonify(result)


@app.route("/api/hololoop/create", methods=["POST"])
def api_hololoop_create():
    """Create a hololoop bond from a selected option.

    Request body:
    - item_a_id: ID of first Queue Item
    - item_b_id: ID of second Queue Item
    - option_index: Selected option (1-4)
    - link_text_forward: A→B sentence (optional, uses generated if not provided)
    - link_text_return: B→A sentence (optional, uses generated if not provided)
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    item_a_id = data.get("item_a_id")
    item_b_id = data.get("item_b_id")
    option_index = data.get("option_index", 1)

    if not item_a_id or not item_b_id:
        return jsonify({"error": "missing_item_ids"}), 400

    item_a = cli.store.get_item(item_a_id)
    item_b = cli.store.get_item(item_b_id)

    if not item_a:
        return jsonify({"error": "item_a_not_found"}), 404
    if not item_b:
        return jsonify({"error": "item_b_not_found"}), 404

    # Allow custom link text or use generated
    link_text_forward = data.get("link_text_forward")
    link_text_return = data.get("link_text_return")

    if not link_text_forward or not link_text_return:
        # Generate options and get the selected one
        result = generate_hololoop_options(item_a, item_b)
        options = result["options"]

        if option_index < 1 or option_index > len(options):
            return jsonify({"error": "invalid_option_index"}), 400

        selected = options[option_index - 1]
        link_text_forward = link_text_forward or selected["link_text_forward"]
        link_text_return = link_text_return or selected["link_text_return"]
        relation_type = selected["relation_type"]
    else:
        relation_type = data.get("relation_type", "extends")

    # Create hololoop bond using CLI
    bond_id = cli.cmd_hololoop_create(item_a_id, item_b_id, option_index)

    bond = cli.store.get_bond(bond_id)

    return jsonify({
        "status": "created",
        "bond": bond,
        "hololoop": {
            "item_a_id": item_a_id,
            "item_b_id": item_b_id,
            "link_text_forward": link_text_forward,
            "link_text_return": link_text_return,
            "relation_type": relation_type,
        },
    })


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


# === Queue Lattice: Handles API ===

@app.route("/api/items/<item_id>/handles")
def api_get_handles(item_id):
    """Get handles for an item."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item = cli.store.get_item(item_id)
    if not item:
        return jsonify({"error": "item_not_found"}), 404

    handles = item.get("handles", [])

    # If no stored handles, extract from content
    if not handles:
        raw = extract_handles(item.get("body") or "", item.get("title"))
        selected = choose_diverse_handles(raw, k=5)
        handles = [{"quote": h["quote"], "kind": h["kind"], "starred": False} for h in selected]

    return jsonify({
        "item_id": item_id,
        "handles": handles,
    })


@app.route("/api/items/<item_id>/handles", methods=["PUT"])
def api_update_handles(item_id):
    """Update handles for an item (star/unstar, edit, add, remove)."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item = cli.store.get_item(item_id)
    if not item:
        return jsonify({"error": "item_not_found"}), 404

    data = request.json or {}
    new_handles = data.get("handles", [])

    # Validate handles (3-7 per item)
    if len(new_handles) < 1 or len(new_handles) > 10:
        return jsonify({"error": "invalid_handle_count"}), 400

    # Convert to ItemHandle objects and update item
    from fieldkit.schemas import now_iso
    item["handles"] = new_handles
    item["updated_at"] = now_iso()

    # Save updated item
    item_obj = dict_to_item(item)
    cli.store.upsert_item(item_obj)

    return jsonify({
        "status": "updated",
        "item_id": item_id,
        "handles": new_handles,
    })


# === Queue Lattice: Related Items API ===

@app.route("/api/items/<item_id>/related")
def api_related_items(item_id):
    """Get items related to the given item using local similarity.

    Query params:
    - k: Number of related items to return (default 5)
    - method: Similarity method (jaccard|bm25|hybrid, default hybrid)
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    item = cli.store.get_item(item_id)
    if not item:
        return jsonify({"error": "item_not_found"}), 404

    cli._load_context()

    # Get all Q items in episode
    all_items = cli.store.load_items({"episode_id": cli._episode_id})
    q_items = [i for i in all_items if i["type"] == "Q"]

    k = int(request.args.get("k", 5))
    method = request.args.get("method", "hybrid")

    related = find_related_items(item, q_items, k=k, method=method)

    return jsonify({
        "item_id": item_id,
        "related": related,
        "method": method,
    })


# === Queue Lattice: Draft Hololoop API ===

@app.route("/api/draft-hololoop", methods=["POST"])
def api_create_draft_hololoop():
    """Auto-create a draft hololoop between two items.

    Request body:
    - source_item_id: The newly created item (or active item)
    - target_item_id: Optional target item (if not provided, finds best match)

    Returns the draft hololoop with one generated hololink option.
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    data = request.json or {}
    source_item_id = data.get("source_item_id")
    target_item_id = data.get("target_item_id")

    if not source_item_id:
        return jsonify({"error": "missing_source_item_id"}), 400

    source_item = cli.store.get_item(source_item_id)
    if not source_item:
        return jsonify({"error": "source_item_not_found"}), 404

    cli._load_context()

    # Get target item (provided or find best match)
    if target_item_id:
        target_item = cli.store.get_item(target_item_id)
        if not target_item:
            return jsonify({"error": "target_item_not_found"}), 404
    else:
        # Find best target using retrieval
        all_items = cli.store.load_items({"episode_id": cli._episode_id})
        q_items = [i for i in all_items if i["type"] == "Q" and i["id"] != source_item_id]
        target_item = find_best_target_for_hololoop(source_item, q_items)
        if not target_item:
            return jsonify({"error": "no_target_available"}), 400

    # Generate hololink options using the new pipeline
    result = generate_hololink_options(source_item, target_item, return_debug=True)
    options = result.get("options", [])

    if not options:
        return jsonify({"error": "no_hololink_options_generated"}), 500

    # Use first option as the draft
    selected = options[0]

    # Create draft hololoop bond
    bond_id = cli.cmd_hololoop_create(
        source_item["id"],
        target_item["id"],
        option_index=1,
    )

    bond = cli.store.get_bond(bond_id)

    return jsonify({
        "status": "draft_created",
        "bond": bond,
        "source_item": source_item,
        "target_item": target_item,
        "hololink": {
            "link_text_forward": selected["link_text_forward"],
            "link_text_return": selected["link_text_return"],
            "handle_a_used": selected.get("handle_a_used"),
            "handle_b_used": selected.get("handle_b_used"),
        },
        "all_options": options,  # For "regenerate" functionality
    })


@app.route("/api/draft-hololoop/<bond_id>/regenerate", methods=["POST"])
def api_regenerate_draft_hololoop(bond_id):
    """Regenerate hololink options for an existing draft hololoop."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    bond = cli.store.get_bond(bond_id)
    if not bond:
        return jsonify({"error": "bond_not_found"}), 404

    if bond.get("bond_kind") != "hololoop":
        return jsonify({"error": "not_a_hololoop"}), 400

    if bond.get("status") != "draft":
        return jsonify({"error": "bond_not_draft"}), 400

    input_item_ids = bond.get("input_item_ids", [])
    if len(input_item_ids) != 2:
        return jsonify({"error": "invalid_input_items"}), 400

    source_item = cli.store.get_item(input_item_ids[0])
    target_item = cli.store.get_item(input_item_ids[1])

    if not source_item or not target_item:
        return jsonify({"error": "items_not_found"}), 404

    # Generate new options
    result = generate_hololink_options(source_item, target_item, return_debug=True)

    return jsonify({
        "bond_id": bond_id,
        "options": result.get("options", []),
        "source": result.get("source"),
        "debug": result.get("debug"),
    })


@app.route("/api/draft-hololoop/<bond_id>/accept", methods=["POST"])
def api_accept_draft_hololoop(bond_id):
    """Accept a draft hololoop (add to curated_bond_ids)."""
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    bond = cli.store.get_bond(bond_id)
    if not bond:
        return jsonify({"error": "bond_not_found"}), 404

    if bond.get("bond_kind") != "hololoop":
        return jsonify({"error": "not_a_hololoop"}), 400

    cli._load_context()

    # Add to curated bonds (acceptance action)
    cli.cmd_curate_bond_add(bond_id)

    return jsonify({
        "status": "accepted",
        "bond_id": bond_id,
    })


@app.route("/api/draft-hololoop/<bond_id>/update", methods=["PUT"])
def api_update_draft_hololoop(bond_id):
    """Update a draft hololoop with new link text or target.

    Request body:
    - link_text_forward: Optional new A→B text
    - link_text_return: Optional new B→A text
    - target_item_id: Optional new target item
    """
    cli = get_cli()
    if not cli.store.is_initialized():
        return jsonify({"error": "not_initialized"}), 400

    bond = cli.store.get_bond(bond_id)
    if not bond:
        return jsonify({"error": "bond_not_found"}), 404

    if bond.get("bond_kind") != "hololoop":
        return jsonify({"error": "not_a_hololoop"}), 400

    if bond.get("status") != "draft":
        return jsonify({"error": "bond_not_draft"}), 400

    data = request.json or {}

    # Update fields
    from fieldkit.schemas import now_iso
    from fieldkit.store_jsonl import dict_to_bond

    if "link_text_forward" in data:
        bond["link_text_forward"] = data["link_text_forward"]
    if "link_text_return" in data:
        bond["link_text_return"] = data["link_text_return"]
    if "target_item_id" in data:
        new_target = cli.store.get_item(data["target_item_id"])
        if not new_target:
            return jsonify({"error": "target_item_not_found"}), 404
        bond["input_item_ids"] = [bond["input_item_ids"][0], data["target_item_id"]]

    bond["updated_at"] = now_iso()

    # Save updated bond
    bond_obj = dict_to_bond(bond)
    cli.store.upsert_bond(bond_obj)

    return jsonify({
        "status": "updated",
        "bond": bond,
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
