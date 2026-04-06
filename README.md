# woolies-skill

An AI agent skill for searching Woolworths Australia products, optimising shopping lists, and meal planning. Works with any agent that supports the [Agent Skills](https://agentskills.io) pattern (Claude Code, OpenCode, etc).

## What it does

- Searches woolworths.com.au for products and compares prices
- Ranks by unit price, highlights specials and half-price items
- Plans meals by clustering recipes around shared ingredients to reduce cost and waste
- Saves recipes locally so it learns what you cook over time
- Generates a browser console snippet to add items to your Woolworths cart

## Install

Clone into your agent's skill directory. The folder must be named `woolies`.

**Claude Code:**
```bash
git clone https://github.com/jamespember/woolies-skill.git ~/.claude/skills/woolies
```

**OpenCode:**
```bash
git clone https://github.com/jamespember/woolies-skill.git ~/.config/opencode/skills/woolies
```

**Other agents:** clone it wherever your agent loads skills from. The agent needs to read `SKILL.md` to know what to do.

Then make the scripts executable:
```bash
chmod +x <install-path>/scripts/*.sh
```

## Requirements

- `bash`, `curl`, `python3` (standard on macOS/Linux)
- No API keys needed for searching
- Adding to cart requires being logged into woolworths.com.au in your browser

## Usage

Use the `/woolies` slash command, or just ask naturally -- the agent will pick up the skill automatically when it's relevant.

```
/woolies milk, eggs, chicken thighs, rice
```

```
/woolies shop for beef tacos and fried rice
```

```
/woolies plan 5 dinners for this week
```

Or without the command:

```
optimise my woolies list: milk, eggs, bread
plan meals for the week
```

The skill supports three modes:

1. **Shopping list** -- give it a list of items, it searches Woolworths and compares prices
2. **Recipe shopping** -- name some recipes, it pulls ingredients (from its library or its own knowledge), merges duplicates, and price-compares
3. **Meal planning** -- ask it to plan meals and it clusters recipes around shared ingredients to minimise cost and waste

Recipes you confirm get saved to `recipes.json` so the skill remembers them next time.

## Files

```
SKILL.md           # Skill definition the agent reads for instructions
scripts/search.sh  # Product search via Woolworths API
scripts/recipes.sh # Recipe library CRUD + ingredient overlap analysis
scripts/cart.sh    # Generates JS snippet to add items to cart
recipes.json       # Your saved recipes (starts empty, grows over time)
```
