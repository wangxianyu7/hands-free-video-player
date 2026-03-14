"""Flask server for English Listening Practice app."""

import glob
import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, Response, send_from_directory

from explainer import chat_about_content, explain_subtitle, get_client, text_to_speech, transcribe_audio
from srt_parser import parse_srt

load_dotenv(override=True)

app = Flask(__name__, static_folder="static", template_folder="templates")

# --- Config ---
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "")
MODEL = os.getenv("MODEL", "gpt-4o-mini")
VIDEO_DIR = os.path.dirname(os.path.abspath(__file__))


def find_files():
    """Find video and subtitle files in the working directory."""
    videos = sorted(glob.glob(os.path.join(VIDEO_DIR, "*.mp4"))
                    + glob.glob(os.path.join(VIDEO_DIR, "*.mkv"))
                    + glob.glob(os.path.join(VIDEO_DIR, "*.webm")))
    srts = sorted(glob.glob(os.path.join(VIDEO_DIR, "*.srt")))
    return videos, srts


@app.route("/")
def index():
    videos, srts = find_files()
    video_names = [os.path.basename(v) for v in videos]
    srt_names = [os.path.basename(s) for s in srts]
    return render_template("index.html", videos=video_names, srts=srt_names)


@app.route("/video/<path:filename>")
def serve_video(filename):
    """Serve video with range request support for instant seeking."""
    filepath = os.path.join(VIDEO_DIR, filename)
    if not os.path.isfile(filepath):
        return "Not found", 404

    file_size = os.path.getsize(filepath)
    range_header = request.headers.get("Range")

    if range_header:
        match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else min(start + 1024 * 1024, file_size - 1)
            end = min(end, file_size - 1)
            length = end - start + 1

            def generate():
                with open(filepath, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            resp = Response(generate(), status=206, mimetype="video/mp4")
            resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            resp.headers["Content-Length"] = str(length)
            resp.headers["Accept-Ranges"] = "bytes"
            return resp

    # No range — stream the full file
    def generate_full():
        with open(filepath, "rb") as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                yield data

    resp = Response(generate_full(), mimetype="video/mp4")
    resp.headers["Content-Length"] = str(file_size)
    resp.headers["Accept-Ranges"] = "bytes"
    return resp


@app.route("/subtitles/<path:filename>")
def get_subtitles(filename):
    """Return parsed subtitles as JSON."""
    filepath = os.path.join(VIDEO_DIR, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "not found"}), 404
    subs = parse_srt(filepath)
    return jsonify([
        {"index": s.index, "start": s.start_seconds, "end": s.end_seconds, "text": s.text}
        for s in subs
    ])


@app.route("/explain", methods=["POST"])
def explain():
    """Explain a subtitle line."""
    data = request.json
    sub_index = data.get("sub_index")
    srt_file = data.get("srt_file")

    if not srt_file:
        return jsonify({"error": "no srt_file"}), 400

    filepath = os.path.join(VIDEO_DIR, srt_file)
    subs = parse_srt(filepath)

    target = None
    context = []
    for i, s in enumerate(subs):
        if s.index == sub_index:
            target = s
            start = max(0, i - 3)
            end = min(len(subs), i + 4)
            context = subs[start:end]
            break

    if not target:
        return jsonify({"error": "subtitle not found"}), 404

    try:
        client = get_client(API_KEY, BASE_URL if BASE_URL else None)
        explanation = explain_subtitle(client, MODEL, target, context)
        return jsonify({"explanation": explanation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """Chat about content."""
    data = request.json
    question = data.get("question", "")
    history = data.get("history", [])
    srt_file = data.get("srt_file")

    if not srt_file or not question:
        return jsonify({"error": "missing fields"}), 400

    filepath = os.path.join(VIDEO_DIR, srt_file)
    subs = parse_srt(filepath)
    context_window = subs[:200] if len(subs) > 200 else subs

    try:
        client = get_client(API_KEY, BASE_URL if BASE_URL else None)
        answer = chat_about_content(client, MODEL, question, context_window, history)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/voice", methods=["POST"])
def voice_conversation():
    """Voice conversation endpoint.
    Receives audio blob, transcribes with Whisper, gets LLM response,
    converts to speech with TTS, returns both text and audio.
    """
    audio_file = request.files.get("audio")
    srt_file = request.form.get("srt_file", "")
    current_sub_index = request.form.get("current_sub_index", "-1")
    history_json = request.form.get("history", "[]")

    if not audio_file:
        return jsonify({"error": "no audio"}), 400

    import base64
    import json
    import traceback

    try:
        history = json.loads(history_json)
        client = get_client(API_KEY, BASE_URL if BASE_URL else None)

        # 1. Transcribe user speech with Whisper
        audio_bytes = audio_file.read()
        user_text = transcribe_audio(client, audio_bytes)

        # 2. Detect if it's a playback command
        lower = user_text.lower().strip()
        playback_commands = {
            "stop": "STOP", "pause": "STOP",
            "play": "PLAY", "go": "PLAY", "continue": "PLAY", "resume": "PLAY",
            "rewind": "REWIND", "go back": "REWIND", "back": "REWIND",
            "forward": "FORWARD", "skip": "FORWARD",
            "repeat": "LOOP", "loop": "LOOP", "again": "LOOP",
            "slower": "SLOWER", "slow down": "SLOWER",
            "faster": "FASTER", "speed up": "FASTER",
        }

        for phrase, cmd in playback_commands.items():
            if lower.startswith(phrase) or lower == phrase:
                return jsonify({
                    "user_text": user_text,
                    "command": cmd,
                    "response_text": "",
                    "audio_base64": "",
                })

        # 3. Get subtitle context for the LLM
        context_subs = []
        if srt_file:
            filepath = os.path.join(VIDEO_DIR, srt_file)
            if os.path.isfile(filepath):
                subs = parse_srt(filepath)
                context_subs = subs[:200] if len(subs) > 200 else subs

                # If user says "explain" with a current subtitle
                current_idx = int(current_sub_index)
                if current_idx >= 0 and ("explain" in lower or "what does" in lower or "what did" in lower):
                    target = None
                    ctx = []
                    for i, s in enumerate(subs):
                        if s.index == current_idx:
                            target = s
                            start = max(0, i - 3)
                            end = min(len(subs), i + 4)
                            ctx = subs[start:end]
                            break
                    if target:
                        response_text = explain_subtitle(client, MODEL, target, ctx)
                        tts_bytes = text_to_speech(client, response_text)
                        audio_b64 = base64.b64encode(tts_bytes).decode()
                        return jsonify({
                            "user_text": user_text,
                            "command": "NONE",
                            "response_text": response_text,
                            "audio_base64": audio_b64,
                        })

        # 4. General conversation
        response_text = chat_about_content(client, MODEL, user_text, context_subs, history)

        # 5. TTS
        tts_bytes = text_to_speech(client, response_text)
        audio_b64 = base64.b64encode(tts_bytes).decode()

        return jsonify({
            "user_text": user_text,
            "command": "NONE",
            "response_text": response_text,
            "audio_base64": audio_b64,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting English Listening Practice...")
    print("Open http://127.0.0.1:5000 in Chrome or Edge")
    app.run(host="127.0.0.1", port=5000, debug=True)
