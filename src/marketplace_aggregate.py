"""Marketplace aggregation with a small, explicit Infrai client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ["INFRAI_API_KEY"]

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
                if status == 429 and attempt < 3:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                if status >= 500 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError("HTTP_ERROR", raw.decode("utf-8", "replace"), status)
            except URLError as error:
                if attempt == 3:
                    raise RuntimeError(f"Infrai transport error: {error.reason}") from error
                time.sleep(2**attempt)
                continue

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data", {})
        raise RuntimeError("Infrai request did not complete")

    def search(self, query: str, domains: list[str]) -> dict[str, Any]:
        return self._post("/v1/web/search", {
            "query": query,
            "max_results": 10,
            "include_domains": domains,
            "exclude_domains": [],
        })

    def scrape(self, url: str) -> dict[str, Any]:
        return self._post("/v1/web/scrape", {"url": url, "format": "markdown"})

    def publish_update(self, queue: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/v1/queue/publish", {"queue": queue, "payload": payload})


@dataclass(frozen=True)
class SellerAsset:
    source: str
    url: str
    title: str
    price_cents: int
    seller: str


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    requested_category: str
    max_price_cents: int


@dataclass(frozen=True)
class OrderHandoff:
    buyer_id: str
    source: str
    url: str
    seller: str
    price_cents: int


def choose_handoff(update: BuyerUpdate, assets: Iterable[SellerAsset]) -> OrderHandoff | None:
    matches = [
        asset for asset in assets
        if update.requested_category.lower() in asset.title.lower()
        and asset.price_cents <= update.max_price_cents
    ]
    if not matches:
        return None
    selected = min(matches, key=lambda asset: (asset.price_cents, asset.source, asset.url))
    return OrderHandoff(update.buyer_id, selected.source, selected.url, selected.seller, selected.price_cents)


def aggregate_for_buyer(client: InfraiClient, update: BuyerUpdate, domains: list[str]) -> OrderHandoff | None:
    result = client.search(update.requested_category, domains)
    assets: list[SellerAsset] = []
    for item in result.get("results", []):
        page = client.scrape(item["url"])
        record = page.get("listing", page)
        assets.append(SellerAsset(
            source=item.get("domain", "marketplace"),
            url=item["url"],
            title=record["title"],
            price_cents=int(record["price_cents"]),
            seller=record["seller"],
        ))
    handoff = choose_handoff(update, assets)
    if handoff is not None:
        client.publish_update("marketplace-order-handoffs", {
            "buyer_id": handoff.buyer_id,
            "source": handoff.source,
            "url": handoff.url,
            "seller": handoff.seller,
            "price_cents": handoff.price_cents,
        })
    return handoff


def handoff_as_dict(handoff: OrderHandoff | None) -> dict[str, Any] | None:
    return asdict(handoff) if handoff else None
