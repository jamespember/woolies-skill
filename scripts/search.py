#!/usr/bin/env python3
"""Woolworths product search helper.

Usage: python3 search.py <search_term> [page_size]

Fetches cookies from the homepage first (Akamai bot detection),
then searches the product API. Outputs JSON to stdout.
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar


def search(search_term: str, page_size: int = 10) -> dict:
    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    )

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    # Step 1: Get bot-detection cookies from the homepage
    req = urllib.request.Request(
        "https://www.woolworths.com.au/",
        headers={"User-Agent": ua},
    )
    try:
        opener.open(req, timeout=15)
    except Exception:
        pass  # Best-effort cookie fetch

    # Step 2: Search products
    encoded_term = urllib.parse.quote(search_term)
    body = json.dumps(
        {
            "Filters": [],
            "IsSpecial": False,
            "Location": f"/shop/search/products?searchTerm={encoded_term}",
            "PageNumber": 1,
            "PageSize": page_size,
            "SearchTerm": search_term,
            "SortType": "TraderRelevance",
            "IsHideEverydayMarketProducts": False,
            "IsRegisteredRewardCardPromotion": None,
            "ExcludeSearchTypes": ["UntraceableVendors"],
            "GpBoost": 0,
            "GroupEdmVariants": False,
            "EnableAdReRanking": False,
        }
    ).encode()

    req = urllib.request.Request(
        "https://www.woolworths.com.au/apis/ui/Search/products",
        data=body,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.woolworths.com.au",
            "Referer": f"https://www.woolworths.com.au/shop/search/products?searchTerm={encoded_term}",
            "User-Agent": ua,
        },
        method="POST",
    )

    try:
        resp = opener.open(req, timeout=20)
        raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        return {"error": f"API returned HTTP {e.code}", "search_term": search_term}
    except Exception as e:
        return {"error": f"Request failed: {e}", "search_term": search_term}

    # Step 3: Parse and extract useful fields
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse API response", "search_term": search_term}

    results = []
    for group in data.get("Products", []):
        for p in group.get("Products", []):
            product = {
                "stockcode": p.get("Stockcode"),
                "name": p.get("DisplayName") or p.get("Name"),
                "brand": p.get("Brand"),
                "size": p.get("PackageSize"),
                "price": p.get("Price"),
                "cup_price": p.get("CupPrice"),
                "cup_measure": p.get("CupMeasure"),
                "cup_string": p.get("CupString"),
                "was_price": p.get("WasPrice"),
                "savings": p.get("SavingsAmount"),
                "is_on_special": p.get("IsOnSpecial", False),
                "is_half_price": p.get("IsHalfPrice", False),
                "is_edr_special": p.get("IsEdrSpecial", False),
                "in_stock": p.get("IsInStock", False),
                "is_available": p.get("IsAvailable", False),
            }

            # Extract multibuy info if present
            ct = p.get("CentreTag") or {}
            mb = ct.get("MultibuyData")
            if mb:
                product["multibuy"] = {
                    "quantity": mb.get("Quantity"),
                    "price": mb.get("Price"),
                }

            # Extract header tag (special label), strip HTML
            ht = p.get("HeaderTag")
            if ht:
                content = ht.get("Content") or ""
                product["special_label"] = re.sub(r"<[^>]+>", "", content)

            results.append(product)

    return {
        "search_term": search_term,
        "total_results": data.get("SearchResultsCount", 0),
        "products": results,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 search.py <search_term> [page_size]", file=sys.stderr)
        sys.exit(1)

    search_term = sys.argv[1]
    page_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    result = search(search_term, page_size)

    if "error" in result:
        print(json.dumps(result), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
