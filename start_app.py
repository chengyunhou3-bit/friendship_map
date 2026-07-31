import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


app_file = Path(__file__).with_name("app.py")
website_url = "http://localhost:8501"


def website_is_running():
    try:
        urllib.request.urlopen(website_url, timeout=1)
        return True
    except (urllib.error.URLError, OSError):
        return False


if website_is_running():
    webbrowser.open(website_url)
    raise SystemExit


process = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.address",
        "localhost",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false"
    ]
)

for _ in range(30):
    if website_is_running():
        webbrowser.open(website_url)
        break

    time.sleep(0.2)

try:
    process.wait()
except KeyboardInterrupt:
    process.terminate()
