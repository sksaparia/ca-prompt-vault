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


def get_next_card():
    used = []
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            used = json.load(f)

    # .jpg, .jpeg, .png — teeno dhundho
    all_cards = sorted(
        list(Path(CARDS_DIR).glob("*.jpg")) +
        list(Path(CARDS_DIR).glob("*.jpeg")) +
        list(Path(CARDS_DIR).glob("*.png"))
    )

    print(f"📂 Total cards found: {len(all_cards)}")
    print(f"✅ Already used: {len(used)}")

    for card_path in all_cards:
        stem = card_path.name  # poora naam use karo stem ki jagah
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


def claude_script(card_name, num):
    """Claude AI se Hinglish voiceover script"""

    # Card number se title guess karo
    titles = {
        1: "GST Registration Checklist",
        2: "Maximize GST Input Tax Credit",
        3: "GSTR-9 Annual Return Filing",
        4: "Income Tax Planning — Salaried Person",
        5: "TDS Compliance Guide",
        6: "Balance Sheet Analysis",
        7: "Audit Documentation",
        8: "Bank Audit aur LFAR Preparation",
        9: "Cash Flow Statement — Ind AS 7",
        10: "Financial Ratio Analysis",
        11: "Payroll Processing + PF/ESI Compliance",
        12: "ROC Annual Compliance — MCA Filings",
        13: "Startup Tax Benefits — Section 80-IAC",
        14: "GST E-Invoice aur E-Way Bill",
        15: "Tax Planning for Business",
        16: "Income Tax Notice — Section 143 aur 148",
        17: "Private Limited Company Registration",
        18: "GST Audit",
        19: "GSTR-9C GST Audit Reconciliation",
        20: "Ind AS Financial Statements Preparation",
        21: "M&A Due Diligence Checklist",
        22: "Advance Tax — Computation aur Schedule",
        23: "Form 3CD Tax Audit — 44 Clauses",
        24: "Working Capital Analysis aur Management",
        25: "LLP Registration aur Compliance",
        26: "GST Refund — RFD-01 Filing Guide",
        27: "Capital Gains on Property — Section 54",
    }
    title = titles.get(num, f"CA Prompt #{num}")

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
    return resp["content"][0]["text"].strip(), title


def make_voiceover(script, out_path):
    """edge-tts se Hindi MP3 voiceover"""
    import edge_tts

    async def _generate():
        communicate = edge_tts.Communicate(
            script,
            voice="hi-IN-SwaraNeural",
            rate="+10%"
        )
        await communicate.save(out_path)

    asyncio.run(_generate())


def get_card_number(filename):
    """Filename se card number nikalo"""
    import re
    # "(1)" ya "(9)" type pattern dhundho
    match = re.search(r'\((\d+)\)', filename)
    if match:
        return int(match.group(1))
    # Ya seedha number dhundho
    match = re.search(r'(\d+)', filename)
    if match:
        return int(match.group(1))
    return 1


def build_video(image, voiceover, bgm, output):
    """FFmpeg se 9:16 final Short banata hai"""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe_path = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    if not os.path.exists(ffprobe_path):
        ffprobe_path = "ffprobe"

    r = subprocess.run(
        [ffprobe_path, "-v", "quiet", "-show_entries", "format=duration",
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

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"✅ ffmpeg: {ffmpeg}")

    # BGM restore
    bgm_path = "bgm.mp3"
    if BGM_B64 and not os.path.exists(bgm_path):
        with open(bgm_path, "wb") as f:
            f.write(base64.b64decode(BGM_B64))
        print("✅ BGM restored")
    elif not os.path.exists(bgm_path):
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi",
            "-i", "aevalsrc=0.1*sin(2*PI*220*t)+0.08*sin(2*PI*330*t):s=44100:d=60",
            bgm_path
        ], capture_output=True)
        print("✅ BGM generated (fallback)")

    # Agle card lo
    card_path, stem = get_next_card()
    if not card_path:
        print("❌ Saari cards use ho gayi! Nayi cards add karo repo mein.")
        return

    print(f"📌 Card file: {card_path.name}")

    # Card number nikalo filename se
    num = get_card_number(card_path.name)
    print(f"🔢 Card number detected: #{num}")

    # 1. Script
    print("\n🤖 Script generate ho rahi hai...")
    script, title = claude_script(card_path.name, num)
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
