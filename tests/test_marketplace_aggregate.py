import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from marketplace_aggregate import BuyerUpdate, SellerAsset, choose_handoff


def test_buyer_update_hands_off_the_lowest_eligible_seller():
    update = BuyerUpdate("buyer-7", "insulin cooler", 18000)
    assets = [
        SellerAsset("north", "https://north.test/a", "Insulin cooler", 17500, "North Supply"),
        SellerAsset("south", "https://south.test/b", "Insulin cooler", 15200, "South Supply"),
        SellerAsset("west", "https://west.test/c", "Insulin cooler", 21000, "West Supply"),
    ]

    handoff = choose_handoff(update, assets)

    assert handoff is not None
    assert handoff.seller == "South Supply"
    assert handoff.price_cents == 15200
    assert handoff.buyer_id == "buyer-7"
