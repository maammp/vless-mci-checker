import asyncio
import base64
import json
import subprocess
import tempfile
import requests

TIMEOUT = 4
MAX_CONCURRENT = 15
TEST_URL = "http://www.gstatic.com/generate_204"

sem = asyncio.Semaphore(MAX_CONCURRENT)


# -----------------------------
# Safe Base64 decoder
# -----------------------------
def safe_decode(data):
    try:
        data = data.strip()

        # اگر subscription plain باشد
        if "vless://" in data:
            return data

        # فقط کاراکترهای مجاز Base64
        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r"
        cleaned = "".join(c for c in data if c in allowed)

        cleaned += "=" * (-len(cleaned) % 4)

        decoded = base64.b64decode(cleaned).decode("utf-8", errors="ignore")

        return decoded

    except Exception as e:
        print("Decode failed:", e)
        return ""


# -----------------------------
# Parse minimal VLESS
# -----------------------------
def parse_vless(link):
    try:
        body = link.replace("vless://", "")
        main, _, _ = body.partition("?")
        uuid, host = main.split("@")
        add, port = host.split(":")
        return {
            "id": uuid,
            "add": add,
            "port": port
        }
    except:
        return None


# -----------------------------
# Build Xray config
# -----------------------------
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


# -----------------------------
# Test single VLESS
# -----------------------------
async def test_vless(link, port):
    async with sem:
        try:
            v = parse_vless(link)
            if not v:
                return False

            cfg = build_config(v, port)

            with tempfile.NamedTemporaryFile("w", delete=False) as f:
                json.dump(cfg, f)
                cfg_path = f.name

            proc = subprocess.Popen(
                ["./xray", "run", "-config", cfg_path],
                stdout=subprocess.DEVNULL,
