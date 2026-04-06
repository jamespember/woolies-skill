#!/usr/bin/env python3
"""Generate an HTML shopping list and open it in the browser.

Usage: python3 shopping_list.py '<json>'

Input JSON schema:
{
  "title": "Shopping List",
  "recipes": ["Beef Tacos", "Fried Rice"],
  "items": [
    {
      "item": "beef mince",
      "product": "Woolworths Beef Mince 500g",
      "stockcode": 661766,
      "price": 7.00,
      "quantity": 1,
      "is_on_special": false,
      "savings": null,
      "special_label": null,
      "used_in": ["Beef Tacos"]
    }
  ],
  "total": 45.50,
  "total_savings": 5.00
}

Output: Writes /tmp/woolies-shopping-list.html and opens it in the browser.
        Prints the file path to stdout as JSON.
"""

import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime


OUTPUT_FILE = "/tmp/woolies-shopping-list.html"


def generate_cart_js(items: list) -> str:
    """Build the add-to-cart JS snippet from items with stockcodes."""
    cart_items = []
    for item in items:
        sc = item.get("stockcode")
        qty = item.get("quantity", 1)
        if sc:
            cart_items.append({"stockcode": int(sc), "quantity": int(qty)})

    if not cart_items:
        return ""

    api_items = []
    for ci in cart_items:
        api_items.append(
            {
                "stockcode": ci["stockcode"],
                "quantity": ci["quantity"],
                "source": "SearchResults",
                "diagnostics": "0",
                "searchTerm": None,
                "evaluateRewardPoints": False,
                "offerId": None,
                "profileId": None,
                "priceLevel": None,
            }
        )
    batches = [api_items[i : i + 10] for i in range(0, len(api_items), 10)]
    item_summary = ", ".join(
        f"{ci['stockcode']} x{ci['quantity']}" for ci in cart_items
    )

    return f"""// Woolies Cart - Adding {len(api_items)} item(s): {item_summary}
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


def generate_html(data: dict) -> str:
    """Generate the full HTML shopping list page."""
    items = data.get("items", [])

    # Auto-calculate totals from items to avoid LLM arithmetic errors
    calculated_total = sum(
        item.get("price", 0) * item.get("quantity", 1) for item in items
    )
    calculated_savings = sum(
        item.get("savings", 0) * item.get("quantity", 1)
        for item in items
        if item.get("savings")
    )

    # Use provided values only if they match calculated; otherwise use calculated
    provided_total = data.get("total")
    provided_savings = data.get("total_savings")

    if provided_total and abs(provided_total - calculated_total) > 0.01:
        print(
            f"Warning: Correcting total from ${provided_total:.2f} to ${calculated_total:.2f}",
            file=sys.stderr,
        )

    total = calculated_total
    total_savings = calculated_savings if calculated_savings > 0 else provided_savings

    title = html.escape(data.get("title", "Shopping List"))
    recipes = data.get("recipes", [])
    generated = datetime.now().strftime("%a %d %b %Y, %I:%M %p")

    specials_count = sum(1 for i in items if i.get("is_on_special"))

    # Build item rows
    item_rows = []
    for idx, item in enumerate(items):
        name = html.escape(item.get("item", ""))
        product = html.escape(item.get("product", ""))
        stockcode = item.get("stockcode")
        price = item.get("price")
        qty = item.get("quantity", 1)
        on_special = item.get("is_on_special", False)
        savings = item.get("savings")
        special_label = item.get("special_label")
        used_in = item.get("used_in", [])

        price_str = f"${price:.2f}" if price is not None else ""
        line_total = f"${price * qty:.2f}" if price is not None and qty else price_str

        badge = ""
        if on_special:
            if special_label:
                label_text = html.escape(special_label)
            elif savings:
                label_text = f"Save ${savings:.2f}"
            else:
                label_text = "On Special"
            badge = f'<span class="badge special">{label_text}</span>'

        recipes_tag = ""
        if used_in:
            tags = "".join(
                f'<span class="recipe-tag">{html.escape(r)}</span>' for r in used_in
            )
            recipes_tag = f'<div class="used-in">{tags}</div>'

        qty_str = f' <span class="qty">&times;{qty}</span>' if qty and qty > 1 else ""

        product_link = (
            f'<a class="product-link" href="https://www.woolworths.com.au/shop/productdetails/{stockcode}" target="_blank">{product}</a>'
            if stockcode
            else product
        )

        item_rows.append(f"""
      <label class="item" data-idx="{idx}">
        <input type="checkbox" />
        <div class="item-body">
          <div class="item-main">
            <span class="item-name">{name}{qty_str}</span>
            <span class="item-price">{line_total}</span>
          </div>
          <div class="item-detail">{product_link} {badge}</div>
          {recipes_tag}
        </div>
      </label>""")

    recipes_section = ""
    if recipes:
        recipe_pills = " ".join(
            f'<span class="recipe-pill">{html.escape(r)}</span>' for r in recipes
        )
        recipes_section = f'<div class="recipes-bar">{recipe_pills}</div>'

    total_section = ""
    if total is not None:
        savings_line = ""
        if total_savings:
            savings_line = f'<div class="savings-line">Saving ${total_savings:.2f} from specials</div>'
        total_section = f"""
    <div class="total-bar">
      <div class="total-line">
        <span>Estimated Total</span>
        <span class="total-price">${total:.2f}</span>
      </div>
      {savings_line}
    </div>"""

    # Cart section
    cart_js = generate_cart_js(items)
    cart_section = ""
    if cart_js:
        cart_js_escaped = html.escape(cart_js)
        cart_section = f"""
    <div class="cart-panel" id="cartPanel">
      <button class="cart-toggle" id="cartToggle" title="Add to Cart script">&#128722; Add to Cart Script</button>
      <div class="cart-body" id="cartBody">
        <p class="cart-instructions">Copy this script, go to <a href="https://www.woolworths.com.au" target="_blank">woolworths.com.au</a> (logged in), open DevTools console (F12), and paste it.</p>
        <pre class="cart-code" id="cartCode">{cart_js_escaped}</pre>
        <div class="cart-buttons">
          <button class="cart-select-all" id="cartSelectAll">Select All</button>
          <button class="cart-copy" id="cartCopy">Copy to Clipboard</button>
        </div>
      </div>
    </div>"""

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>
  :root {{
    --green: #125a30;
    --green-light: #e8f5e9;
    --special-bg: #fff3e0;
    --special-text: #e65100;
    --grey-light: #f5f5f5;
    --grey-border: #e0e0e0;
    --text: #212121;
    --text-muted: #757575;
    --radius: 10px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--grey-light);
    color: var(--text);
    min-height: 100dvh;
    padding-bottom: 120px;
  }}
  header {{
    background: var(--green);
    color: #fff;
    padding: 20px 16px 16px;
    position: sticky;
    top: 0;
    z-index: 10;
  }}
  header h1 {{
    font-size: 1.3rem;
    font-weight: 700;
  }}
  header .meta {{
    font-size: 0.8rem;
    opacity: 0.8;
    margin-top: 4px;
  }}
  .counter {{
    display: inline-block;
    background: rgba(255,255,255,0.2);
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.8rem;
    margin-left: 8px;
  }}
  .recipes-bar {{
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .recipe-pill {{
    background: var(--green-light);
    color: var(--green);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
  }}
  .items {{
    padding: 0 12px;
  }}
  .item {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: #fff;
    border-radius: var(--radius);
    padding: 14px 14px;
    margin-bottom: 8px;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    border: 1px solid var(--grey-border);
    transition: opacity 0.2s;
  }}
  .item:has(input:checked) {{
    opacity: 0.45;
  }}
  .item:has(input:checked) .item-name {{
    text-decoration: line-through;
  }}
  .item input[type="checkbox"] {{
    width: 22px;
    height: 22px;
    margin-top: 2px;
    flex-shrink: 0;
    accent-color: var(--green);
    cursor: pointer;
  }}
  .item-body {{
    flex: 1;
    min-width: 0;
  }}
  .item-main {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }}
  .item-name {{
    font-weight: 600;
    font-size: 1rem;
  }}
  .qty {{
    font-weight: 400;
    color: var(--text-muted);
  }}
  .item-price {{
    font-weight: 700;
    white-space: nowrap;
    font-size: 1rem;
  }}
  .item-detail {{
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 3px;
  }}
  .product-link {{
    color: var(--green);
    text-decoration: none;
  }}
  .product-link:hover {{
    text-decoration: underline;
  }}
  .badge {{
    display: inline-block;
    padding: 1px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    vertical-align: middle;
    margin-left: 4px;
  }}
  .badge.special {{
    background: var(--special-bg);
    color: var(--special-text);
  }}
  .used-in {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
  }}
  .recipe-tag {{
    font-size: 0.7rem;
    background: var(--grey-light);
    color: var(--text-muted);
    padding: 2px 8px;
    border-radius: 8px;
  }}
  .total-bar {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #fff;
    border-top: 2px solid var(--green);
    padding: 16px;
    z-index: 10;
  }}
  .total-line {{
    display: flex;
    justify-content: space-between;
    font-size: 1.1rem;
    font-weight: 700;
  }}
  .total-price {{
    color: var(--green);
  }}
  .savings-line {{
    color: var(--special-text);
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 4px;
    text-align: right;
  }}
  .progress-bar {{
    height: 3px;
    background: var(--grey-border);
    margin-top: 10px;
    border-radius: 2px;
    overflow: hidden;
  }}
  .progress-fill {{
    height: 100%;
    background: var(--green);
    width: 0%;
    transition: width 0.3s;
  }}
  /* Cart panel */
  .cart-panel {{
    padding: 0 12px;
    margin-top: 16px;
    margin-bottom: 16px;
  }}
  .cart-toggle {{
    width: 100%;
    padding: 14px 16px;
    background: var(--green);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    -webkit-tap-highlight-color: transparent;
  }}
  .cart-toggle:hover {{
    opacity: 0.9;
  }}
  .cart-body {{
    display: none;
    background: #fff;
    border: 1px solid var(--grey-border);
    border-radius: 0 0 var(--radius) var(--radius);
    margin-top: -6px;
    padding: 14px;
  }}
  .cart-body.open {{
    display: block;
  }}
  .cart-instructions {{
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-bottom: 10px;
    line-height: 1.5;
  }}
  .cart-instructions a {{
    color: var(--green);
    text-decoration: none;
    font-weight: 600;
  }}
  .cart-code {{
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 8px;
    font-size: 0.72rem;
    line-height: 1.4;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
  }}
  .cart-buttons {{
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }}
  .cart-select-all {{
    flex: 1;
    padding: 12px;
    background: #fff;
    color: var(--green);
    border: 2px solid var(--green);
    border-radius: var(--radius);
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }}
  .cart-select-all:hover {{
    background: var(--green-light);
  }}
  .cart-copy {{
    flex: 2;
    padding: 12px;
    background: var(--green);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }}
  .cart-copy:hover {{
    opacity: 0.9;
  }}
  .cart-copy.copied {{
    background: #2e7d32;
  }}
</style>
</head>
<body>

<header>
  <h1>{title}<span class="counter" id="counter">0/{len(items)}</span></h1>
  <div class="meta">{generated}{f" &middot; {specials_count} special{'s' if specials_count != 1 else ''}" if specials_count else ""}</div>
</header>

{recipes_section}

<div class="items">
  {"".join(item_rows)}
</div>

{cart_section}

{total_section}

<script>
(function() {{
  const total = {len(items)};
  const counter = document.getElementById("counter");
  const boxes = document.querySelectorAll('.item input[type="checkbox"]');
  const KEY = "woolies-checked";

  // Restore state
  try {{
    const saved = JSON.parse(localStorage.getItem(KEY) || "[]");
    saved.forEach(idx => {{
      if (boxes[idx]) boxes[idx].checked = true;
    }});
  }} catch(e) {{}}

  function update() {{
    const checked = [...boxes].filter(b => b.checked).length;
    counter.textContent = checked + "/" + total;
    // Save state
    const idxs = [...boxes].map((b,i) => b.checked ? i : -1).filter(i => i >= 0);
    localStorage.setItem(KEY, JSON.stringify(idxs));
  }}

  boxes.forEach(b => b.addEventListener("change", update));
  // Prevent product links from toggling the checkbox
  document.querySelectorAll(".product-link").forEach(a => {{
    a.addEventListener("click", e => e.stopPropagation());
  }});
  update();
}})();

// Cart panel toggle + copy
(function() {{
  const toggle = document.getElementById("cartToggle");
  const body = document.getElementById("cartBody");
  const copyBtn = document.getElementById("cartCopy");
  const selectBtn = document.getElementById("cartSelectAll");
  const code = document.getElementById("cartCode");
  if (!toggle || !body) return;

  toggle.addEventListener("click", function() {{
    body.classList.toggle("open");
  }});

  selectBtn.addEventListener("click", function() {{
    const range = document.createRange();
    range.selectNodeContents(code);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }});

  copyBtn.addEventListener("click", function() {{
    const text = code.textContent;
    navigator.clipboard.writeText(text).then(function() {{
      copyBtn.textContent = "Copied!";
      copyBtn.classList.add("copied");
      setTimeout(function() {{
        copyBtn.textContent = "Copy to Clipboard";
        copyBtn.classList.remove("copied");
      }}, 2000);
    }}).catch(function() {{
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      copyBtn.textContent = "Copied!";
      copyBtn.classList.add("copied");
      setTimeout(function() {{
        copyBtn.textContent = "Copy to Clipboard";
        copyBtn.classList.remove("copied");
      }}, 2000);
    }});
  }});
}})();
</script>

</body>
</html>"""

    return page_html


def open_in_browser(path: str):
    """Try to open the file in the default browser."""
    if shutil.which("xdg-open"):
        subprocess.Popen(
            ["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    elif shutil.which("open"):
        subprocess.Popen(
            ["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 shopping_list.py '<json>'", file=sys.stderr)
        sys.exit(1)

    raw = sys.argv[1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    items = data.get("items", [])
    if not items:
        print(json.dumps({"error": "No items in shopping list"}), file=sys.stderr)
        sys.exit(1)

    page_html = generate_html(data)

    with open(OUTPUT_FILE, "w") as f:
        f.write(page_html)

    print(json.dumps({"status": "ok", "file": OUTPUT_FILE, "items": len(items)}))

    open_in_browser(OUTPUT_FILE)


if __name__ == "__main__":
    main()
