"""
Basic SDK example: resolve an envelope brief.

This example shows the smallest useful flow:
1) define an envelope brief (size, weight, destination country)
2) determine letter type from dimensions/weight
3) resolve product + zone + price
"""

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from labs.lib.python.porto_client import create_porto_client  # noqa: E402

client = create_porto_client()


async def main() -> None:
    print("Envelope brief -> Porto resolution")
    print("=" * 40)

    # Envelope brief (adjust these values as needed)
    destination_country_code = "DE"
    weight_grams = 20
    dimensions = {"length": 229, "width": 162, "height": 5}

    print("Brief:")
    print(f"- destination country: {destination_country_code}")
    print(f"- weight: {weight_grams}g")
    print(f"- dimensions: {dimensions['length']}x{dimensions['width']}x{dimensions['height']} mm")

    result = await client.identify(
        country_code=destination_country_code,
        weight=weight_grams,
        dimensions=dimensions,
    )

    print("\nResolved result:")
    print(
        f"- letter type: {result['letter_type']['id']}"
        f" (adjusted={result['letter_type']['adjusted']})"
    )
    print(f"- product: {result['product']['id']} ({result['product']['name']})")
    print(f"- zone: {result['zone']['id']} ({result['zone']['name']})")
    print(f"- price: {result['price']['amount'] / 100:.2f} {result['price']['currency']}")


if __name__ == "__main__":
    asyncio.run(main())
