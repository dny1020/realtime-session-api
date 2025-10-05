import uuid
import json
import asyncio
from typing import Optional, Dict, Any, Tuple, Callable
from loguru import logger
import httpx
import websockets
from datetime import datetime

from config.settings import get_settings

settings = get_settings()


class AsteriskService:
    """Service for interacting with Asterisk ARI (REST + WebSocket)."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected_ok: bool = False
        self._ws_task: Optional[asyncio.Task] = None
        self._event_handlers: Dict[str, Callable] = {}

    def _build_client(self) -> httpx.AsyncClient:
        # Configure sensible timeouts and connection limits
        timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
        limits = httpx.Limits(
            max_keepalive_connections=settings.ari_max_keepalive,
            max_connections=settings.ari_max_connections
        )
        return httpx.AsyncClient(
            base_url=settings.ari_http_url,
            auth=(settings.ari_username, settings.ari_password),
            timeout=timeout,
            limits=limits,
            headers={"Accept": "application/json"},
        )

    async def connect(self) -> bool:
        """Connect to ARI HTTP and WebSocket"""
        try:
            # HTTP Client
            if self._client is None:
                self._client = self._build_client()
            # Probe /applications to verify access
            resp = await self._client.get("/applications")
            ok = resp.status_code == 200
            self._connected_ok = ok
            
            if ok:
                # Connect to WebSocket for events
                await self._connect_websocket()
            
            logger.info(
                "ARI connectivity check",
                extra={"ok": ok, "status": resp.status_code, "websocket": self._ws is not None},
            )
            return self._connected_ok
        except Exception as e:
            logger.error("Error connecting to ARI", extra={"error": str(e)})
            self._connected_ok = False
            return False

    async def _connect_websocket(self):
        """Connect to ARI WebSocket for real-time events"""
        try:
            # Build WebSocket URL from HTTP URL
            ws_url = settings.ari_http_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{ws_url}/events?app={settings.ari_app}&api_key={settings.ari_username}:{settings.ari_password}"
            
            self._ws = await websockets.connect(ws_url)
            logger.info("WebSocket connected to ARI", extra={"url": ws_url})
            
            # Start listening for events
            self._ws_task = asyncio.create_task(self._listen_events())
        except Exception as e:
            logger.error("Error connecting to WebSocket", extra={"error": str(e)})
            self._ws = None

    async def _listen_events(self):
        """Listen for ARI events via WebSocket"""
        if self._ws is None:
            return
        
        try:
            async for message in self._ws:
                try:
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    logger.debug(f"ARI Event received: {event_type}", extra={"event": event})
                    
                    # Call registered handlers
                    if event_type in self._event_handlers:
                        await self._event_handlers[event_type](event)
                    
                    # Also call generic handler if registered
                    if "*" in self._event_handlers:
                        await self._event_handlers["*"](event)
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to decode WebSocket message", extra={"message": message})
                except Exception as e:
                    logger.error("Error processing ARI event", extra={"error": str(e)})
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._ws = None
        except Exception as e:
            logger.error("Error in WebSocket listener", extra={"error": str(e)})
            self._ws = None

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific ARI event type. Use '*' for all events."""
        self._event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def disconnect(self):
        """Disconnect from ARI HTTP and WebSocket"""
        # Cancel WebSocket listener
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        
        # Close WebSocket
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        
        # Close HTTP client
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