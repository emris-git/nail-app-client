from __future__ import annotations

import hmac
import json
import time
from hashlib import sha256
from typing import Any, Optional

import httpx


class ClientApiError(RuntimeError):
    pass


class ClientApi:
    def __init__(self, base_url: str, hmac_secret: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = hmac_secret
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _sign(self, *, method: str, path: str, body: str, tg_user_id: int) -> dict[str, str]:
        ts = int(time.time())
        msg = f"{ts}.{method}.{path}.{body}".encode("utf-8")
        sig = hmac.new(self._secret.encode("utf-8"), msg, sha256).hexdigest()
        return {
            "X-Client-Bot-Timestamp": str(ts),
            "X-Client-Bot-Signature": sig,
            "X-Tg-User-Id": str(tg_user_id),
        }

    async def _request(
        self,
        *,
        method: str,
        path: str,
        tg_user_id: int,
        json_body: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        body_str = ""
        if json_body is not None:
            # Must match server's raw request.body() decoding used for signature
            body_str = json.dumps(json_body, separators=(",", ":"), ensure_ascii=False)
        headers = self._sign(method=method, path=path, body=body_str, tg_user_id=tg_user_id)
        if json_body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        r = await self._client.request(method, path, headers=headers, content=body_str or None, params=params)
        if r.status_code >= 400:
            raise ClientApiError(f"{method} {path} failed: {r.status_code} {r.text}")
        if r.status_code == 204:
            return None
        return r.json()

    async def list_masters(self, tg_user_id: int) -> list[dict[str, Any]]:
        return await self._request(method="GET", path="/client/masters", tg_user_id=tg_user_id)

    async def get_master(self, tg_user_id: int, slug: str) -> dict[str, Any]:
        return await self._request(method="GET", path=f"/client/masters/{slug}", tg_user_id=tg_user_id)

    async def list_services(self, tg_user_id: int, slug: str) -> list[dict[str, Any]]:
        return await self._request(method="GET", path=f"/client/masters/{slug}/services", tg_user_id=tg_user_id)

    async def get_availability(
        self, tg_user_id: int, slug: str, service_id: int, days: int = 14
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path=f"/client/masters/{slug}/availability",
            tg_user_id=tg_user_id,
            params={"service_id": service_id, "days": days},
        )

    async def create_booking(self, tg_user_id: int, master_slug: str, service_id: int, start_at: str) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/client/bookings",
            tg_user_id=tg_user_id,
            json_body={"master_slug": master_slug, "service_id": service_id, "start_at": start_at},
        )

    async def my_bookings(self, tg_user_id: int) -> dict[str, Any]:
        return await self._request(method="GET", path="/client/clients/me/bookings", tg_user_id=tg_user_id)

    async def cancel_booking(self, tg_user_id: int, booking_id: int) -> None:
        await self._request(
            method="POST",
            path=f"/client/bookings/{booking_id}/cancel",
            tg_user_id=tg_user_id,
        )

    async def list_favorites(self, tg_user_id: int) -> list[dict[str, Any]]:
        return await self._request(method="GET", path="/client/clients/me/favorites", tg_user_id=tg_user_id)

    async def add_favorite(self, tg_user_id: int, master_slug: str) -> None:
        await self._request(
            method="POST",
            path="/client/clients/me/favorites",
            tg_user_id=tg_user_id,
            json_body={"master_slug": master_slug},
        )

    async def remove_favorite(self, tg_user_id: int, master_slug: str) -> None:
        await self._request(
            method="DELETE",
            path=f"/client/clients/me/favorites/{master_slug}",
            tg_user_id=tg_user_id,
        )

