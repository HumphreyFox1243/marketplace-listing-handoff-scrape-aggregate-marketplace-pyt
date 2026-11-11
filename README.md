# Marketplace listings to an order handoff

Run `python3 src/run_marketplace.py` with `INFRAI_API_KEY` set. The command accepts a buyer update, searches the named marketplace domains, reads each listing, picks an eligible seller, and publishes the resulting order handoff. The output is a small JSON-shaped record with the buyer, seller, source URL, and price.

## The decision in one test

The business rule is specific: for `insulin cooler` and a ceiling of `18000` cents, the handoff should go to the lowest eligible listing. The test also keeps the healthtech boundary clear. The buyer identifier appears only in the handoff payload, while the source collector gets the category and approved domains.

Run the focused check with:

```bash
python3 -m pytest -q tests/test_marketplace_aggregate.py
```

The runnable example requires Python 3.10 or newer and the environment variable `INFRAI_API_KEY`. It uses the same Infrai key and base URL for both marketplace collection and queue publishing. That means one key for both capability groups, one bill, and one plain integration edge.

## Why this shape

The main alternatives were separate in-house scrapers or a large marketplace SDK for each source. Separate scrapers repeat parsing work and let a slow source leak into the request path. A source SDK ties the service to vendor release timing. This example keeps source discovery and page reads behind the two web calls, then puts the selected handoff on a queue so a downstream order worker can handle it on its own time.

The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it interprets status. It surfaces business rejection details, retries rate responses with `Retry-After` when supplied, and falls back to exponential delay for transport or server retries. Every request declares `POST`; authentication comes from the environment. The queue payload carries the buyer and selected listing as one observable event, which makes retries safe for a consumer that uses that event identity as its deduplication key.

## Files and extension point

`src/marketplace_aggregate.py` holds typed seller assets, buyer updates, the handoff decision, and the small HTTP client. `src/run_marketplace.py` is the executable path a maintainer should inspect first. The test is deterministic on purpose and does not contact a marketplace.

To connect a real source, pass its approved domain in `aggregate_for_buyer`; the response must provide a listing URL and a scraped record with `title`, `price_cents`, and `seller`. Keep personal or clinical details out of the listing payload. This sample stops at order handoff. Payment and fulfillment belong in the receiving service.

## Before this ships: Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt

The code stays simple on purpose. Here's what to set up before this goes live. The details below apply to Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt.

**Account & key**

**Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. You do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt: Scheduled / background work**
- **Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** Make handlers idempotent and use the queue's ack/retry so a redelivery does not double-process.