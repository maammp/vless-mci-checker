import asyncio
import base64
import json
import subprocess
import tempfile
import requests

TIMEOUT = 4
MAX_CONCURRENT = 10
TEST_URL = "http://www.gstatic.com/generate_204"

sem = asyncio.Semaphore(MAX_CONCURRENT)


def safe_decode(data):
    try:
        data = data.strip()

        if "vless://" in data:
            return data

        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r"
        cleaned = "".join(c for c in data if c in allowed)

        cleaned += "=" * (-len(cleaned) % 4)

        return base64.b64decode(cleaned).decode("utf-8", errors="ignore")

    except:
        return ""


def parse_vless(link):
    try:
        body = link.replace("vless://", "")
        main = body.split("?")[0]
        uuid, host = main.split("@")
        add, port = host.split(":")
        return {"id": uuid, "add": add, "port": port}
    except:
        return None


def build_config(vless, port):
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
            }
        }]
    }


async def test_vless(link, port):
    async with sem:
        try:
            v = parse_vless(link)
            if not v:
                return False

            config = build_config(v, port)

            with tempfile.NamedTemporaryFile("w", delete=False) as f:
                json.dump(config, f)
                config_path = f.name

            proc = subprocess.Popen(
                ["./xray", "run", "-config", config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            await asyncio.sleep(0.8)

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
        sources = [l.strip() for l in f if l.strip()]

    all_vless = []

    for url in sources:
        try:
            raw = requests.get(url, timeout=10).text
            decoded = safe_decode(raw)

            for line in decoded.splitlines():
                if line.startswith("vless://"):
                    all_vless.append(line)
        except:
            continue

    all_vless = list(set(all_vless))
    print("Total VLESS:", len(all_vless))

    base_port = 20000
    tasks = []

    for i, link in enumerate(all_vless):
        tasks.append(test_vless(link, base_port + i))

    results = await asyncio.gather(*tasks)

    alive = [v for v, ok in zip(all_vless, results) if ok]

    print("Alive:", len(alive))

    encoded = base64.b64encode("\n".join(alive).encode()).decode()

    with open("alive_base64.txt", "w") as f:
        f.write(encoded)


asyncio.run(main())
