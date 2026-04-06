#!/usr/bin/env python3
"""Manage the woolies recipe library.

Usage:
  python3 recipes.py list                         - List all saved recipes (names + tags)
  python3 recipes.py show <name>                  - Show a recipe's full details
  python3 recipes.py save '<recipe_json>'         - Save/update a recipe
  python3 recipes.py delete <name>                - Delete a recipe by name
  python3 recipes.py search <ingredient>          - Find recipes containing an ingredient
  python3 recipes.py overlap <name1> <name2> ...  - Show shared ingredients between recipes
"""

import json
import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPE_FILE = os.path.join(SCRIPT_DIR, "..", "recipes.json")


def load_data() -> dict:
    """Load recipe data from file, creating it if needed."""
    if not os.path.exists(RECIPE_FILE):
        data = {"recipes": []}
        save_data(data)
        return data
    with open(RECIPE_FILE, "r") as f:
        return json.load(f)


def save_data(data: dict):
    """Write recipe data to file."""
    with open(RECIPE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_recipe(recipes: list, name: str):
    """Find a recipe by name (case-insensitive)."""
    name_lower = name.lower().strip()
    for r in recipes:
        if r["name"].lower().strip() == name_lower:
            return r
    return None


def ingredient_key(ing: dict) -> str:
    """Normalise ingredient name for comparison."""
    return ing.get("item", "").lower().strip()


def cmd_list(recipes: list):
    if not recipes:
        print(json.dumps({"recipes": [], "count": 0}))
        return
    summary = []
    for r in recipes:
        summary.append(
            {
                "name": r["name"],
                "tags": r.get("tags", []),
                "serves": r.get("serves"),
                "ingredient_count": len(r.get("ingredients", [])),
            }
        )
    print(json.dumps({"recipes": summary, "count": len(summary)}, indent=2))


def cmd_show(recipes: list, args: list):
    if not args:
        print('{"error": "Usage: recipes.py show <name>"}', file=sys.stderr)
        sys.exit(1)
    name = " ".join(args)
    r = find_recipe(recipes, name)
    if r:
        print(json.dumps(r, indent=2))
    else:
        print(json.dumps({"error": f"Recipe '{name}' not found"}))


def cmd_save(data: dict, recipes: list, args: list):
    if not args:
        print('{"error": "Usage: recipes.py save \'<json>\'"}', file=sys.stderr)
        sys.exit(1)
    raw = args[0]
    try:
        new_recipe = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    if "name" not in new_recipe or "ingredients" not in new_recipe:
        print(
            json.dumps({"error": "Recipe must have 'name' and 'ingredients'"}),
            file=sys.stderr,
        )
        sys.exit(1)

    existing = find_recipe(recipes, new_recipe["name"])
    if existing:
        idx = recipes.index(existing)
        recipes[idx] = new_recipe
        action_taken = "updated"
    else:
        recipes.append(new_recipe)
        action_taken = "saved"

    data["recipes"] = recipes
    save_data(data)
    print(
        json.dumps(
            {
                "status": action_taken,
                "name": new_recipe["name"],
                "total_recipes": len(recipes),
            }
        )
    )


def cmd_delete(data: dict, recipes: list, args: list):
    if not args:
        print('{"error": "Usage: recipes.py delete <name>"}', file=sys.stderr)
        sys.exit(1)
    name = " ".join(args)
    existing = find_recipe(recipes, name)
    if existing:
        recipes.remove(existing)
        data["recipes"] = recipes
        save_data(data)
        print(
            json.dumps(
                {"status": "deleted", "name": name, "total_recipes": len(recipes)}
            )
        )
    else:
        print(json.dumps({"error": f"Recipe '{name}' not found"}))


def cmd_search(recipes: list, args: list):
    if not args:
        print('{"error": "Usage: recipes.py search <ingredient>"}', file=sys.stderr)
        sys.exit(1)
    query = " ".join(args).lower()
    matches = []
    for r in recipes:
        for ing in r.get("ingredients", []):
            if query in ingredient_key(ing):
                matches.append({"name": r["name"], "matched_ingredient": ing})
                break
    print(
        json.dumps(
            {"query": query, "matches": matches, "count": len(matches)}, indent=2
        )
    )


def cmd_overlap(recipes: list, args: list):
    if len(args) < 2:
        print(
            '{"error": "Usage: recipes.py overlap <name1> <name2> ..."}',
            file=sys.stderr,
        )
        sys.exit(1)

    selected = []
    for name in args:
        r = find_recipe(recipes, name)
        if not r:
            print(json.dumps({"error": f"Recipe '{name}' not found"}))
            sys.exit(1)
        selected.append(r)

    # Build ingredient sets per recipe
    recipe_ingredients = {}
    for r in selected:
        keys = set()
        for ing in r.get("ingredients", []):
            keys.add(ingredient_key(ing))
        recipe_ingredients[r["name"]] = keys

    # Find overlaps
    all_ingredients = set()
    for keys in recipe_ingredients.values():
        all_ingredients |= keys

    overlap_map = {}
    for ing in sorted(all_ingredients):
        used_in = [name for name, keys in recipe_ingredients.items() if ing in keys]
        overlap_map[ing] = used_in

    shared = {k: v for k, v in overlap_map.items() if len(v) > 1}
    unique = {k: v[0] for k, v in overlap_map.items() if len(v) == 1}

    print(
        json.dumps(
            {
                "recipes": [r["name"] for r in selected],
                "total_unique_ingredients": len(all_ingredients),
                "shared_ingredients": shared,
                "shared_count": len(shared),
                "unique_ingredients": unique,
                "unique_count": len(unique),
            },
            indent=2,
        )
    )


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python3 recipes.py <list|show|save|delete|search|overlap> [args]",
            file=sys.stderr,
        )
        sys.exit(1)

    action = sys.argv[1]
    args = sys.argv[2:]

    data = load_data()
    recipes = data.get("recipes", [])

    if action == "list":
        cmd_list(recipes)
    elif action == "show":
        cmd_show(recipes, args)
    elif action == "save":
        cmd_save(data, recipes, args)
    elif action == "delete":
        cmd_delete(data, recipes, args)
    elif action == "search":
        cmd_search(recipes, args)
    elif action == "overlap":
        cmd_overlap(recipes, args)
    else:
        print(
            json.dumps(
                {
                    "error": f"Unknown action: {action}. Use list|show|save|delete|search|overlap"
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
