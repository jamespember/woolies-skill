---
name: woolies
description: >
  Woolworths shopping list optimiser and meal planner. Searches
  woolworths.com.au for best prices, plans meals by clustering recipes
  around shared ingredients to minimise cost and waste, and can add items
  to your cart. Learns your recipes over time. Use when asked to "optimise
  my shopping", "woolies list", "woolworths shop", "grocery list",
  "plan meals", "meal plan", "what should I cook this week", or when the
  /woolies command is run.
---

# Woolies Shopping List Optimiser & Meal Planner

## Tools

### Product Search

```bash
python3 scripts/search.py "<search term>" [page_size]
```

- Returns JSON: `name`, `brand`, `size`, `price`, `cup_price`, `cup_measure`,
  `is_on_special`, `is_half_price`, `savings`, `special_label`, `in_stock`
- Run searches **in parallel** for speed

### Recipe Library

```bash
python3 scripts/recipes.py <action> [args]
```

| Action | Usage | Description |
|--------|-------|-------------|
| `list` | `recipes.py list` | List all saved recipes |
| `show` | `recipes.py show "Beef Tacos"` | Show full recipe details |
| `save` | `recipes.py save '<json>'` | Save or update a recipe |
| `delete` | `recipes.py delete "Beef Tacos"` | Delete a recipe |
| `search` | `recipes.py search onion` | Find recipes using an ingredient |
| `overlap` | `recipes.py overlap "Beef Tacos" "Nachos"` | Show shared ingredients |

#### Recipe JSON Schema

When saving a recipe, use this format:

```json
{
  "name": "Beef Tacos",
  "serves": 4,
  "tags": ["mexican", "quick", "weeknight"],
  "ingredients": [
    {"item": "beef mince", "qty": "500g", "search_term": "beef mince"},
    {"item": "onion", "qty": "1", "search_term": "brown onion"},
    {"item": "taco shells", "qty": "1 pack", "search_term": "taco shells"},
    {"item": "cheddar cheese", "qty": "200g", "search_term": "cheddar cheese"},
    {"item": "sour cream", "qty": "1 tub", "search_term": "sour cream"},
    {"item": "iceberg lettuce", "qty": "1", "search_term": "iceberg lettuce"},
    {"item": "tomato", "qty": "2", "search_term": "tomato"}
  ]
}
```

Key points:
- `item` is the normalised ingredient name (lowercase, singular where sensible)
- `search_term` is what to search on Woolworths (can differ from item name)
- `tags` help with clustering and suggestions
- Skip pantry staples (oil, salt, pepper, common dried spices) unless central

### Add to Cart

```bash
python3 scripts/cart.py '[{"stockcode": 123, "quantity": 1}]'
```

- Generates a JavaScript snippet the user pastes into the browser console on
  woolworths.com.au (must be logged in)
- Always ask before generating

### Shopping List HTML

```bash
python3 scripts/shopping_list.py '<json>'
```

- Generates a self-contained HTML shopping list and opens it in the browser
- Writes to `/tmp/woolies-shopping-list.html` (overwritten each time)
- The page is mobile-friendly with checkboxes that persist via localStorage
- **Embedded Add to Cart script** - when items include `stockcode`, the page
  includes a collapsible panel with the cart JS snippet, a "Select All" button,
  and a "Copy to Clipboard" button. No need to run `cart.py` separately.
- Input JSON schema:

```json
{
  "title": "Shopping List",
  "recipes": ["Beef Tacos", "Fried Rice"],
  "items": [
    {
      "item": "beef mince",
      "product": "Woolworths Beef Mince 500g",
      "stockcode": 661766,
      "price": 7.00,
      "quantity": 2,
      "is_on_special": true,
      "savings": 3.00,
      "special_label": "2 for $10",
      "used_in": ["Beef Tacos", "Fried Rice"]
    }
  ],
  "total": 45.50,
  "total_savings": 5.00
}
```

- `title`: optional, defaults to "Shopping List"
- `recipes`: optional, shown as pills at the top of the page
- `items[].stockcode`: optional, links product name to its Woolworths page
- `items[].used_in`: optional, shows which recipes need each item
- `total` / `total_savings`: optional, shown in a sticky footer

---

## Workflows

The skill supports three modes depending on what the user asks for.

### Mode 1: Quick Shopping List

**Trigger**: User provides a plain list like "milk, eggs, bread, chicken"

1. For each item, search Woolworths (5-10 results, parallel)
2. Rank top 3 by unit price, boosting on-special items within 15% of cheapest
3. Exclude out-of-stock items
4. Present comparison table per item with recommendation
5. Show summary with estimated total and savings
6. Offer to add recommended items to cart
7. **Generate HTML shopping list** - call `shopping_list.py` with the final
   picks (include `stockcode` from search results so products link to
   Woolworths). Opens in browser automatically.

### Mode 2: Recipe Shopping

**Trigger**: User provides recipe names like "beef tacos, spaghetti bolognese"

1. **Check the library first** - run `recipes.py list` then `recipes.py show`
   for any matching saved recipes
2. **For unknown recipes** - generate ingredients from your knowledge. Present
   the breakdown and ask the user to confirm/adjust
3. **Save confirmed recipes** - once the user confirms a recipe's ingredients,
   save it with `recipes.py save` so it's available next time. Tell the user
   you're saving it.
4. **Merge ingredients** across recipes, summing quantities for duplicates.
   Call `recipes.py overlap` to highlight what's shared.
5. **Search and optimise** per Mode 1
6. **Note the overlaps** - tell the user which shared ingredients save them
   money/waste (e.g. "onion is used in both tacos and bolognese")
7. **Generate HTML shopping list** per Mode 1 step 7

### Mode 3: Meal Planning

**Trigger**: User asks to "plan meals", "what should I cook this week", or
gives a number like "plan 5 dinners"

1. **Load the library** - run `recipes.py list` to see what's saved
2. **Suggest recipe combinations** that maximise ingredient overlap:
   - If the library has recipes, prioritise combinations from it
   - Fill gaps with new suggestions from your knowledge
   - When suggesting, explain WHY these cluster well (shared ingredients)
3. **Present 2-3 meal plan options** as groups, showing:
   - The recipes in each group
   - Shared ingredients count
   - Estimated unique ingredients needed
4. **User picks a plan** (or mixes and matches)
5. **Save any new recipes** that the user confirms
6. **Run overlap analysis** with `recipes.py overlap` on the final selection
7. **Search and optimise** per Mode 1
8. **Present the full plan** with:
   - Recipe list with shared ingredient highlights
   - Optimised shopping list
   - Total cost estimate
   - Savings from ingredient clustering vs buying separately
9. **Generate HTML shopping list** per Mode 1 step 7

### Clustering Logic

When suggesting recipe combinations for meal planning, optimise for:

1. **Ingredient overlap** - recipes that share proteins, vegetables, bases
   - e.g. mince → tacos + bolognese + cottage pie
   - e.g. chicken thighs → stir fry + curry + tray bake
2. **Variety** - don't suggest 5 mince dishes. Vary proteins and cuisines
3. **Practicality** - mix quick weeknight meals with slower weekend ones
4. **Seasonal sense** - suggest warming food in winter, lighter in summer

When comparing combinations, score them by:
- `shared_count` from the overlap tool (higher = better)
- `total_unique_ingredients` from the overlap tool (lower = better)
- Variety of protein/cuisine (subjective, use judgement)

---

## Output Format

### Per-item comparison:

```
## Onion (need: 3 across 2 recipes)

| # | Product | Size | Price | Unit Price | Special? |
|---|---------|------|-------|------------|----------|
| 1 | ...     | ...  | $X.XX | $X.XX/kg   | ...      |
| 2 | ...     | ...  | $X.XX | $X.XX/kg   |          |

-> PICK: [Product] - [reason]
```

### Summary:

```
## Shopping List Summary

| Item | Recommended | Price | Special? |
|------|-------------|-------|----------|
| ...  | ...         | $X.XX | ...      |

**Estimated Total: $XX.XX**
**Savings from specials: $X.XX**

### Ingredient Overlap
- onion: used in Beef Tacos, Spaghetti Bolognese (buy 3)
- tinned tomatoes: used in Bolognese, Chilli (buy 2 cans)
```

---

## Important Rules

- Always check `in_stock` and `is_available` before recommending
- Use `cup_price` / `cup_measure` directly for unit price comparison
- **Always save confirmed recipes** so the library grows over time
- **Always check the library first** before generating a recipe from scratch
- Do NOT skip the confirmation step for new recipes
- If a search returns nothing useful, suggest alternative search terms
- Note that Woolworths prices change frequently - prices are as-of search time
- The search API does NOT require login
- The cart API requires the user to be logged into woolworths.com.au in browser
