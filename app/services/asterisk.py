import uuid
import json
import asyncio
from typing import Optional, Dict, Any, Tuple
from loguru import logger
import httpx

from config.settings import get_settings

settings = get_settings()


class AsteriskService:
    """Service for interacting with Asterisk ARI (REST)."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._connected_ok: bool = False

    def _build_client(self) -> httpx.AsyncClient:
        # Configure sensible timeouts and connection limits
        timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        return httpx.AsyncClient(
            base_url=settings.ari_http_url,
            auth=(settings.ari_username, settings.ari_password),
            timeout=timeout,
            limits=limits,
            headers={"Accept": "application/json"},
        )

    async def connect(self) -> bool:
        # For ARI over REST, "connect" can validate credentials with a lightweight GET
        try:
            if self._client is None:
                self._client = self._build_client()
            # Probe /applications to verify access
            resp = await self._client.get("/applications")
            ok = resp.status_code == 200
            self._connected_ok = ok
            logger.info(
                "ARI connectivity check",
                extra={"ok": ok, "status": resp.status_code},
            )
            return self._connected_ok
        except Exception as e:
            logger.error("Error connecting to ARI", extra={"error": str(e)})
            self._connected_ok = False
            return False

    async def disconnect(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._connected_ok = False

    async def is_connected(self) -> bool:
        return self._client is not None and self._connected_ok

    async def originate_call(
        self,
        phone_number: str,
        context: Optional[str] = None,
        extension: Optional[str] = None,
        priority: Optional[int] = None,
        timeout: Optional[int] = None,
        caller_id: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Origina una llamada usando ARI al contexto/extensión indicados.
        Realiza un POST a /channels con endpoint Local/number@context, luego dials to extension.
        """
        # Defaults from settings (for compatibility with existing API)
        context = context or settings.default_context
        extension = extension or settings.default_extension
        priority = priority or settings.default_priority
        timeout = timeout or settings.default_timeout
        caller_id = caller_id or settings.default_caller_id

        if self._client is None and not await self.connect():
            return {"success": False, "error": "Unable to connect to ARI"}

        action_id = str(uuid.uuid4())
        # Strategy: create a channel that dials the Local/number@context path
        channel_id = action_id

        params = {
            "endpoint": f"Local/{phone_number}@{context}",
            "app": settings.ari_app,
            "callerId": caller_id,
            "timeout": int(timeout / 1000) if timeout else None,
            "channelId": channel_id,
        }
        # Remove None entries and ensure variables are JSON-encoded for ARI
        params = {k: v for k, v in params.items() if v is not None}
        if variables:
            try:
                params["variables"] = json.dumps(variables)
            except Exception:
                # Fallback: stringify dict
                params["variables"] = json.dumps({str(k): str(v) for k, v in variables.items()})

        async def _attempt() -> Tuple[bool, Optional[httpx.Response], Optional[str]]:
            try:
                resp = await self._client.post("/channels", params=params)  # type: ignore[arg-type]
                if resp.status_code in (200, 202):
                    return True, resp, None
                # Treat 5xx as retryable, 401/403/404 as final
                if 500 <= resp.status_code < 600:
                    return False, resp, None
                return False, resp, f"ARI error {resp.status_code}"
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                return False, None, str(e)
            except Exception as e:
                return False, None, str(e)

        # Simple retry with exponential backoff for transient failures
        attempts = 0
        last_error: Optional[str] = None
        last_resp: Optional[httpx.Response] = None
        while attempts < 3:
            ok, resp, err = await _attempt()
            if ok and resp is not None:
                logger.info("ARI originate accepted", extra={"channel_id": channel_id})
                return {
                    "success": True,
                    "call_id": action_id,
                    "phone_number": phone_number,
                    "channel": channel_id,
                    "context": context,
                    "extension": extension,
                    "priority": priority,
                    "timeout": timeout,
                    "caller_id": caller_id,
                    "message": "Call originated via ARI",
                }
            # Not ok
            last_error = err
            last_resp = resp
            attempts += 1
            if attempts < 3:
                await asyncio.sleep(0.3 * (2 ** (attempts - 1)))

        # If we reach here, all attempts failed
        if last_resp is not None:
            logger.error(
                "ARI originate failed",
                extra={"status": last_resp.status_code, "body": last_resp.text[:500]},
            )
            return {
                "success": False,
                "error": f"ARI error {last_resp.status_code}",
                "details": last_resp.text,
            }
        logger.error("ARI originate exception", extra={"error": last_error})
        return {"success": False, "error": last_error or "Unknown error"}


# Instancia global del servicio
asterisk_service = AsteriskService()


async def get_asterisk_service() -> AsteriskService:
    return asterisk_service