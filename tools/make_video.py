#!/usr/bin/env python3
"""Render a 9:16 faceless horror short from a story.json.

Pipeline: free neural TTS (edge-tts) -> AI backgrounds (Pollinations, free, no key)
-> Ken Burns + grade + grain + flicker -> word-synced captions + SMS/title overlays
-> procedural SFX mix -> loudness-normalized MP4 (1080x1920, 30 fps, H.264/AAC).

Usage:
  python3 tools/make_video.py stories/001-mom-forgot-keys/story.json
  python3 tools/make_video.py STORY --preview        # 540x960, fast check
  python3 tools/make_video.py STORY --no-ai-images   # offline placeholder backgrounds
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sfx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
W, H, FPS = 1080, 1920, 30
SR = sfx.SR
MIN_LEN, MAX_LEN = 61.0, 180.0

CA_FILE = next((p for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE"),
                            "/root/.ccr/ca-bundle.crt") if p and os.path.exists(p)), None)


def log(*a):
    print("[make_video]", *a, flush=True)


def h(s, n=12):
    return hashlib.sha1(s.encode()).hexdigest()[:n]


def norm_word(w):
    return "".join(c for c in w.lower() if c.isalnum())


# ------------------------------------------------------------------ fonts

def font(name, size):
    cands = {
        "display": [FONT_DIR / "Anton-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
        "ui_bold": ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_DIR / "Anton-Regular.ttf"],
        "ui": ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_DIR / "Anton-Regular.ttf"],
    }[name]
    for c in cands:
        if Path(c).exists():
            return ImageFont.truetype(str(c), size)
    return ImageFont.load_default()


# ------------------------------------------------------------------ TTS

KOKORO_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
_kokoro = None


def kokoro_tts(text, voice, speed, cache):
    """Kokoro (Apache-2.0) narration; word times estimated from text (no native boundaries)."""
    global _kokoro
    key = h(f"kokoro|{text}|{voice}|{speed}")
    wav, meta = cache / f"tts_{key}.wav", cache / f"tts_{key}.json"
    if not (wav.exists() and meta.exists()):
        import soundfile as sf
        if _kokoro is None:
            from kokoro_onnx import Kokoro
            KOKORO_DIR.mkdir(parents=True, exist_ok=True)
            for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
                if not (KOKORO_DIR / f).exists():
                    log(f"downloading {f}")
                    subprocess.run(["curl", "-sSL", "--retry", "4", "-o", str(KOKORO_DIR / f), KOKORO_URL + f], check=True)
            _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
        audio, sr = _kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        sf.write(str(wav), audio, sr)
        # estimate word timing over the voiced span: weight = letters, plus pauses after punctuation
        a = np.abs(audio)
        nz = np.nonzero(a > 0.01)[0]
        t0, t1 = (nz[0] / sr, nz[-1] / sr) if len(nz) else (0.0, len(audio) / sr)
        toks = text.split()
        weights = [max(2, sum(c.isalnum() for c in w)) + (6 if w[-1] in ".?!:" else 3 if w[-1] in ",;" else 0) for w in toks]
        unit = (t1 - t0) / max(1, sum(weights))
        words, cur = [], t0
        for w, wt in zip(toks, weights):
            letters = max(2, sum(c.isalnum() for c in w)) * unit
            words.append((cur, letters, w.strip('.,!?:;"')))
            cur += wt * unit
        meta.write_text(json.dumps(words))
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(pcm, dtype=np.float32).copy(), [tuple(w) for w in json.loads(meta.read_text())]


def tts(text, voice, rate, pitch, cache):
    """Return (mono float32 audio, [(start_s, dur_s, word)])."""
    key = h(f"{text}|{voice}|{rate}|{pitch}")
    mp3, meta = cache / f"tts_{key}.mp3", cache / f"tts_{key}.json"
    if not (mp3.exists() and meta.exists()):
        import certifi
        import edge_tts
        if CA_FILE:  # agent/corporate proxies re-sign TLS; edge-tts pins certifi
            certifi.where = lambda: CA_FILE
            import edge_tts.communicate as ec
            if hasattr(ec, "certifi"):
                ec.certifi.where = lambda: CA_FILE

        async def run():
            com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary",
                                       proxy=os.environ.get("HTTPS_PROXY") or None)
            words, buf = [], bytearray()
            async for ch in com.stream():
                if ch["type"] == "audio":
                    buf += ch["data"]
                elif ch["type"] == "WordBoundary":
                    words.append((ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]))
            return bytes(buf), words

        for attempt in range(4):
            try:
                audio, words = asyncio.run(run())
                break
            except Exception as e:  # network hiccups
                log(f"TTS retry {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
        else:
            raise SystemExit("TTS failed after retries")
        mp3.write_bytes(audio)
        meta.write_text(json.dumps(words))
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(pcm, dtype=np.float32).copy(), [tuple(w) for w in json.loads(meta.read_text())]


# ------------------------------------------------------------------ images

def fetch_image(prompt, cache, offline):
    key = h(prompt)
    path = cache / f"img_{key}.jpg"
    if path.exists():
        return Image.open(path).convert("RGB")
    if not offline:
        seed = int(key[:6], 16)
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
               f"?width=768&height=1344&nologo=true&seed={seed}&model=flux")
        ctx = ssl.create_default_context(cafile=CA_FILE) if CA_FILE else None
        for attempt in range(6):
            try:
                with urllib.request.urlopen(url, timeout=180, context=ctx) as r:
                    data = r.read()
                path.write_bytes(data)
                img = Image.open(path).convert("RGB")
                log(f"image ok {key} {img.size}")
                return img
            except Exception as e:  # anonymous tier answers 402/429 when rate-limited
                log(f"image retry {attempt + 1} ({key}): {e}")
                time.sleep(12 * (attempt + 1))
        log(f"image FAILED, using placeholder: {prompt[:60]}")
    # offline / failed placeholder: dark gradient with a soft light source
    yy, xx = np.mgrid[0:1344, 0:768]
    seed = int(key[:6], 16)
    cx, cy = 200 + seed % 400, 300 + seed % 700
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    v = np.clip(90 * np.exp(-d / 380), 0, 255)
    arr = np.stack([v * 0.7, v * 0.85, v], -1).astype(np.uint8)
    return Image.fromarray(arr)


def grade(img, size):
    """Crop watermark strip, cover-fit to size, horror grade, vignette."""
    w, h_ = img.size
    img = img.crop((0, 0, w, int(h_ * 0.93)))  # Pollinations badge sits bottom-right
    tw, th = size
    s = max(tw / img.width, th / img.height)
    img = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    l, t = (img.width - tw) // 2, (img.height - th) // 2
    img = img.crop((l, t, l + tw, t + th))
    img = ImageEnhance.Color(img).enhance(0.45)
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Brightness(img).enhance(0.8)
    a = np.asarray(img).astype(np.float32)
    a *= np.array([0.92, 1.0, 1.08])  # cold teal-blue cast
    yy, xx = np.mgrid[0:th, 0:tw]
    r = np.sqrt(((xx - tw / 2) / (tw / 2)) ** 2 + ((yy - th / 2) / (th / 2)) ** 2)
    a *= np.clip(1.15 - 0.55 * r ** 1.8, 0.25, 1.0)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ overlays (RGBA numpy)

def text_block(text, fnt, max_w, fill=(255, 255, 255), stroke=8, stroke_fill=(0, 0, 0), spacing=10, align="center"):
    words, lines, cur = text.split(), [], ""
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for w_ in words:
        test = (cur + " " + w_).strip()
        if d.textlength(test, font=fnt) + 2 * stroke > max_w and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = test
    lines.append(cur)
    asc, desc = fnt.getmetrics()
    lh = asc + desc + spacing
    bw = int(max(d.textlength(l_, font=fnt) for l_ in lines) + 2 * stroke + 4)
    img = Image.new("RGBA", (bw, lh * len(lines) + 2 * stroke), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for i, l_ in enumerate(lines):
        lw = dr.textlength(l_, font=fnt)
        x = (bw - lw) / 2 if align == "center" else stroke
        dr.text((x, stroke + i * lh), l_, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def caption_img(words, active, s):
    """One caption chunk, active word highlighted, TikTok style."""
    fnt = font("display", int(96 * s))
    stroke = int(9 * s)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    space = d.textlength(" ", font=fnt)
    widths = [d.textlength(w_, font=fnt) for w_ in words]
    max_w = (W - 160) * s
    lines, cur, cw = [], [], 0
    for i, wd in enumerate(widths):
        if cur and cw + space + wd > max_w:
            lines.append(cur)
            cur, cw = [], 0
        cw += (space if cur else 0) + wd
        cur.append(i)
    lines.append(cur)
    asc, desc = fnt.getmetrics()
    lh = asc + desc
    img = Image.new("RGBA", (int(max_w + 2 * stroke), lh * len(lines) + 2 * stroke), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for li, idxs in enumerate(lines):
        lw = sum(widths[i] for i in idxs) + space * (len(idxs) - 1)
        x = (img.width - lw) / 2
        for i in idxs:
            col = (255, 214, 0) if i == active else (255, 255, 255)
            dr.text((x, stroke + li * lh), words[i], font=fnt, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))
            x += widths[i] + space
    return img


def heart(dr, x, y, size, fill):
    r = size / 4
    dr.ellipse((x, y, x + 2 * r, y + 2 * r), fill=fill)
    dr.ellipse((x + 2 * r, y, x + 4 * r, y + 2 * r), fill=fill)
    dr.polygon([(x + 0.2 * r, y + 1.45 * r), (x + 3.8 * r, y + 1.45 * r), (x + 2 * r, y + 3.6 * r)], fill=fill)


def sms_img(sender, text, tm, s, app="MESSAGES", heart_icon=True):
    """iOS-style lock-screen notification banner."""
    cw = int(960 * s)
    pad = int(30 * s)
    f_small, f_name, f_body = font("ui", int(30 * s)), font("ui_bold", int(42 * s)), font("ui", int(42 * s))
    body = text_block(text, f_body, cw - 2 * pad - int(110 * s), stroke=0, spacing=int(8 * s), align="left")
    ch = int(150 * s) + body.height
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=int(40 * s), fill=(28, 28, 32, 235))
    ic = int(80 * s)
    dr.rounded_rectangle((pad, pad, pad + ic, pad + ic), radius=int(18 * s), fill=(52, 199, 89, 255))
    dr.ellipse((pad + ic * .2, pad + ic * .25, pad + ic * .8, pad + ic * .72), fill=(255, 255, 255))
    dr.polygon([(pad + ic * .3, pad + ic * .62), (pad + ic * .25, pad + ic * .8), (pad + ic * .45, pad + ic * .68)],
               fill=(255, 255, 255))
    tx = pad + ic + int(26 * s)
    dr.text((tx, pad - int(2 * s)), app, font=f_small, fill=(160, 160, 168))
    tw = dr.textlength(tm, font=f_small)
    dr.text((cw - pad - tw, pad - int(2 * s)), tm, font=f_small, fill=(160, 160, 168))
    dr.text((tx, pad + int(38 * s)), sender, font=f_name, fill=(255, 255, 255))
    nw = dr.textlength(sender + " ", font=f_name)
    if heart_icon:
        heart(dr, tx + nw, pad + int(50 * s), int(34 * s), (255, 59, 48))
    img.alpha_composite(body, (tx, pad + int(96 * s)))
    return img


def title_img(text, s, size=104, color=(255, 255, 255)):
    return text_block(text, font("display", int(size * s)), int((W - 140) * s), fill=color, stroke=int(9 * s))


def hook_img(text, s):
    t = text_block(text, font("display", int(78 * s)), int((W - 180) * s), stroke=0)
    pad = int(28 * s)
    img = Image.new("RGBA", (t.width + 2 * pad, t.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=int(22 * s),
                                          fill=(0, 0, 0, 185))
    img.alpha_composite(t, (pad, pad))
    return img


def composite(frame, ov, x, y, alpha=1.0):
    """Alpha-blend RGBA numpy ov onto float32 frame at (x, y)."""
    fh, fw = frame.shape[:2]
    oh, ow = ov.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(fw, x + ow), min(fh, y + oh)
    if x0 >= x1 or y0 >= y1:
        return
    o = ov[y0 - y:y1 - y, x0 - x:x1 - x]
    a = o[..., 3:4] * (alpha / 255.0)
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + o[..., :3] * a


# ------------------------------------------------------------------ build

def build(story_path, out_root, preview, offline, allow_any_length):
    story = json.loads(Path(story_path).read_text())
    sid = story["id"]
    out = Path(out_root) / sid
    cache = out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    s = 0.5 if preview else 1.0
    fw, fh = int(W * s), int(H * s)

    # 1) narration + timeline
    t = 0.0
    scenes = []
    for sc in story["scenes"]:
        start = t
        narr_start = start + sc.get("pre", 0.0)
        audio, words = (np.zeros(0, np.float32), [])
        if sc.get("narration"):
            if story.get("tts") == "kokoro":
                audio, words = kokoro_tts(sc["narration"], story["voice"], story.get("speed", 1.0), cache)
            else:
                audio, words = tts(sc["narration"], story["voice"], story.get("rate", "+0%"),
                                   story.get("pitch", "+0Hz"), cache)
            # trim edge-tts leading/trailing silence so pacing is controlled by "post"
            nz = np.nonzero(np.abs(audio) > 0.01)[0]
            if len(nz):
                lead = max(0, nz[0] - int(0.03 * SR))
                audio = audio[lead: nz[-1] + int(0.05 * SR)]
                words = [(a - lead / SR, d, w_) for a, d, w_ in words]
        narr_end = narr_start + len(audio) / SR
        end = narr_end + sc.get("post", 0.0)
        scenes.append(dict(cfg=sc, start=start, narr_start=narr_start, narr_end=narr_end, end=end,
                           audio=audio, words=[(narr_start + a, d, w_) for a, d, w_ in words]))
        t = end
    total = t
    log(f"duration {total:.2f}s")
    if not allow_any_length and not (MIN_LEN <= total <= MAX_LEN):
        raise SystemExit(f"Duration {total:.1f}s outside {MIN_LEN}-{MAX_LEN}s. Edit narration/pauses "
                         f"or pass --allow-any-length.")

    def resolve(scn, spec, key_at="at", key_word="at_word"):
        if key_word in spec:
            target = norm_word(spec[key_word])
            for a, _, w_ in scn["words"]:
                if norm_word(w_) == target:
                    return a
            raise SystemExit(f"at_word '{spec[key_word]}' not found in: {scn['cfg']['narration']}")
        v = spec.get(key_at, 0.0)
        if v == "end":
            return scn["narr_end"]
        return scn["start"] + float(v)

    def resolve_until(scn, spec, at):
        u = spec.get("until")
        if u is None:
            return None
        if u == "end":
            return scn["end"]
        return at + float(u)

    # 2) audio mix
    n = int((total + 0.5) * SR)
    mix = np.zeros(n, np.float32)

    def place(sig, at, gain):
        i = int(at * SR)
        e = min(n, i + len(sig))
        if i < n:
            mix[i:e] += sig[: e - i] * gain

    mix += sfx.room_tone(n / SR)[:n] * 0.035
    hits = []
    for scn in scenes:
        if len(scn["audio"]):
            v = sfx.reverb(scn["audio"], 0.7, 0.1, 4000)
            place(v / (np.max(np.abs(v)) + 1e-9) * 0.9, scn["narr_start"], 1.0)
        for fx in scn["cfg"].get("sfx", []):
            at = resolve(scn, fx)
            until = resolve_until(scn, fx, at)
            dur = max(0.3, (until - at) if until else 2.0)
            sig = sfx.EFFECTS[fx["type"]](dur)
            place(sig, at, sfx.DEFAULT_GAIN[fx["type"]] * fx.get("gain", 1.0))
            if fx["type"] in ("hit", "knock3"):
                hits.append(at)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    raw_wav, wav = cache / "mix_raw.wav", out / "audio.wav"
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw_wav), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", str(wav)], check=True)

    # 3) shots
    margin = 1.3  # oversize for zoom/pan headroom
    shots = []
    for si, scn in enumerate(scenes):
        cfg_shots = scn["cfg"]["shots"]
        span = (scn["end"] - scn["start"]) / len(cfg_shots)
        for k, sh in enumerate(cfg_shots):
            a = scn["start"] + k * span
            img = None
            if sh.get("image_file"):  # e.g. a Canva export saved in the story folder
                src = Image.open(Path(story_path).parent / sh["image_file"]).convert("RGB")
                img = np.asarray(grade(src, (int(fw * margin), int(fh * margin))))
            elif not sh.get("black"):
                src = fetch_image(sh["prompt"] + ", " + story.get("style_prompt", ""), cache, offline)
                img = np.asarray(grade(src, (int(fw * margin), int(fh * margin))))
            shots.append(dict(a=a, b=a + span, img=img, motion=sh.get("motion", "zoom_in"),
                              flicker=scn["cfg"].get("flicker", False), scene=si))

    # 4) overlays
    overlays = []  # (a, b, rgba ndarray, x, y)

    def add(img, a, b, x=None, y=0):
        arr = np.asarray(img)
        overlays.append((a, b, arr, (fw - arr.shape[1]) // 2 if x is None else x, y))

    hook_scenes = story.get("hook_scenes", 2)
    if story.get("hook_text"):
        add(hook_img(story["hook_text"], s), 0.0, scenes[min(hook_scenes, len(scenes)) - 1]["end"], y=int(190 * s))
    for scn in scenes:
        for ov in scn["cfg"].get("overlays", []):
            a = resolve(scn, ov)
            b = resolve_until(scn, ov, a) or scn["end"]
            if ov["kind"] == "sms":
                slot = ov.get("slot")
                y = int((330 + 235 * slot) * s) if slot is not None else int(470 * s)
                add(sms_img(ov.get("sender", "Mom"), ov["text"], ov.get("time", "3:12 AM"), s,
                            ov.get("app", "MESSAGES"), ov.get("heart", True)), a, b, y=y)
            elif ov["kind"] == "title":
                im = title_img(ov["text"], s)
                black = scn["cfg"]["shots"][0].get("black")
                add(im, a, b, y=int((720 if black else 330) * s))
            elif ov["kind"] == "choice":
                add(title_img(ov["text"], s, 92, (255, 214, 0)), a, b, y=int(1060 * s))

    # 5) captions (word-synced chunks)
    caps = []
    for scn in scenes:
        if scn["cfg"].get("captions", True) is False or not scn["words"]:
            continue
        text = scn["cfg"]["narration"]
        cursor, toks = 0, []
        for a, d, w_ in scn["words"]:
            i = text.find(w_, cursor)
            if i < 0:
                toks.append((a, d, w_, False))
                continue
            j = i + len(w_)
            while j < len(text) and not text[j].isspace():
                j += 1
            raw = text[i:j]
            cursor = j
            toks.append((a, d, raw.strip(".,!?:;\"").upper(), raw[-1:] in ".,!?:;"))
        chunk = []
        for tok in toks:
            chunk.append(tok)
            if len(chunk) == 3 or tok[3]:
                caps.append(chunk)
                chunk = []
        if chunk:
            caps.append(chunk)
    cap_frames = []  # (a, b, [(wa, wb, img)])
    for ci, ch in enumerate(caps):
        a = ch[0][0]
        last_end = ch[-1][0] + ch[-1][1]
        nxt = caps[ci + 1][0][0] if ci + 1 < len(caps) else total
        b = min(nxt, last_end + 0.6)
        words = [w_ for _, _, w_, _ in ch]
        variants = []
        for k, (wa, wd, _, _) in enumerate(ch):
            wb = ch[k + 1][0] if k + 1 < len(ch) else b
            variants.append((wa, wb, np.asarray(caption_img(words, k, s))))
        cap_frames.append((a, b, variants))
    cap_y = int(1180 * s)

    # 6) render frames
    rng = np.random.default_rng(7)
    # half-res grain upscaled: reads as film grain and keeps the bitrate sane
    grains = [np.asarray(Image.fromarray(rng.normal(128, 9, (fh // 2, fw // 2)).clip(0, 255).astype(np.uint8))
                         .resize((fw, fh), Image.BILINEAR)).astype(np.float32)[..., None] - 128 for _ in range(6)]
    mp4 = out / ("preview.mp4" if preview else "final.mp4")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{fw}x{fh}", "-r", str(FPS),
         "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
         "-crf", "24", "-maxrate", "2M", "-bufsize", "4M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
         "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    nframes = int(total * FPS)
    flick = np.convolve(rng.normal(0, 1, nframes + 20), np.ones(4) / 4, mode="same")
    cover_ms = story.get("post", {}).get("cover_ms", 1500)
    t0 = time.time()
    for fi in range(nframes):
        tt = fi / FPS
        sh = next((x for x in shots if x["a"] <= tt < x["b"]), shots[-1])
        p = (tt - sh["a"]) / max(1e-6, sh["b"] - sh["a"])
        if sh["img"] is None:
            frame = np.zeros((fh, fw, 3), np.float32)
        else:
            src = sh["img"]
            sh_h, sh_w = src.shape[:2]
            m = sh["motion"]
            ease = 0.5 - 0.5 * math.cos(math.pi * p)
            z = {"zoom_in": 1.0 + 0.12 * ease, "slow_zoom_in": 1.0 + 0.28 * p ** 1.5,
                 "zoom_out": 1.12 - 0.12 * ease, "pan_right": 1.08, "shake": 1.1}.get(m, 1.0 + 0.1 * ease)
            cw_, ch_ = sh_w / margin / z, sh_h / margin / z
            cx, cy = sh_w / 2, sh_h / 2
            if m == "pan_right":
                cx = sh_w / 2 - (sh_w - cw_) * 0.35 + (sh_w - cw_) * 0.7 * ease
            if m == "shake":
                cx += rng.normal(0, 5 * s)
                cy += rng.normal(0, 5 * s)
            for ht in hits:  # impact shake
                if 0 <= tt - ht < 0.45:
                    k = (1 - (tt - ht) / 0.45) * 14 * s
                    cx += rng.normal(0, k)
                    cy += rng.normal(0, k)
            box = (cx - cw_ / 2, cy - ch_ / 2, cx + cw_ / 2, cy + ch_ / 2)
            frame = np.asarray(Image.fromarray(src).resize((fw, fh), Image.BILINEAR, box=box)).astype(np.float32)
            if sh["flicker"]:
                frame *= 0.88 + 0.1 * math.tanh(flick[fi]) + (-0.25 if rng.random() < 0.02 else 0)
            fade_in = min(1.0, (tt - sh["a"]) / 0.12) if sh["a"] > 0 else 1.0
            frame *= fade_in
        frame += grains[fi % len(grains)]
        for a, b, arr, x, y in overlays:
            if a <= tt < b:
                k = min(1.0, (tt - a) / 0.12)
                composite(frame, arr, x, y + int((1 - k) * 18 * s), k)
        for a, b, variants in cap_frames:
            if a <= tt < b:
                arr = next((v for wa, wb, v in variants if wa <= tt < wb), variants[-1][2])
                composite(frame, arr, (fw - arr.shape[1]) // 2, cap_y)
                break
        out8 = np.clip(frame, 0, 255).astype(np.uint8)
        enc.stdin.write(out8.tobytes())
        if fi == int(cover_ms / 1000 * FPS):
            Image.fromarray(out8).save(out / "cover.jpg", quality=92)
        if fi % (FPS * 10) == 0:
            log(f"frame {fi}/{nframes} ({time.time() - t0:.0f}s)")
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("ffmpeg encode failed")

    # 7) side files
    def ts(x):
        return f"{int(x // 3600):02}:{int(x % 3600 // 60):02}:{int(x % 60):02},{int(x * 1000 % 1000):03}"
    srt = [f"{i + 1}\n{ts(a)} --> {ts(b)}\n{' '.join(w_ for _, _, w_, _ in caps[i])}\n"
           for i, (a, b, _) in enumerate(cap_frames)]
    (out / "captions.srt").write_text("\n".join(srt))
    meta = dict(id=sid, title=story["title"], duration=round(total, 2), video=mp4.name,
                **story.get("post", {}))
    (out / "post.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    log(f"done -> {mp4} ({total:.1f}s, {mp4.stat().st_size / 1e6:.1f} MB)")
    return mp4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--preview", action="store_true", help="half resolution, fast encode")
    ap.add_argument("--no-ai-images", action="store_true", help="offline placeholder backgrounds")
    ap.add_argument("--allow-any-length", action="store_true")
    a = ap.parse_args()
    build(a.story, a.out, a.preview, a.no_ai_images, a.allow_any_length)


if __name__ == "__main__":
    main()
