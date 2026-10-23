#!/usr/bin/env python3
"""Publish an episode's final.mp4 on the `media` branch and print its public URL.

Videos stay out of night-autopilot/main history; clones that fetch only night-autopilot stay small.
Usage: python3 tools/upload_media.py 005-some-slug   (reads output/<id>/final.mp4)
"""
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "https://github.com/tokbotxai-code/Night.git"
BRANCH = "media"
RAW = "https://raw.githubusercontent.com/tokbotxai-code/Night/media"


def git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def main():
    sid = sys.argv[1]
    src = ROOT / "output" / sid / "final.mp4"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    with tempfile.TemporaryDirectory() as tmp:
        for attempt in range(4):
            shutil.rmtree(tmp, ignore_errors=True)
            Path(tmp).mkdir()
            git("init", "-q", cwd=tmp)
            git("remote", "add", "origin", REMOTE, cwd=tmp)
            exists = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", BRANCH],
                                    cwd=tmp, capture_output=True).returncode == 0
            if exists:
                git("fetch", "-q", "--depth", "1", "origin", BRANCH, cwd=tmp)
                git("checkout", "-q", "-B", BRANCH, "FETCH_HEAD", cwd=tmp)
            else:
                git("checkout", "-q", "--orphan", BRANCH, cwd=tmp)
            (Path(tmp) / sid).mkdir(exist_ok=True)
            shutil.copy(src, Path(tmp) / sid / "final.mp4")
            git("add", f"{sid}/final.mp4", cwd=tmp)
            git("-c", "user.name=Night Stories", "-c", "user.email=noreply@nightstories.tv",
                "commit", "-qm", f"media {sid}", cwd=tmp)
            r = subprocess.run(["git", "push", "-q", "origin", f"HEAD:{BRANCH}"], cwd=tmp, capture_output=True, text=True)
            if r.returncode == 0:
                break
            print(f"push rejected, retry {attempt + 1}: {r.stderr.strip()[:200]}", file=sys.stderr)
            time.sleep(2 ** attempt)
        else:
            raise SystemExit("push to media branch failed")
    url = f"{RAW}/{sid}/final.mp4"
    for _ in range(30):  # raw.githubusercontent.com can lag a moment after a push
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as resp:
                if resp.status == 200:
                    print(url)
                    return
        except Exception:
            pass
        time.sleep(10)
    raise SystemExit(f"URL not reachable yet: {url}")


if __name__ == "__main__":
    main()
