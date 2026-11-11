from marketplace_aggregate import BuyerUpdate, InfraiClient, aggregate_for_buyer, handoff_as_dict


def main() -> None:
    update = BuyerUpdate(buyer_id="buyer-104", requested_category="insulin cooler", max_price_cents=18000)
    handoff = aggregate_for_buyer(InfraiClient(), update, ["example-marketplace.test"])
    print(handoff_as_dict(handoff) or {"status": "no_match"})


if __name__ == "__main__":
    main()
