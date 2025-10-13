import uuid
import json
import asyncio
from typing import Optional, Dict, Any, Callable
from loguru import logger
import httpx
import websockets
from websockets.exceptions import ConnectionClosed

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
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect: bool = True
        self._ws_connected: bool = False

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
                extra={"ok": ok, "status": resp.status_code, "websocket": self._ws_connected},
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
            self._ws_connected = True
            logger.info("WebSocket connected to ARI", extra={"url": ws_url})
            
            # Start listening for events with reconnection support
            self._ws_task = asyncio.create_task(self._listen_events_with_reconnect())
        except Exception as e:
            logger.error("Error connecting to WebSocket", extra={"error": str(e)})
            self._ws = None
            self._ws_connected = False

    async def _ensure_ws_connection(self) -> bool:
        """Reconnect WebSocket with exponential backoff"""
        retry_delays = [1, 2, 5, 10, 30, 60]
        
        for attempt, delay in enumerate(retry_delays, 1):
            try:
                logger.info(f"WebSocket reconnection attempt {attempt}/{len(retry_delays)}")
                
                # Build WebSocket URL from HTTP URL
                ws_url = settings.ari_http_url.replace("http://", "ws://").replace("https://", "wss://")
                ws_url = f"{ws_url}/events?app={settings.ari_app}&api_key={settings.ari_username}:{settings.ari_password}"
                
                self._ws = await websockets.connect(ws_url)
                self._ws_connected = True
                logger.info(f"WebSocket reconnected successfully on attempt {attempt}")
                return True
                
            except Exception as e:
                logger.warning(
                    f"WebSocket reconnection attempt {attempt} failed, retrying in {delay}s",
                    extra={"error": str(e)}
                )
                if attempt < len(retry_delays):
                    await asyncio.sleep(delay)
        
        logger.error("WebSocket reconnection failed after all retries")
        return False

    async def _listen_events_with_reconnect(self):
        """Listen for ARI events via WebSocket with automatic reconnection"""
        while self._should_reconnect:
            # Ensure we have a connection
            if not self._ws or not self._ws_connected:
                if not await self._ensure_ws_connection():
                    # If reconnection failed after all retries, wait before trying again
                    logger.warning("Waiting 60s before retry cycle...")
                    await asyncio.sleep(60)
                    continue
            
            try:
                async for message in self._ws:
                    try:
                        event = json.loads(message)
                        event_type = event.get("type")
                        
                        logger.debug(f"ARI Event received: {event_type}", extra={"event": event})
                        
                        # Call registered handlers
                        if event_type in self._event_handlers:
                            try:
                                await self._event_handlers[event_type](event)
                            except Exception as e:
                                logger.error(
                                    f"Error in event handler for {event_type}",
                                    extra={"error": str(e), "event": event}
                                )
                        
                        # Also call generic handler if registered
                        if "*" in self._event_handlers:
                            try:
                                await self._event_handlers["*"](event)
                            except Exception as e:
                                logger.error(
                                    "Error in generic event handler",
                                    extra={"error": str(e), "event": event}
                                )
                                
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode WebSocket message", extra={"message": message})
                    except Exception as e:
                        logger.error("Error processing ARI event", extra={"error": str(e)})
                        
            except ConnectionClosed as e:
                logger.warning(
                    "WebSocket connection closed, will reconnect",
                    extra={"code": e.code, "reason": e.reason}
                )
                self._ws = None
                self._ws_connected = False
                # Loop will retry connection
                
            except Exception as e:
                logger.error(
                    "Unexpected error in WebSocket listener, will reconnect",
                    extra={"error": str(e)}
                )
                self._ws = None
                self._ws_connected = False
                await asyncio.sleep(5)  # Brief pause before reconnection

    async def _listen_events(self):
        """Legacy method - kept for backwards compatibility but deprecated"""
        logger.warning("_listen_events() is deprecated, use _listen_events_with_reconnect()")
        await self._listen_events_with_reconnect()

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific ARI event type. Use '*' for all events."""
        self._event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def disconnect(self):
        """Disconnect from ARI HTTP and WebSocket"""
        # Stop reconnection attempts
        self._should_reconnect = False
        
        # Cancel WebSocket listener
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None
        
        # Cancel reconnection task if running
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        
        # Close WebSocket
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            self._ws_connected = False
        
        # Close HTTP client
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        
        self._connected_ok = False

    async def is_connected(self) -> bool:
        """Check if both HTTP and WebSocket are connected"""
        return self._client is not None and self._connected_ok and self._ws_connected

    async def originate_call(
        self,
        phone_number: str,
        context: str,
        extension: str,
        priority: int,
        timeout: int,
        caller_id: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Originate a call using Asterisk ARI"""
        if self._client is None and not await self.connect():
            return {"success": False, "error": "Unable to connect to ARI"}

        channel_id = str(uuid.uuid4())
        params = {
            "endpoint": f"Local/{phone_number}@{context}",
            "app": settings.ari_app,
            "callerId": caller_id,
            "timeout": int(timeout / 1000) if timeout else None,
            "channelId": channel_id,
        }
        
        # Add variables if provided
        if variables:
            params["variables"] = json.dumps(variables)
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Attempt to originate with simple retry
        for attempt in range(3):
            try:
                resp = await self._client.post("/channels", params=params)
                if resp.status_code in (200, 202):
                    logger.info("ARI originate accepted", extra={"channel_id": channel_id})
                    return {
                        "success": True,
                        "call_id": channel_id,
                        "phone_number": phone_number,
                        "channel": channel_id,
                        "context": context,
                        "extension": extension,
                        "priority": priority,
                        "timeout": timeout,
                        "caller_id": caller_id,
                        "message": "Call originated via ARI",
                    }
                elif resp.status_code < 500:
                    # Client error, don't retry
                    logger.error("ARI originate failed", extra={"status": resp.status_code, "body": resp.text[:500]})
                    return {"success": False, "error": f"ARI error {resp.status_code}", "details": resp.text}
                    
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                logger.warning(f"ARI timeout on attempt {attempt + 1}", extra={"error": str(e)})
            except Exception as e:
                logger.error(f"ARI exception on attempt {attempt + 1}", extra={"error": str(e)})
                return {"success": False, "error": str(e)}
            
            # Wait before retry (exponential backoff)
            if attempt < 2:
                await asyncio.sleep(0.3 * (2 ** attempt))

        return {"success": False, "error": "ARI originate failed after retries"}

    async def hangup_channel(self, channel_id: str) -> Dict[str, Any]:
        """Hangup a channel via ARI"""
        if self._client is None:
            return {"success": False, "error": "Not connected to ARI"}
        
        try:
            resp = await self._client.delete(f"/channels/{channel_id}")
            if resp.status_code in (200, 204):
                logger.info("Channel hangup successful", extra={"channel_id": channel_id})
                return {"success": True}
            else:
                logger.error(
                    "Channel hangup failed",
                    extra={"channel_id": channel_id, "status": resp.status_code}
                )
                return {"success": False, "error": f"ARI error {resp.status_code}"}
        except Exception as e:
            logger.error("Exception during channel hangup", extra={"error": str(e)})
            return {"success": False, "error": str(e)}


# Global service instance
asterisk_service = AsteriskService()


async def get_asterisk_service() -> AsteriskService:
    return asterisk_service
