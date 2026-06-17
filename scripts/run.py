"""
CA Prompt Vault — YouTube Shorts Auto-Upload
GitHub Actions se roz subah 9 baje apne aap chalta hai
"""

import os, json, subprocess, urllib.request, base64, asyncio
from datetime import datetime
from pathlib import Path

# ── ffmpeg path set karo (imageio-ffmpeg se, bina apt ke) ──
import imageio_ffmpeg
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

# ── ENV VARS ────────────────────────────────────────────────
ANTHROPIC_KEY    = os.environ["ANTHROPIC_API_KEY"]
YT_CLIENT_ID     = os.environ["YT_CLIENT_ID"]
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]
BGM_B64          = os.environ.get("BGM_B64", "")

TRACKER_FILE = "used_cards.json"
CARDS_DIR    = "cards"

# ── CA CARDS DATA ───────────────────────────────────────────
CA_CARDS = {
    "1000573116": {"num": 8,  "title": "Bank Audit aur LFAR Preparation"},
    "1000573117": {"num": 9,  "title": "Cash Flow Statement — Ind AS 7"},
    "1000573118": {"num": 10, "title": "Financial Ratio Analysis"},
    "1000573119": {"num": 11, "title": "Payroll Processing + PF/ESI Compliance"},
    "1000573120": {"num": 12, "title": "ROC Annual Compliance — MCA Filings"},
    "1000573121": {"num": 13, "title": "Startup Tax Benefits — Section 80-IAC"},
    "1000573123": {"num": 14, "title": "GST E-Invoice aur E-Way Bill"},
    "1000573124": {"num": 16, "title": "Income Tax Notice — Section 143 aur 148"},
    "1000573125": {"num": 17, "title": "Private Limited Company Registration"},
    "1000573126": {"num": 19, "title": "GSTR-9C GST Audit Reconciliation"},
    "1000573128": {"num": 20, "title": "Ind AS Financial Statements Preparation"},
    "1000573129": {"num": 21, "title": "M&A Due Diligence Checklist"},
    "1000573130": {"num": 22, "title": "Advance Tax — Computation aur Schedule"},
    "1000573131": {"num": 23, "title": "Form 3CD Tax Audit — 44 Clauses"},
    "1000573132": {"num": 24, "title": "Working Capital Analysis aur Management"},
    "1000573133": {"num": 25, "title": "LLP Registration aur Compliance"},
    "1000573134": {"num": 26, "title": "GST Refund — RFD-01 Filing Guide"},
    "1000573135": {"num": 27, "title": "Capital Gains on Property — Section 54"},
}


def get_next_card():
    used = []
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            used = json.load(f)

    all_cards = sorted(Path(CARDS_DIR).glob("*.jpg"))
    for card_path in all_cards:
        stem = card_path.stem
        if stem not in used:
            return card_path, stem
    return None, None


def mark_used(stem):
    used = []
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            used = json.load(f)
    used.append(stem)
    with open(TRACKER_FILE, "w") as f:
        json.dump(used, f)


def claude_script(title, num):
    """Claude AI se Hinglish voiceover script"""
    prompt = f"""YouTube Shorts ke liye Hinglish voiceover script likho.

Topic: CA Prompt #{num} — {title}

Rules:
- Hinglish (Hindi+English mix, Roman script)
- 55-65 words only (20-25 sec)
- Start: "Doston! Aaj ka CA Prompt hai..."
- Middle: ye prompt kab aur kaise use karo (2 lines)
- End: "Like karo aur subscribe karo CA Prompt Vault ko!"
- Simple language, CA students ke liye

Sirf script text, koi heading nahi."""

    data = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 250,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01"
        }
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
    return resp["content"][0]["text"].strip()


def make_voiceover(script, out_path):
    """edge-tts se Hindi MP3 voiceover — no espeak, no apt needed"""
    import edge_tts

    async def _generate():
        communicate = edge_tts.Communicate(
            script,
            voice="hi-IN-SwaraNeural",
            rate="+10%"
        )
        await communicate.save(out_path)

    asyncio.run(_generate())


def get_ffmpeg_exe():
    """imageio-ffmpeg se ffmpeg binary path lo"""
    return imageio_ffmpeg.get_ffmpeg_exe()


def build_video(image, voiceover, bgm, output):
    """FFmpeg se 9:16 final Short banata hai"""
    ffmpeg = get_ffmpeg_exe()

    # ffprobe bhi same folder mein hota hai
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if not os.path.exists(ffprobe):
        # fallback: system ffprobe use karo
        ffprobe = "ffprobe"

    r = subprocess.run(
        [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", voiceover],
        capture_output=True, text=True
    )
    dur = min(float(r.stdout.strip()) + 1.5, 58)

    subprocess.run([
        ffmpeg, "-y",
        "-loop", "1", "-i", str(image),
        "-i", voiceover,
        "-i", bgm,
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v];"
        "[1:a]volume=1.7[vo];"
        "[2:a]volume=0.18,aloop=loop=-1:size=2e+09[bg];"
        "[vo][bg]amix=inputs=2:duration=first[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output
    ], check=True, capture_output=True)


def get_yt_access_token():
    import urllib.parse
    data = urllib.parse.urlencode({
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "refresh_token": YT_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]


def upload_youtube(video_path, title, description, access_token):
    """YouTube Data API v3 resumable upload"""
    meta = json.dumps({
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": ["CA exam", "GST", "income tax", "CA prompt", "accounting",
                     "finance", "shorts", "CA student", "ICAI"],
            "categoryId": "27"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }).encode()

    init_req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        data=meta,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(os.path.getsize(video_path))
        },
        method="POST"
    )
    with urllib.request.urlopen(init_req) as r:
        upload_url = r.headers["Location"]

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_req = urllib.request.Request(
        upload_url,
        data=video_data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4"
        },
        method="PUT"
    )
    with urllib.request.urlopen(upload_req) as r:
        resp = json.loads(r.read())

    return f"https://youtube.com/shorts/{resp['id']}"


def main():
    print(f"\n{'='*50}")
    print(f"CA Prompt Vault — {datetime.now().strftime('%d %b %Y %I:%M %p')}")
    print(f"{'='*50}\n")

    ffmpeg = get_ffmpeg_exe()
    print(f"✅ ffmpeg path: {ffmpeg}")

    # BGM restore karo
    bgm_path = "bgm.mp3"
    if BGM_B64 and not os.path.exists(bgm_path):
        with open(bgm_path, "wb") as f:
            f.write(base64.b64decode(BGM_B64))
        print("✅ BGM restored from secret")
    elif not os.path.exists(bgm_path):
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi",
            "-i", "aevalsrc=0.1*sin(2*PI*220*t)+0.08*sin(2*PI*330*t):s=44100:d=60",
            bgm_path
        ], capture_output=True)
        print("✅ BGM generated (fallback tone)")

    # Agle card lo
    card_path, stem = get_next_card()
    if not card_path:
        print("❌ Saari cards use ho gayi! Nayi cards add karo repo mein.")
        return

    info  = CA_CARDS.get(stem, {"num": "?", "title": stem})
    num   = info["num"]
    title = info["title"]
    print(f"📌 Card #{num}: {title}")
    print(f"📊 File: {card_path.name}")

    # 1. Script
    print("\n🤖 Script generate ho rahi hai...")
    script = claude_script(title, num)
    print(f"   {script[:70]}...")

    # 2. Voiceover
    print("🎙️  Voiceover ban raha hai...")
    make_voiceover(script, "voiceover.mp3")
    print("   ✅ Done")

    # 3. Video
    print("🎬 Video build ho raha hai...")
    build_video(card_path, "voiceover.mp3", bgm_path, "output.mp4")
    size = os.path.getsize("output.mp4") / 1024 / 1024
    print(f"   ✅ {size:.1f} MB ready")

    # 4. Upload
    print("📤 YouTube pe upload ho raha hai...")
    token = get_yt_access_token()

    yt_title = f"CA Prompt #{num}: {title} 🔥 #Shorts"
    yt_desc  = (
        f"🎯 Aaj ka CA Prompt: {title}\n\n"
        f"{script}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Roz nayi CA tips ke liye Subscribe karo!\n"
        f"📌 Save karo baad mein dekhne ke liye\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"#CAPrompt #CAExam #GST #IncomeTax #Accounting #Shorts #Finance #ICAI #CA"
    )

    url = upload_youtube("output.mp4", yt_title, yt_desc, token)
    mark_used(stem)

    # Cleanup
    for f in ["voiceover.mp3", "output.mp4"]:
        if os.path.exists(f):
            os.remove(f)

    print(f"\n{'='*50}")
    print(f"🎉 SUCCESS!")
    print(f"🔗 {url}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
