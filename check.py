import asyncio
import base64
import json
import subprocess
import tempfile
import requests

TIMEOUT = 4
MAX_CONCURRENT = 20
TEST_URL = "http://www.gstatic.com/generate_204"

sem = asyncio.Semaphore(MAX_CONCURRENT)

def decode_b64(data):
    data += "=" * (-len(data) % 4)
    return base64.b64decode(data).decode(errors="ignore")

def build_xray_config(vless, port):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": port,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": vless["add"],
                    "port": int(vless["port"]),
                    "users": [{
                        "id": vless["id"],
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": vless.get("streamSettings", {})
        }]
    }

def parse_vless(link):
    body = link.replace("vless://", "")
    main, _, params = body.partition("?")
    uuid, host = main.split("@")
    add, port = host.split(":")
    return {
        "id": uuid,
        "add": add,
        "port": port,
        "streamSettings": {}
    }

async def test_vless(link, port):
    async with sem:
        try:
            v = parse_vless(link)
            cfg = build_xray_config(v, port)

            with tempfile.NamedTemporaryFile("w", delete=False) as f:
                json.dump(cfg, f)
                cfg_path = f.name

            proc = subprocess.Popen(
                ["./xray", "run", "-config", cfg_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            await asyncio.sleep(0.7)

            r = requests.get(
                TEST_URL,
                proxies={
                    "http": f"socks5h://127.0.0.1:{port}",
                    "https": f"socks5h://127.0.0.1:{port}"
                },
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile)"
                }
            )

            proc.kill()
            return r.status_code == 204

        except:
            return False

async def main():
    with open("subs.txt") as f:
        subs = [l.strip() for l in f if l.strip()]

    vless_all = []
    for url in subs:
        raw = requests.get(url, timeout=10).text
        decoded = decode_b64(raw)
        for l in decoded.splitlines():
            if l.startswith("vless://"):
                vless_all.append(l)

    vless_all = list(set(vless_all))
    print("Total VLESS:", len(vless_all))

    tasks = []
    base_port = 20000

    for i, v in enumerate(vless_all):
        tasks.append(test_vless(v, base_port + i))

    results = await asyncio.gather(*tasks)

    alive = [v for v, ok in zip(vless_all, results) if ok]

    print("Alive:", len(alive))

    encoded = base64.b64encode("\n".join(alive).encode()).decode()
    with open("alive_base64.txt", "w") as f:
        f.write(encoded)

asyncio.run(main())
