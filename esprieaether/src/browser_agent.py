"""Browser agent — screenshot + extract web pages via curl + parse."""
import subprocess, re, json
from pathlib import Path

def screenshot(url: str, timeout: int = 60) -> dict:
    """Screenshot a page via headless chrome (if available) — falls back to text extract."""
    # Try chrome headless screenshot
    chrome_paths = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]
    for chrome in chrome_paths:
        if Path(chrome).exists():
            out = str(Path(__file__).parent.parent / "screenshot.png")
            try:
                subprocess.run(
                    [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                     f"--screenshot={out}", "--window-size=1280,720", url],
                    timeout=timeout, capture_output=True,
                )
                if Path(out).exists():
                    return {"ok": True, "screenshot": out, "url": url}
            except Exception:
                pass
    # fallback: text extract
    return extract(url)

def extract(url: str, timeout: int = 30) -> dict:
    """Extract page text via curl (strip HTML)."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "-m", str(timeout), "--ssl-no-revoke",
             "-A", "Mozilla/5.0", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        html = result.stdout
        # strip scripts/styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # strip tags
        text = re.sub(r"<[^>]+>", " ", html)
        # collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # extract title
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()
        return {
            "ok": True, "url": url, "title": title,
            "text": text[:3000], "length": len(text),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "extract"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
    if action == "screenshot":
        print(json.dumps(screenshot(url), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(extract(url), ensure_ascii=False, indent=2))
