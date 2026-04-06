#!/usr/bin/env python3
"""Generate a JavaScript snippet to add items to Woolworths cart.

Usage: python3 cart.py '<json_items>'

Input: JSON array of objects with "stockcode" and "quantity" fields, e.g.:
  [{"stockcode": 661766, "quantity": 1}, {"stockcode": 224763, "quantity": 2}]

Output: A JavaScript snippet to paste into the browser console on
        woolworths.com.au while logged in.
"""

import json
import sys


def generate_cart_js(items: list) -> str:
    """Generate the add-to-cart JavaScript snippet."""
    api_items = []
    for item in items:
        sc = item.get("stockcode")
        qty = item.get("quantity", 1)
        if not sc:
            raise ValueError(f"Missing stockcode in item: {item}")
        api_items.append(
            {
                "stockcode": int(sc),
                "quantity": int(qty),
                "source": "SearchResults",
                "diagnostics": "0",
                "searchTerm": None,
                "evaluateRewardPoints": False,
                "offerId": None,
                "profileId": None,
                "priceLevel": None,
            }
        )

    # Batch into groups of 10 to avoid overwhelming the API
    batches = [api_items[i : i + 10] for i in range(0, len(api_items), 10)]
    item_summary = ", ".join(f"{it['stockcode']} x{it['quantity']}" for it in api_items)

    js = f"""// Woolies Cart - Adding {len(api_items)} item(s): {item_summary}
(async () => {{
  const batches = {json.dumps([{"items": b} for b in batches])};
  let added = 0, failed = 0;
  for (const batch of batches) {{
    try {{
      const res = await fetch('/api/v3/ui/trolley/update', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': '*/*' }},
        body: JSON.stringify(batch),
        credentials: 'same-origin'
      }});
      if (res.ok) {{
        const data = await res.json();
        added += batch.items.length;
        console.log(`Added ${{batch.items.length}} item(s) to cart`, data);
      }} else {{
        failed += batch.items.length;
        console.error(`Failed (${{res.status}})`, await res.text());
      }}
    }} catch (e) {{
      failed += batch.items.length;
      console.error('Error adding to cart:', e);
    }}
  }}
  const msg = `Done! ${{added}} item(s) added to cart` + (failed ? `, ${{failed}} failed` : '');
  console.log(msg);
  alert(msg);
  location.reload();
}})();"""

    return js


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python3 cart.py '<json_array_of_stockcode_quantity>'",
            file=sys.stderr,
        )
        sys.exit(1)

    raw = sys.argv[1]
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list) or len(items) == 0:
        print("Error: Input must be a non-empty JSON array", file=sys.stderr)
        sys.exit(1)

    try:
        js = generate_cart_js(items)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(js)


if __name__ == "__main__":
    main()
