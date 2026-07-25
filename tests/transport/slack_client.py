"""Slack API client for transport survivability testing.

Zero dependencies beyond requests + stdlib.
Handles the three gotchas:
  1. Cross-origin auth stripping on CDN redirect (SlackAuthAdapter)
  2. CDN propagation delay after upload (wait_for_download_ready)
  3. Deprecated files.upload for snippets (upload_snippet with fallback)
"""

import json
import time
import requests
from urllib.parse import urlparse
from pathlib import Path

SLACK_DOMAINS = {"slack.com", "files.slack.com", "slack-files.com",
                 "slack-edge.com", "slack-imgs.com", "slack-core.com"}

class SlackAPIError(Exception):
    """Raised when the Slack API returns ok:false or an HTTP error."""


class SlackAuthAdapter(requests.adapters.HTTPAdapter):
    """Preserve Authorization header on redirects within Slack's CDN infrastructure.

    Without this, requests strips the Bearer token on the files.slack.com →
    slack-files.com redirect, and you silently download a login page instead
    of the actual file bytes.
    """
    def should_retain_auth_on_redirect(self, original_url, redirect_url):
        orig = urlparse(original_url).hostname or ""
        redir = urlparse(redirect_url).hostname or ""

        def is_slack(host):
            return any(host == d or host.endswith("." + d) for d in SLACK_DOMAINS)

        return is_slack(orig) and is_slack(redir)


class SlackTransportClient:
    """Talk to the Slack Web API for transport survivability tests.

    Usage:
        client = SlackTransportClient(bot_token="xoxb-...", channel_id="C...")
        result = client.upload_file("probe.png")
        raw_bytes, meta = client.download_file(result["files"][0]["id"])
    """

    def __init__(self, bot_token: str, channel_id: str):
        self.token = bot_token
        self.channel = channel_id
        self.base = "https://slack.com/api"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {bot_token}"
        self.session.mount("https://", SlackAuthAdapter())
        self._last_request = 0.0
        self._min_interval = 3.0  # 20 req/min for file ops

    # ------------------------------------------------------------------
    # rate limiting
    # ------------------------------------------------------------------

    def _rate_limit(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    # ------------------------------------------------------------------
    # file upload (modern API: getUploadURLExternal + completeUploadExternal)
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str, title: str | None = None) -> dict:
        """Upload a file to the test channel. Returns the full API response."""
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        file_size = path.stat().st_size
        title = title or path.name

        self._rate_limit()

        # Step 1: get a one-time upload URL
        r = self.session.post(
            f"{self.base}/files.getUploadURLExternal",
            data={"filename": title, "length": file_size},
        )
        up = r.json()
        if not up.get("ok"):
            raise SlackAPIError(f"getUploadURLExternal failed: {up.get('error')}")

        # Step 2: POST raw bytes to the upload URL (NO auth header — it's pre-signed)
        with open(path, "rb") as f:
            raw_r = requests.post(up["upload_url"], data=f.read())
        if raw_r.status_code != 200:
            raise SlackAPIError(
                f"Upload POST failed: HTTP {raw_r.status_code}, body: {raw_r.text[:200]}"
            )

        # Step 3: complete the upload and attach to channel
        r = self.session.post(
            f"{self.base}/files.completeUploadExternal",
            data={
                "files": json.dumps([{"id": up["file_id"], "title": title}]),
                "channel_id": self.channel,
            },
        )
        result = r.json()
        if not result.get("ok"):
            raise SlackAPIError(f"completeUploadExternal failed: {result.get('error')}")
        return result

    def upload_snippet(self, local_path: str, title: str,
                       snippet_type: str = "text") -> dict:
        """Upload as a code snippet. Uses deprecated files.upload with fallback.

        NOTE: The modern upload API has no snippet_type parameter.
        files.upload still works as of 2026-07 but is deprecated.
        If it stops working, this falls back to upload_file().
        """
        self._rate_limit()
        try:
            r = self.session.post(
                f"{self.base}/files.upload",
                data={
                    "channels": self.channel,
                    "title": title,
                    "filetype": snippet_type,
                },
                files={"file": (title, open(local_path, "rb"))},
            )
            result = r.json()
            if result.get("ok"):
                return result
        except Exception:
            pass
        # Fallback: upload as regular file (no snippet rendering)
        return self.upload_file(local_path, title)

    # ------------------------------------------------------------------
    # file download
    # ------------------------------------------------------------------

    def get_file_info(self, file_id: str) -> dict:
        """Call files.info. Returns the 'file' object from the response."""
        self._rate_limit()
        r = self.session.get(f"{self.base}/files.info", params={"file": file_id})
        info = r.json()
        if not info.get("ok"):
            raise SlackAPIError(f"files.info failed: {info.get('error')}")
        return info["file"]

    def wait_for_download_ready(self, file_id: str, timeout: float = 15.0) -> dict:
        """Poll files.info until url_private_download is populated.

        After completeUploadExternal, the CDN takes 1-3 seconds to process.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            f = self.get_file_info(file_id)
            if f.get("url_private_download"):
                return f
            time.sleep(1.0)
        raise SlackAPIError(
            f"url_private_download not ready for file {file_id} after {timeout}s"
        )

    def download_file(self, file_id: str) -> tuple[bytes, dict]:
        """Download file bytes + metadata.

        Returns (raw_bytes, file_metadata_dict).
        Handles the CDN redirect trap via SlackAuthAdapter.
        """
        file_data = self.wait_for_download_ready(file_id)
        url = file_data["url_private_download"]

        r = self.session.get(url)
        ct = r.headers.get("content-type", "")
        if "text/html" in ct:
            raise SlackAPIError(
                f"Download returned HTML (likely auth-stripped redirect). "
                f"Content-Type: {ct}, head bytes: {r.content[:200]}"
            )
        return r.content, file_data

    # ------------------------------------------------------------------
    # messages (for slack_paste transport)
    # ------------------------------------------------------------------

    def post_message(self, text: str) -> dict:
        """Post a message to the test channel. Returns {channel, ts}."""
        self._rate_limit()
        r = self.session.post(
            f"{self.base}/chat.postMessage",
            data={
                "channel": self.channel,
                "text": text,
                "unfurl_links": "false",
                "unfurl_media": "false",
            },
        )
        result = r.json()
        if not result.get("ok"):
            raise SlackAPIError(f"chat.postMessage failed: {result.get('error')}")
        return {"channel": result["channel"], "ts": result["ts"]}

    def get_message_text(self, ts: str) -> str:
        """Retrieve a message by timestamp. Returns the text field."""
        self._rate_limit()
        r = self.session.get(
            f"{self.base}/conversations.history",
            params={
                "channel": self.channel,
                "latest": ts,
                "limit": 1,
                "inclusive": True,
            },
        )
        result = r.json()
        if not result.get("ok"):
            raise SlackAPIError(f"conversations.history failed: {result.get('error')}")
        msgs = result.get("messages", [])
        if not msgs:
            raise SlackAPIError(f"Message at ts={ts} not found in channel {self.channel}")
        return msgs[0].get("text", "")

    def delete_message(self, ts: str) -> None:
        """Delete a message. Best-effort — does not raise on failure."""
        self._rate_limit()
        self.session.post(
            f"{self.base}/chat.delete",
            data={"channel": self.channel, "ts": ts},
        )
