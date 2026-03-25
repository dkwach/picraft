import json
import os
import time
from typing import Iterator

import requests
from mcpi import block
from mcpi.minecraft import Minecraft

HIT_ENDPOINT = os.environ.get("HIT_ENDPOINT", "http://127.0.0.1:5000/hit")
MINING_SWINGS = int(os.environ.get("MINING_SWINGS", "5"))
CHAT_PREFIX = "[mcontrol]"


def hit_stream(endpoint: str) -> Iterator[bool]:
    """Yield hit states streamed via Server-Sent Events."""
    headers = {"Accept": "text/event-stream"}
    while True:
        try:
            with requests.get(endpoint, stream=True, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    stripped = line.strip()
                    if not stripped or not stripped.startswith("data:"):
                        continue
                    payload = stripped[5:].strip()
                    if not payload:
                        continue
                    try:
                        message = json.loads(payload)
                    except json.JSONDecodeError:
                        print(f"Ignoring malformed payload: {payload}")
                        continue
                    yield bool(message.get("hit"))
            print("exit from for")
        except requests.RequestException as exc:
            print(f"Hit stream error: {exc}; retrying in 2s")
            time.sleep(2)


def build_block(mc: Minecraft) -> None:
    x, y, z = mc.player.getTilePos()
    mc.setBlocks(x + 1, y + 1, z + 1, x + 2, y + 2, z + 2, block.WOOD.id)


def post(mc: Minecraft, msg: str):
    print(msg)
    mc.postToChat(msg)


def main() -> None:
    endpoint = HIT_ENDPOINT
    mc = Minecraft.create()
    post(mc, f"{CHAT_PREFIX} listening on {endpoint}")

    last_state = False
    for hit_state in hit_stream(endpoint):
        if hit_state and not last_state:
            post(mc, f"{CHAT_PREFIX} Hit detected!")
            build_block(mc)
        last_state = hit_state


if __name__ == "__main__":
    main()
