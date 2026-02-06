import base64
import json
import subprocess
import asyncio
import aiohttp
import requests
from urllib.parse import parse_qs

XRAY = "./xray"
TEST_URL = "https://www.google.com/generate_204"
SOCKS_PORT = 10808
TIMEOUT = 3

def decode_sub(url):
    r = requests.get(url, timeout=10)
    t = r.text.strip()
    try:
        return base64.b64decode(t).decode().splitlines()
    except:
        return t.splitlines()

def parse_vless(link):
    link = link.replace("vless://", "")
    main = link.split("#")[0]
    user, rest = main.split("@")
    host_port, params = rest.split("?", 1)
    host, port = host_port.split(":")
    qs = parse_qs(params)

    return {
        "id": user,
        "host": host,
        "port": int(port),
        "security": qs.get("security", ["none"])[0],
        "sni": qs.get("sni", [""])[0]
    }

async def test_vless(link):
    cfg = parse_vless(link)

    xray_config = {
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": SOCKS_PORT,
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": cfg["host"],
                    "port": cfg["port"],
                    "users": [{
                        "id": cfg["id"],
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": {
                "security": cfg["security"],
                "tlsSettings": {
                    "serverName": cfg["sni"],
                    "allowInsecure": False
                }
            }
        }]
    }

    with open("cfg.json", "w") as f:
        json.dump(xray_config, f)

    proc = subprocess.Popen(
        [XRAY, "-config", "cfg.json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TEST_URL, timeout=TIMEOUT):
                return True
    except:
        return False
    finally:
        proc.kill()

async def main():
    subs = open("subscriptions.txt").read().splitlines()
    links = []

    for s in subs:
        links.extend(decode_sub(s))

    tasks = []
    vless_links = []

    for l in links:
        if l.startswith("vless://"):
            vless_links.append(l)
            tasks.append(test_vless(l))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    alive = [l for l, r in zip(vless_links, results) if r is True]

    encoded = base64.b64encode("\n".join(alive).encode()).decode()
    with open("alive_base64.txt", "w") as f:
        f.write(encoded)

asyncio.run(main())
