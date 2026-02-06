import base64
import requests

TIMEOUT = 8

def fetch_sub(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.text.strip()
    except:
        pass
    return ""

def decode_base64(data):
    try:
        missing = len(data) % 4
        if missing:
            data += "=" * (4 - missing)
        return base64.b64decode(data).decode("utf-8", errors="ignore")
    except:
        return ""

def main():
    with open("subs.txt", "r") as f:
        sources = [line.strip() for line in f if line.strip()]

    vless_links = []

    for url in sources:
        raw = fetch_sub(url)
        if not raw:
            continue

        decoded = decode_base64(raw)
        for line in decoded.splitlines():
            if line.startswith("vless://"):
                vless_links.append(line)

    # حذف تکراری‌ها
    vless_links = list(set(vless_links))

    # خروجی Base64
    final_text = "\n".join(vless_links)
    encoded = base64.b64encode(final_text.encode()).decode()

    with open("alive_base64.txt", "w") as f:
        f.write(encoded)

    print(f"Collected {len(vless_links)} VLESS configs")

if __name__ == "__main__":
    main()
