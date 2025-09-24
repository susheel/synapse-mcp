"""Quick smoke test for Redis-backed session storage.

Run with REDIS_URL set to a reachable Redis instance.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from synapse_mcp.session_storage.redis_backend import RedisSessionStorage


class SmokeFailure(RuntimeError):
    pass


async def run_smoke(redis_url: str) -> None:
    storage = RedisSessionStorage(redis_url)

    print(f"[+] Connected to Redis at {redis_url}")

    await storage.set_user_token("smoke-user", "token-1", ttl_seconds=5)
    token = await storage.get_user_token("smoke-user")
    if token != "token-1":
        raise SmokeFailure(f"Expected token-1 immediately after set, got {token!r}")
    subject = await storage.find_user_by_token("token-1")
    if subject != "smoke-user":
        raise SmokeFailure(f"Token lookup returned {subject!r} instead of smoke-user")
    print("[+] Initial token written and retrieved")

    await storage.set_user_token("smoke-user", "token-2", ttl_seconds=5)
    token_after_swap = await storage.get_user_token("smoke-user")
    if token_after_swap != "token-2":
        raise SmokeFailure(f"Expected token-2 after swap, got {token_after_swap!r}")
    old_subject = await storage.find_user_by_token("token-1")
    if old_subject is not None:
        raise SmokeFailure("Old token still resolves to a subject after replacement")
    print("[+] Replacement token stored and previous token removed")

    print("[+] Waiting for TTL to expire...")
    await asyncio.sleep(6)

    expired_token = await storage.get_user_token("smoke-user")
    if expired_token is not None:
        raise SmokeFailure("Token still present after TTL expiry")
    expired_subject = await storage.find_user_by_token("token-2")
    if expired_subject is not None:
        raise SmokeFailure("find_user_by_token returned subject after TTL expiry")

    print("[+] Token expired as expected")

    await storage.cleanup_expired_tokens()
    remaining_subjects = await storage.get_all_user_subjects()
    if remaining_subjects:
        raise SmokeFailure(f"Cleanup left residual subjects: {remaining_subjects}")
    print("[+] Cleanup removed stale index entries")

    await storage.close()
    print("[✓] Redis session storage smoke test passed")


def main() -> int:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("ERROR: REDIS_URL environment variable not set", file=sys.stderr)
        return 2

    try:
        asyncio.run(run_smoke(redis_url))
    except SmokeFailure as exc:
        print(f"SMOKE FAILURE: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
