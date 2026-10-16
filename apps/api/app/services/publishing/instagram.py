"""Instagram API with Instagram Login. No Facebook Page or private Instagram API."""

import logging
from urllib.parse import urlencode

import httpx

# Token exchange endpoints require query credentials; HTTP client info logs include URLs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

SCOPES = ["instagram_business_basic", "instagram_business_content_publish", "instagram_business_manage_insights"]
GRAPH = "https://graph.instagram.com"


def checked(response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        raise RuntimeError(f"Instagram returned non-JSON HTTP {response.status_code}") from None
    if response.is_error or "error" in body:
        error = body.get("error") or {}
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        # Provider messages may echo credentials or signed media URLs. Never persist them.
        raise RuntimeError(f"Instagram API HTTP {response.status_code}, error code {code}")
    return body


def authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
    return "https://www.instagram.com/oauth/authorize?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(SCOPES),
            "state": state,
            "enable_fb_login": "0",
            "force_authentication": "1",
        }
    )


def exchange(code: str, settings) -> dict:
    try:
        return _exchange(code, settings)
    except httpx.HTTPError:
        raise RuntimeError("Instagram authorization exchange could not reach Meta") from None


def _exchange(code: str, settings) -> dict:
    with httpx.Client(timeout=30) as client:
        short = checked(
            client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": settings.instagram_client_id,
                    "client_secret": settings.instagram_client_secret.get_secret_value(),
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.instagram_redirect_uri,
                    "code": code,
                },
            )
        )
        if "access_token" not in short:
            raise RuntimeError("Instagram did not return an access token")
        long = checked(
            client.get(
                f"{GRAPH}/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": settings.instagram_client_secret.get_secret_value(),
                    "access_token": short["access_token"],
                },
            )
        )
        return {**long, "user_id": str(short.get("user_id", "")), "permissions": short.get("permissions", [])}


class Instagram:
    def __init__(self, access_token: str, version: str = "v24.0"):
        self.token = access_token
        self.base = f"{GRAPH}/{version}"

    def request(self, method: str, path: str, **params) -> dict:
        try:
            with httpx.Client(timeout=60, headers={"Authorization": f"Bearer {self.token}"}) as client:
                response = (
                    client.get(f"{self.base}/{path}", params=params)
                    if method == "GET"
                    else client.post(f"{self.base}/{path}", data=params)
                )
            return checked(response)
        except httpx.HTTPError:
            raise RuntimeError("Instagram network request failed; outcome may be unknown") from None

    def profile(self) -> dict:
        return self.request("GET", "me", fields="user_id,username,account_type")

    def permissions(self, user_id: str) -> list[str]:
        body = self.request("GET", f"{user_id}/permissions")
        return [p["permission"] for p in body.get("data", []) if p.get("status") == "granted"]

    def refresh(self) -> dict:
        try:
            return checked(
                httpx.get(
                    f"{GRAPH}/refresh_access_token",
                    params={
                        "grant_type": "ig_refresh_token",
                        "access_token": self.token,
                    },
                    timeout=30,
                )
            )
        except httpx.HTTPError:
            raise RuntimeError("Instagram token renewal could not reach Meta") from None

    def create_reel(self, user_id: str, video_url: str, caption: str) -> str:
        return str(
            self.request(
                "POST",
                f"{user_id}/media",
                media_type="REELS",
                video_url=video_url,
                caption=caption,
                share_to_feed="true",
            )["id"]
        )

    def container(self, container_id: str) -> dict:
        return self.request("GET", container_id, fields="status_code,status")

    def publish(self, user_id: str, container_id: str) -> str:
        return str(self.request("POST", f"{user_id}/media_publish", creation_id=container_id)["id"])
