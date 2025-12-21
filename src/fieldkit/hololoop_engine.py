"""
Field-Kit v0.1 Hololoop Engine (Queue Lattice PASS 2)

Generates 4 hololoop options for connecting two Queue Items.

A hololoop is a two-way navigational bond between items A and B:
- link_text_forward: A→B sentence referencing handles from BOTH A and B
- link_text_return: B→A sentence referencing handles from BOTH B and A

Key requirements (PASS 2):
- Each link sentence must quote handles from BOTH items (not just one)
- 4 options with varied sentence structures
- Content-derived, not generic templates
- No relation type labels shown to user
"""

import hashlib
import os
import json
from typing import List, Dict, Any, Optional, Tuple

from .handles import extract_handles, choose_diverse_handles


# === Bidirectional sentence templates (PASS 2: both handles in each sentence) ===
# Each template uses {handle_a} and {handle_b} - both must appear
BIDIRECTIONAL_TEMPLATES = [
    # Template set 1: extends/develops
    {
        "id": "extends",
        "forward": 'How does "{handle_a}" lead into "{handle_b}"?',
        "return": 'How does "{handle_b}" build on "{handle_a}"?',
    },
    # Template set 2: supports/grounds
    {
        "id": "supports",
        "forward": '"{handle_a}" provides a foundation for understanding "{handle_b}"',
        "return": '"{handle_b}" draws context from "{handle_a}"',
    },
    # Template set 3: contrasts/differs
    {
        "id": "contrasts",
        "forward": 'Compare "{handle_a}" with "{handle_b}"',
        "return": 'How does "{handle_b}" differ from "{handle_a}"?',
    },
    # Template set 4: elaborates/unpacks
    {
        "id": "elaborates",
        "forward": '"{handle_a}" expands into "{handle_b}"',
        "return": '"{handle_b}" unpacks the idea in "{handle_a}"',
    },
]


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _try_openai_generation(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Try to generate hololoop options via OpenAI API.

    Returns: (options or None, warning_message)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, ""

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    warning = ""

    try:
        import openai

        # Prepare handle quotes
        quotes_a = [h["quote"] for h in handles_a[:6]]
        quotes_b = [h["quote"] for h in handles_b[:6]]

        system_prompt = """You generate exactly 4 hololoop options connecting two items.

A hololoop has two hololinks:
- link_text_forward: How A relates to B (must quote handles from BOTH A and B)
- link_text_return: How B relates to A (must quote handles from BOTH B and A)

CRITICAL RULES:
1. Each link_text MUST contain quotes from BOTH items (one A handle AND one B handle)
2. Put handles in double quotes within the sentence
3. Keep sentences 10-25 words
4. Make sentences specific to the content, not generic
5. Each option should use DIFFERENT handles

Example format:
- forward: 'How does "A's concept" connect to "B's idea"?'
- return: '"B's idea" builds on "A's concept"'

Output JSON:
{
  "options": [
    {
      "option_index": 1,
      "relation_type": "extends|supports|contrasts|elaborates",
      "link_text_forward": "sentence with BOTH A handle and B handle",
      "link_text_return": "sentence with BOTH B handle and A handle",
      "handle_a_used": "the handle from A",
      "handle_b_used": "the handle from B"
    },
    ...
  ]
}"""

        # Truncate bodies
        body_a = (item_a.get("body") or "")[:800]
        body_b = (item_b.get("body") or "")[:800]

        user_prompt = f"""Item A:
Title: {item_a.get("title", "")}
Body: {body_a}

Handles from A (use in BOTH link_text_forward AND link_text_return):
{json.dumps(quotes_a, indent=2)}

Item B:
Title: {item_b.get("title", "")}
Body: {body_b}

Handles from B (use in BOTH link_text_forward AND link_text_return):
{json.dumps(quotes_b, indent=2)}

Generate 4 hololoop options. EACH sentence must contain one A handle AND one B handle."""

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
        except openai.BadRequestError as e:
            if "model" in str(e).lower():
                warning = f"Invalid model '{model}', falling back to gpt-4o-mini"
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
            else:
                raise

        content = response.choices[0].message.content
        data = json.loads(content)

        options = data.get("options", [])
        if not options and isinstance(data, list):
            options = data

        if len(options) < 4:
            return None, "OpenAI returned fewer than 4 options"

        # Normalize to our format
        results = []
        for i, opt in enumerate(options[:4], 1):
            results.append({
                "option_index": i,
                "relation_type": opt.get("relation_type", "extends"),
                "link_text_forward": opt.get("link_text_forward", ""),
                "link_text_return": opt.get("link_text_return", ""),
            })

        return results, warning

    except ImportError:
        return None, "openai package not installed"
    except Exception as e:
        print(f"[hololoop_engine] OpenAI generation failed: {e}")
        return None, str(e)


def _deterministic_fallback(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate hololoop options deterministically.

    PASS 2: Each hololink sentence must reference handles from BOTH items.
    Uses content-based seed to select varied templates and handles.
    """
    # Content hash for deterministic but varied selection
    content = (item_a.get("title", "") + item_a.get("body", "") +
               item_b.get("title", "") + item_b.get("body", ""))
    seed = _hash_content(content)

    # Ensure we have enough handles (pad with title if needed)
    while len(handles_a) < 4:
        title = item_a.get("title", "this content")[:50]
        handles_a.append({"quote": title, "kind": "heading", "score": 0.5})
    while len(handles_b) < 4:
        title = item_b.get("title", "this content")[:50]
        handles_b.append({"quote": title, "kind": "heading", "score": 0.5})

    options = []

    for i, template_set in enumerate(BIDIRECTIONAL_TEMPLATES):
        # Select different handles for each option
        # Use seed + offset to ensure variety
        a_idx = (seed + i) % len(handles_a)
        b_idx = (seed + i + 2) % len(handles_b)

        handle_a = handles_a[a_idx]["quote"]
        handle_b = handles_b[b_idx]["quote"]

        # Format templates with BOTH handles in each sentence
        link_text_forward = template_set["forward"].format(
            handle_a=handle_a,
            handle_b=handle_b,
        )
        link_text_return = template_set["return"].format(
            handle_a=handle_a,
            handle_b=handle_b,
        )

        options.append({
            "option_index": i + 1,
            "relation_type": template_set["id"],
            "link_text_forward": link_text_forward,
            "link_text_return": link_text_return,
            # PASS 2: Track which handles were used for validation
            "handle_a_used": handle_a,
            "handle_b_used": handle_b,
        })

    return options


def generate_hololoop_options(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Generate 4 hololoop options for connecting items A and B.

    Args:
        item_a: First Queue Item dict (with id, title, body)
        item_b: Second Queue Item dict (with id, title, body)
        return_debug: Include debug info in response

    Returns:
        Dict with:
        - options: List of 4 hololoop option dicts
        - source: "llm" | "fallback"
        - warning: Optional warning message
        - debug: Optional debug info (if return_debug=True)
    """
    # Extract handles from both items
    handles_a = extract_handles(
        item_a.get("body") or "",
        item_a.get("title")
    )
    handles_b = extract_handles(
        item_b.get("body") or "",
        item_b.get("title")
    )

    # Select diverse handles
    selected_a = choose_diverse_handles(handles_a, k=6)
    selected_b = choose_diverse_handles(handles_b, k=6)

    # Try OpenAI generation
    options, warning = _try_openai_generation(item_a, item_b, selected_a, selected_b)

    source = "llm" if options else "fallback"

    if not options:
        options = _deterministic_fallback(item_a, item_b, selected_a, selected_b)

    result = {
        "options": options,
        "source": source,
        "warning": warning or None,
        "item_a_id": item_a.get("id"),
        "item_b_id": item_b.get("id"),
    }

    if return_debug:
        result["debug"] = {
            "handles_a": [h["quote"] for h in selected_a],
            "handles_b": [h["quote"] for h in selected_b],
            "all_handles_a_count": len(handles_a),
            "all_handles_b_count": len(handles_b),
        }

    return result


def options_to_bond_create_params(
    option: Dict[str, Any],
    item_a_id: str,
    item_b_id: str,
) -> Dict[str, Any]:
    """
    Convert a hololoop option to parameters for creating a Bond.

    Returns dict suitable for Bond creation with:
    - input_item_ids: [item_a_id, item_b_id]
    - prompt_text: Combined description
    - bond_kind: "hololoop"
    - link_text_forward: A→B sentence
    - link_text_return: B→A sentence
    """
    return {
        "input_item_ids": [item_a_id, item_b_id],
        "prompt_text": f"Hololoop ({option['relation_type']}): {item_a_id} ↔ {item_b_id}",
        "intent_type": option.get("relation_type", "extends"),
        "bond_kind": "hololoop",
        "link_text_forward": option["link_text_forward"],
        "link_text_return": option["link_text_return"],
    }
