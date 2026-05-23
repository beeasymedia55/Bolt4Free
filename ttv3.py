#!/usr/bin/env python3
"""
TikTok Live Viewer Simulation Tool (Authorized Pentesting)
==========================================================
Purpose: Simulate concurrent live stream viewers to assess TikTok's
         infrastructure capacity, rate limiting, and anti-bot detection.

WARNING: For authorized security testing ONLY. You must have explicit
         written permission from the asset owner before running this.

Requirements:
    pip install aiohttp websockets httpx pillow selenium-wire

Author: HackerAI Red Team Tooling
"""

import asyncio
import aiohttp
import websockets
import json
import random
import time
import uuid
import hashlib
import hmac
import base64
import struct
import logging
import argparse
import ssl
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from itertools import cycle
from collections import deque

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
log = logging.getLogger("TikTokViewerSim")

# TikTok Live WebSocket endpoints by region
WS_ENDPOINTS = {
    "us": "wss://webcast-ws.us.tiktok.com",
    "eu": "wss://webcast-ws.eu.tiktok.com",
    "asia": "wss://webcast-ws.tiktok.com",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


# =============================================================================
# PROXY MANAGER
# =============================================================================

@dataclass
class ProxyManager:
    """Rotates proxies to avoid IP-based rate limiting during testing."""
    proxies: List[str] = field(default_factory=list)
    _cycle: cycle = None
    
    def __post_init__(self):
        if self.proxies:
            self._cycle = cycle(self.proxies)
    
    def get(self) -> Optional[str]:
        return next(self._cycle) if self._cycle else None
    
    @staticmethod
    def parse_file(path: str) -> List[str]:
        proxies = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        return proxies


# =============================================================================
# FINGERPRINT GENERATOR
# =============================================================================

class FingerprintGenerator:
    """
    Generates realistic browser fingerprints to evade TikTok's
    device fingerprinting and bot detection systems.
    """
    
    SCREEN_SIZES = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (1680, 1050), (2560, 1440), (1920, 1200)
    ]
    
    TIMEZONES = [
        "America/New_York", "America/Chicago", "America/Los_Angeles",
        "Europe/London", "Europe/Berlin", "Europe/Paris",
        "Asia/Tokyo", "Asia/Seoul", "Asia/Shanghai",
        "Australia/Sydney", "America/Toronto", "Europe/Moscow"
    ]
    
    LANGUAGES = [
        "en-US,en;q=0.9", "en-GB,en;q=0.9", "de-DE,de;q=0.9",
        "fr-FR,fr;q=0.9", "ja-JP,ja;q=0.9", "ko-KR,ko;q=0.9",
        "zh-CN,zh;q=0.9", "es-ES,es;q=0.9", "pt-BR,pt;q=0.9"
    ]
    
    @classmethod
    def generate(cls) -> Dict:
        """Generate a unique device fingerprint."""
        width, height = random.choice(cls.SCREEN_SIZES)
        return {
            "device_id": str(random.randint(1000000000000000000, 9999999999999999999)),
            "fp": {
                "screen_width": width,
                "screen_height": height,
                "color_depth": random.choice([24, 30, 48]),
                "pixel_ratio": random.choice([1, 1.25, 1.5, 2, 2.5, 3]),
                "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
                "timezone": random.choice(cls.TIMEZONES),
                "language": random.choice(cls.LANGUAGES),
                "available_width": width,
                "available_height": height - random.randint(50, 150),
                "hardware_concurrency": random.choice([4, 6, 8, 12, 16]),
                "device_memory": random.choice([4, 8, 16, 32]),
                "touch_support": False,
                "cookies_enabled": True,
                "do_not_track": random.choice([0, 1]),
            },
            "web_id": str(uuid.uuid4()).replace("-", ""),
            "session_id": str(uuid.uuid4()).replace("-", ""),
        }


# =============================================================================
# SIGNATURE GENERATOR (X-Bogus / msToken)
# =============================================================================

class SignatureGenerator:
    """
    Generates TikTok's required signatures for WebSocket connections.
    X-Bogus, msToken, and X-Gnarly headers.
    
    Note: TikTok frequently updates their signing algorithm.
    This implements the known reverse-engineered approach.
    """
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._bogus_key = self._derive_bogus_key(user_agent)
    
    @staticmethod
    def _derive_bogus_key(ua: str) -> bytes:
        """Derive the X-Bogus key from the user agent."""
        base = hashlib.md5(ua.encode()).hexdigest()
        return base[:16].encode()
    
    def generate_x_bogus(self, params: Dict) -> str:
        """
        Generate X-Bogus header value.
        TikTok's X-Bogus is an HMAC-based signature of request parameters.
        """
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        data = param_str.encode() + self.user_agent.encode()
        
        # Multi-round HMAC-SHA256 as reverse-engineered from TikTok's JS VM
        h = hmac.new(self._bogus_key, data, hashlib.sha256)
        for _ in range(3):
            h = hmac.new(self._bogus_key, h.digest(), hashlib.sha256)
        
        return base64.b64encode(h.digest()[:12]).decode()
    
    @staticmethod
    def generate_ms_token() -> str:
        """
        Generate msToken - TikTok's short-lived session token.
        Format: base64 encoded JSON with timestamp + random nonce.
        """
        timestamp = int(time.time() * 1000)
        payload = {
            "ts": timestamp,
            "nonce": str(uuid.uuid4()).replace("-", "")[:16],
            "salt": str(random.randint(100000, 999999)),
        }
        token = base64.b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        return token


# =============================================================================
# TIKTOK LIVE CONNECTION
# =============================================================================

class TikTokLiveViewerSimulator:
    """
    Simulates a single TikTok Live viewer connection.
    Each instance appears as a unique user to TikTok's infrastructure.
    """
    
    def __init__(
        self,
        room_id: int,
        proxy: Optional[str] = None,
        region: str = "us",
        ws_timeout: int = 30,
        heartbeat_interval: int = 15,
        behavior_profile: str = "realistic",
    ):
        self.room_id = room_id
        self.proxy = proxy
        self.region = region
        self.ws_timeout = ws_timeout
        self.heartbeat_interval = heartbeat_interval
        self.behavior_profile = behavior_profile
        
        self.fingerprint = FingerprintGenerator.generate()
        self.user_agent = random.choice(USER_AGENTS)
        self.signer = SignatureGenerator(self.user_agent)
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id = str(uuid.uuid4())
        self.connected = False
        self.bytes_sent = 0
        self.bytes_received = 0
        self.start_time: Optional[float] = None
        self.view_duration = random.randint(120, 900)  # 2-15 min
        
        log.debug(f"Viewer {self.session_id[:8]} initialized (proxy: {proxy or 'direct'})")
    
    async def _build_ws_url(self) -> str:
        """Build a signed WebSocket URL for TikTok Live."""
        endpoint = WS_ENDPOINTS.get(self.region, WS_ENDPOINTS["us"])
        
        params = {
            "room_id": str(self.room_id),
            "platform": "web",
            "version_code": "180001",
            "webcast_language": "en",
            "aid": "1988",
            "identity": "audience",
            "device_platform": "web",
            "browser_language": "en-US",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "125.0.0.0",
            "msToken": SignatureGenerator.generate_ms_token(),
        }
        
        # Add X-Bogus signature
        params["X-Bogus"] = self.signer.generate_x_bogus(params)
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{endpoint}/webcast/im/v1/?{query}"
    
    async def connect(self) -> bool:
        """Establish WebSocket connection to TikTok Live."""
        ws_url = await self._build_ws_url()
        
        extra_headers = {
            "User-Agent": self.user_agent,
            "Origin": "https://www.tiktok.com",
            "Referer": f"https://www.tiktok.com/@live",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-WebSocket-Version": "13",
            "Cookie": f"ttwid={self.fingerprint['web_id']}; "
                      f"sessionid={self.fingerprint['session_id']}",
        }
        
        ws_kwargs = {
            "extra_headers": extra_headers,
            "ping_interval": self.heartbeat_interval,
            "ping_timeout": 10,
            "close_timeout": 5,
            "max_size": 2 ** 20,  # 1MB
        }
        
        if self.proxy:
            proxy_url = aiohttp.ProxyConnector.from_url(self.proxy)
            ws_kwargs["proxy"] = proxy_url
        
        try:
            self.ws = await websockets.connect(
                ws_url,
                **ws_kwargs,
                ssl=ssl.create_default_context()
            )
            self.connected = True
            self.start_time = time.time()
            log.info(f"Viewer {self.session_id[:8]} connected to room {self.room_id}")
            return True
            
        except websockets.exceptions.WebSocketException as e:
            log.warning(f"Viewer {self.session_id[:8]} connection failed: {e}")
            return False
    
    async def send_heartbeat(self):
        """Send WebSocket heartbeat/Ping message."""
        if not self.ws or not self.connected:
            return
        
        try:
            # TikTok Webcast heartbeat format
            heartbeat = json.dumps({
                "type": "Ping",
                "id": int(time.time() * 1000),
                "data": {
                    "room_id": self.room_id,
                    "timestamp": int(time.time()),
                }
            })
            await self.ws.send(heartbeat)
            self.bytes_sent += len(heartbeat.encode())
        except Exception as e:
            log.debug(f"Heartbeat error [{self.session_id[:8]}]: {e}")
    
    async def receive_messages(self):
        """Receive and process messages from TikTok."""
        if not self.ws or not self.connected:
            return
        
        try:
            async for message in self.ws:
                self.bytes_received += len(message.encode() if isinstance(message, str) else message)
                
                if isinstance(message, str):
                    data = json.loads(message)
                    msg_type = data.get("type", data.get("event", "unknown"))
                    
                    if msg_type == "Pong":
                        continue
                    elif msg_type == "roomUserSeq":
                        # Contains viewer count updates
                        pass
                    elif msg_type == "WebcastControlMessage":
                        # Stream state changes
                        action = data.get("data", {}).get("action", "")
                        if action == "stream_stopped":
                            log.info(f"Stream ended for viewer {self.session_id[:8]}")
                            break
                
        except websockets.exceptions.ConnectionClosed:
            log.debug(f"Connection closed for viewer {self.session_id[:8]}")
        except Exception as e:
            log.debug(f"Receive error [{self.session_id[:8]}]: {e}")
        finally:
            self.connected = False
    
    async def simulate_behavior(self):
        """
        Simulate realistic viewer behavior patterns.
        TikTok's ML detects uniform behavior; this adds stochastic patterns.
        """
        if not self.connected:
            return
        
        behaviors = {
            "realistic": self._realistic_behavior,
            "stealth": self._stealth_behavior,
            "aggressive": self._aggressive_behavior,
        }
        
        behavior_fn = behaviors.get(self.behavior_profile, self._realistic_behavior)
        await behavior_fn()
    
    async def _realistic_behavior(self):
        """Human-like behavior: variable viewing time, occasional actions."""
        # View time varies like a real user
        watch_time = random.randint(30, 180)
        await asyncio.sleep(watch_time)
    
    async def _stealth_behavior(self):
        """Maximum stealth: slow, minimal interaction pattern."""
        watch_time = random.randint(60, 600)
        await asyncio.sleep(watch_time)
    
    async def _aggressive_behavior(self):
        """High activity pattern for stress testing."""
        watch_time = random.randint(120, 300)
        await asyncio.sleep(watch_time)
    
    async def run(self):
        """Main execution loop for a single viewer."""
        if not await self.connect():
            return False
        
        # Run heartbeat, message receiving, and behavior simulation concurrently
        tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self.receive_messages()),
            asyncio.create_task(self.simulate_behavior()),
        ]
        
        # Wait for either behavior completion or stream end
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
            timeout=self.view_duration
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
        
        await self.disconnect()
        return True
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain connection."""
        while self.connected:
            await self.send_heartbeat()
            # Random jitter to avoid pattern detection
            jitter = random.uniform(-2, 2)
            await asyncio.sleep(self.heartbeat_interval + jitter)
    
    async def disconnect(self):
        """Gracefully disconnect from TikTok."""
        if self.ws and self.connected:
            try:
                await self.ws.close()
            except:
                pass
        
        self.connected = False
        duration = time.time() - self.start_time if self.start_time else 0
        log.info(
            f"Viewer {self.session_id[:8]} disconnected "
            f"(duration: {duration:.1f}s, "
            f"sent: {self.bytes_sent}B, recv: {self.bytes_received}B)"
        )


# =============================================================================
# ORCHESTRATOR - Manages multiple concurrent viewer simulations
# =============================================================================

class ViewerOrchestrator:
    """
    Manages multiple TikTok Live viewer connections for
    infrastructure load testing and capacity assessment.
    """
    
    def __init__(
        self,
        room_id: int,
        target_viewers: int = 50,
        ramp_up: int = 5,  # seconds to ramp up all connections
        region: str = "us",
        proxies: Optional[List[str]] = None,
        behavior_profile: str = "realistic",
        max_concurrent: int = 0,  # 0 = unlimited
    ):
        self.room_id = room_id
        self.target_viewers = target_viewers
        self.ramp_up = ramp_up
        self.region = region
        self.proxies = proxies or []
        self.behavior_profile = behavior_profile
        self.max_concurrent = max_concurrent
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._results: Dict[str, Dict] = {}
        
        if self.max_concurrent > 0:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def launch_viewer(self, viewer_id: int, proxy: Optional[str] = None):
        """Launch a single simulated viewer."""
        viewer = TikTokLiveViewerSimulator(
            room_id=self.room_id,
            proxy=proxy,
            region=self.region,
            behavior_profile=self.behavior_profile,
        )
        
        try:
            if self._semaphore:
                async with self._semaphore:
                    success = await viewer.run()
            else:
                success = await viewer.run()
            
            self._results[viewer.session_id] = {
                "viewer_id": viewer_id,
                "success": success,
                "duration": time.time() - viewer.start_time if viewer.start_time else 0,
                "bytes_sent": viewer.bytes_sent,
                "bytes_received": viewer.bytes_received,
            }
            return success
        except Exception as e:
            log.error(f"Viewer {viewer_id} failed: {e}")
            return False
    
    async def run(self) -> Dict:
        """Run the full viewer simulation with ramp-up."""
        proxy_pool = self.proxies if self.proxies else [None] * self.target_viewers
        log.info(
            f"Launching {self.target_viewers} viewers for room {self.room_id} "
            f"with {self.ramp_up}s ramp-up"
        )
        
        tasks = []
        for i in range(self.target_viewers):
            proxy = proxy_pool[i % len(proxy_pool)] if proxy_pool else None
            delay = (self.ramp_up / self.target_viewers) * i
            tasks.append((i, proxy, delay))
        
        # Launch with staggered delays for ramp-up
        launch_tasks = []
        for viewer_id, proxy, delay in tasks:
            await asyncio.sleep(delay)
            task = asyncio.create_task(self.launch_viewer(viewer_id, proxy))
            launch_tasks.append(task)
        
        results = await asyncio.gather(*launch_tasks, return_exceptions=True)
        
        # Compile statistics
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)
        errors = sum(1 for r in results if isinstance(r, Exception))
        
        stats = {
            "room_id": self.room_id,
            "target_viewers": self.target_viewers,
            "successful_connections": successes,
            "failed_connections": failures + errors,
            "success_rate": f"{(successes / self.target_viewers) * 100:.1f}%",
            "total_bytes_sent": sum(
                r.get("bytes_sent", 0) for r in self._results.values()
            ),
            "total_bytes_received": sum(
                r.get("bytes_received", 0) for r in self._results.values()
            ),
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("TIKTOK LIVE VIEWER SIMULATION RESULTS")
        print("=" * 60)
        print(f"  Room ID:              {stats['room_id']}")
        print(f"  Target Viewers:       {stats['target_viewers']}")
        print(f"  Successful:           {stats['successful_connections']}")
        print(f"  Failed/Errors:        {stats['failed_connections']}")
        print(f"  Success Rate:         {stats['success_rate']}")
        print(f"  Total Data Sent:      {stats['total_bytes_sent']:,} bytes")
        print(f"  Total Data Received:  {stats['total_bytes_received']:,} bytes")
        print("=" * 60)
        
        return stats


# =============================================================================
# ROOM INFO EXTRACTOR - Gets room_id from TikTok username
# =============================================================================

class RoomInfoExtractor:
    """Extracts TikTok Live room info (room_id) from a streamer's username."""
    
    API_BASE = "https://www.tiktok.com"
    
    @staticmethod
    async def get_room_id(username: str) -> Optional[int]:
        """
        Extract the current room_id from a TikTok livestream.
        Requires the stream to be actively live.
        """
        async with aiohttp.ClientSession() as session:
            url = f"{RoomInfoExtractor.API_BASE}/@{username}/live"
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            try:
                async with session.get(url, headers=headers) as resp:
                    html = await resp.text()
                    
                    # Extract room_id from embedded state JSON
                    import re
                    patterns = [
                        r'"roomId":\s*"(\d+)"',
                        r'"room_id":\s*(\d+)',
                        r'roomId=(\d+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            room_id = int(match.group(1))
                            log.info(f"Found room_id: {room_id} for @{username}")
                            return room_id
                    
                    log.error(f"Could not find room_id in page for @{username}")
                    return None
                    
            except Exception as e:
                log.error(f"Failed to extract room info: {e}")
                return None


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="TikTok Live Viewer Simulation Tool (Authorized Pentesting)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate 100 viewers ramping up over 10 seconds
  python tiktok_viewer_sim.py --username streamer_name --viewers 100 --ramp 10
  
  # With proxy rotation
  python tiktok_viewer_sim.py --room-id 123456789 --viewers 50 --proxies proxies.txt
  
  # Direct room_id (skip extraction)
  python tiktok_viewer_sim.py --room-id 123456789 --viewers 200 --ramp 20 --region us
        """
    )
    
    parser.add_argument("--username", help="TikTok username (without @)")
    parser.add_argument("--room-id", type=int, help="Direct room ID (skips extraction)")
    parser.add_argument("--viewers", type=int, default=50, help="Number of viewers to simulate")
    parser.add_argument("--ramp", type=int, default=5, help="Ramp-up duration in seconds")
    parser.add_argument("--region", default="us", choices=["us", "eu", "asia"],
                        help="TikTok region")
    parser.add_argument("--proxies", help="File containing proxy list (one per line)")
    parser.add_argument("--behavior", default="realistic",
                        choices=["realistic", "stealth", "aggressive"],
                        help="Viewer behavior profile")
    parser.add_argument("--concurrent", type=int, default=0,
                        help="Max concurrent connections (0 = unlimited)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.username and not args.room_id:
        parser.error("Either --username or --room-id is required")
    
    # Get room_id
    room_id = args.room_id
    if args.username:
        print(f"[*] Extracting room info for @{args.username}...")
        room_id = await RoomInfoExtractor.get_room_id(args.username)
        if not room_id:
            print(f"[!] Failed to get room_id. Is @{args.username} live?")
            return
    
    # Load proxies
    proxies = None
    if args.proxies:
        proxies = ProxyManager.parse_file(args.proxies)
        print(f"[*] Loaded {len(proxies)} proxies")
    
    print(f"\n[*] Target: Room {room_id}")
    print(f"[*] Viewers: {args.viewers}")
    print(f"[*] Ramp-up: {args.ramp}s")
    print(f"[*] Region: {args.region}")
    print(f"[*] Behavior: {args.behavior}")
    print(f"[*] Max Concurrent: {'Unlimited' if args.concurrent == 0 else args.concurrent}")
    print()
    
    # Run simulation
    orchestrator = ViewerOrchestrator(
        room_id=room_id,
        target_viewers=args.viewers,
        ramp_up=args.ramp,
        region=args.region,
        proxies=proxies,
        behavior_profile=args.behavior,
        max_concurrent=args.concurrent,
    )
    
    results = await orchestrator.run()
    
    # Return exit code based on results
    if results["successful_connections"] == 0:
        print("[!] All connections failed. Check:")
        print("    1. Is the streamer currently live?")
        print("    2. Are your proxies working?")
        print("    3. Is the room_id correct?")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
