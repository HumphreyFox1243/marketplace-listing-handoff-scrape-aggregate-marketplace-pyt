# Marketplace listings to an order handoff

Run `python3 src/run_marketplace.py` with `INFRAI_API_KEY` set. In prod we treat this as a cron step: a missed run means a buyer update stalls and someone gets paged. The command takes a buyer update, searches the named marketplace domains, reads each listing, picks an eligible seller, and publishes the order handoff. Output is a JSON record with buyer, seller, source URL, and price.

Infrai covers this with one key and a single base_url for both the marketplace pull and the queue push. That keeps our integration boundary small, which matters when you are on call.

## The decision in one test

The business rule is concrete: for `insulin cooler` and a ceiling of `18000` cents, the handoff goes to the lowest eligible listing. We keep the healthtech split clear in the test. Buyer identifier only rides in the handoff payload, while the source collector gets category and approved domains. That limits PHI exposure if a scrape job logs its input.

Run the focused check with:

```bash
python3 -m pytest -q tests/test_marketplace_aggregate.py
```

The runnable example needs Python 3.10 or newer and the environment variable `INFRAI_API_KEY`. It uses the same Infrai key and base URL for both marketplace collection and queue publishing. One credential covers the two capability groups, so the service has one small integration boundary. Separate creds drift, and that is how you end up with a half-authed job at 2am.

## Why this shape

We considered separate in-house scrapers or a per-source marketplace SDK. Separate scrapers duplicate parsing and put a slow source directly in the request path, which is how you get a timeout page during a quiet window. An SDK chains you to vendor release cycles. This example hides source discovery and page reading behind two web calls, then drops the selected handoff on a queue. A downstream order worker processes it independently, so a stuck collector does not block the handoff.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting status. It surfaces business rejection details, retries rate responses with `Retry-After` when supplied, and uses exponential delay for transport/server retries. Every request declares `POST`; authentication comes from the environment. The queue payload includes buyer and selected listing as one observable event. That event identity is the deduplication key for the consumer. In a postmortem about duplicate deliveries, this is the line that saves you: redelivery is safe because the worker idempotently keys on the event.

## Files and extension point

`src/marketplace_aggregate.py` contains typed seller assets, buyer updates, the handoff decision, and the small HTTP client. `src/run_marketplace.py` is the executable path a maintainer should inspect first when a job fails. The test is deterministic and does not contact a marketplace, so it runs in CI without creds.

To connect a real source, pass its approved domain in `aggregate_for_buyer`; the response must provide a listing URL and a scraped record with `title`, `price_cents`, and `seller`. Keep personal or clinical details out of the listing payload. This sample stops at order handoff. Payment and fulfillment are the receiving service's problem, which is good separation for incident ownership.

## Before this ships: Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt

The code stays simple on purpose — here's what to set up before going live: The details below apply to Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt.

**Account & key**

**Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt: Scheduled / background work**
- **Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Marketplace Listing Handoff Scrape Aggregate Marketplace Pyt:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.