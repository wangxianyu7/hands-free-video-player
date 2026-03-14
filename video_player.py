"""Custom HTML5 video player with voice control using Web Speech API."""

import json
from urllib.parse import quote

from srt_parser import Subtitle, format_timestamp


def build_subtitle_json(subtitles: list[Subtitle]) -> str:
    """Convert subtitles to JSON for the JS player."""
    subs = [
        {
            "index": s.index,
            "start": s.start_seconds,
            "end": s.end_seconds,
            "text": s.text,
        }
        for s in subtitles
    ]
    return json.dumps(subs)


def get_player_html(video_url: str, subtitles: list[Subtitle], rewind_seconds: int = 5) -> str:
    """Generate the full HTML5 player with voice control.
    video_url: full URL to the video file (e.g. http://127.0.0.1:8502/video.mp4)
    """
    subs_json = build_subtitle_json(subtitles)

    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0e1117; color: #fafafa; }}

    .player-container {{
        width: 100%;
        max-width: 100%;
    }}

    video {{
        width: 100%;
        border-radius: 8px;
        background: #000;
    }}

    .controls {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 0;
        flex-wrap: wrap;
    }}

    .controls button {{
        padding: 8px 16px;
        border: 1px solid #333;
        border-radius: 6px;
        background: #262730;
        color: #fafafa;
        cursor: pointer;
        font-size: 14px;
        transition: background 0.2s;
    }}
    .controls button:hover {{ background: #3a3a4a; }}
    .controls button.active {{ background: #ff4b4b; border-color: #ff4b4b; }}

    .controls select {{
        padding: 8px;
        border: 1px solid #333;
        border-radius: 6px;
        background: #262730;
        color: #fafafa;
        font-size: 14px;
    }}

    .voice-status {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        margin: 8px 0;
        border-radius: 6px;
        background: #1a1a2e;
        border: 1px solid #333;
        font-size: 14px;
    }}

    .voice-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #555;
        transition: background 0.3s;
    }}
    .voice-dot.listening {{ background: #00cc66; animation: pulse 1.5s infinite; }}
    .voice-dot.heard {{ background: #ff4b4b; }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}

    .subtitle-display {{
        padding: 12px;
        margin: 8px 0;
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 6px;
        min-height: 50px;
        font-size: 16px;
        line-height: 1.5;
    }}

    .subtitle-display .current {{ color: #ff4b4b; font-weight: bold; }}
    .subtitle-display .context {{ color: #888; }}

    .voice-log {{
        padding: 8px 12px;
        margin: 4px 0;
        background: #1e1e2e;
        border-left: 3px solid #ff4b4b;
        border-radius: 0 6px 6px 0;
        font-size: 13px;
        color: #ccc;
    }}

    .time-display {{
        font-size: 14px;
        color: #aaa;
        min-width: 100px;
        text-align: center;
    }}
</style>
</head>
<body>
<div class="player-container">
    <video id="videoPlayer" preload="metadata">
        <source src="{video_url}" type="video/mp4">
        Your browser does not support HTML5 video.
    </video>

    <div class="controls">
        <button onclick="togglePlay()" id="playBtn">Play</button>
        <button onclick="rewind()">Rewind {rewind_seconds}s</button>
        <button onclick="forward()">Forward {rewind_seconds}s</button>
        <button onclick="toggleLoop()" id="loopBtn">Loop Off</button>
        <select onchange="setSpeed(this.value)" id="speedSelect">
            <option value="0.5">0.5x</option>
            <option value="0.75">0.75x</option>
            <option value="1" selected>1x</option>
            <option value="1.25">1.25x</option>
            <option value="1.5">1.5x</option>
        </select>
        <span class="time-display" id="timeDisplay">00:00 / 00:00</span>
    </div>

    <div class="voice-status">
        <div class="voice-dot" id="voiceDot"></div>
        <span id="voiceStatus">Voice control: click "Start Listening" to begin</span>
        <button onclick="toggleVoice()" id="voiceBtn" style="margin-left:auto; padding:6px 12px; border:1px solid #333; border-radius:6px; background:#262730; color:#fafafa; cursor:pointer; font-size:13px;">Start Listening</button>
    </div>

    <div class="subtitle-display" id="subtitleDisplay">
        Subtitles will appear here...
    </div>

    <div id="voiceLog"></div>
</div>

<script>
    const video = document.getElementById('videoPlayer');
    const playBtn = document.getElementById('playBtn');
    const loopBtn = document.getElementById('loopBtn');
    const timeDisplay = document.getElementById('timeDisplay');
    const subtitleDisplay = document.getElementById('subtitleDisplay');
    const voiceDot = document.getElementById('voiceDot');
    const voiceStatus = document.getElementById('voiceStatus');
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceLog = document.getElementById('voiceLog');

    const REWIND_SECONDS = {rewind_seconds};
    const subtitles = {subs_json};

    let isLooping = false;
    let loopStart = 0;
    let loopEnd = 0;
    let currentSubIndex = -1;
    let recognition = null;
    let isListening = false;

    // --- Playback controls ---
    function togglePlay() {{
        if (video.paused) {{
            video.play();
            playBtn.textContent = 'Pause';
        }} else {{
            video.pause();
            playBtn.textContent = 'Play';
        }}
    }}

    function rewind() {{
        video.currentTime = Math.max(0, video.currentTime - REWIND_SECONDS);
    }}

    function forward() {{
        video.currentTime = Math.min(video.duration, video.currentTime + REWIND_SECONDS);
    }}

    function setSpeed(speed) {{
        video.playbackRate = parseFloat(speed);
    }}

    function toggleLoop() {{
        if (isLooping) {{
            isLooping = false;
            loopBtn.textContent = 'Loop Off';
            loopBtn.classList.remove('active');
        }} else if (currentSubIndex >= 0) {{
            isLooping = true;
            const sub = subtitles[currentSubIndex];
            loopStart = sub.start;
            loopEnd = sub.end;
            loopBtn.textContent = 'Loop On';
            loopBtn.classList.add('active');
        }}
    }}

    function loopCurrentSentence() {{
        if (currentSubIndex >= 0) {{
            const sub = subtitles[currentSubIndex];
            isLooping = true;
            loopStart = sub.start;
            loopEnd = sub.end;
            loopBtn.textContent = 'Loop On';
            loopBtn.classList.add('active');
            video.currentTime = loopStart;
            video.play();
            playBtn.textContent = 'Pause';
        }}
    }}

    // --- Time & subtitle update ---
    function formatTime(sec) {{
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }}

    video.addEventListener('timeupdate', () => {{
        const t = video.currentTime;
        timeDisplay.textContent = formatTime(t) + ' / ' + formatTime(video.duration || 0);

        // Loop check
        if (isLooping && t >= loopEnd) {{
            video.currentTime = loopStart;
        }}

        // Find current subtitle
        let found = -1;
        for (let i = 0; i < subtitles.length; i++) {{
            if (t >= subtitles[i].start && t <= subtitles[i].end) {{
                found = i;
                break;
            }}
        }}

        if (found !== currentSubIndex) {{
            currentSubIndex = found;
            updateSubtitleDisplay();
            // Send current subtitle index to Streamlit
            if (found >= 0) {{
                window.parent.postMessage({{
                    type: 'subtitle_update',
                    index: found,
                    subIndex: subtitles[found].index
                }}, '*');
            }}
        }}
    }});

    video.addEventListener('play', () => {{ playBtn.textContent = 'Pause'; }});
    video.addEventListener('pause', () => {{ playBtn.textContent = 'Play'; }});

    function updateSubtitleDisplay() {{
        if (currentSubIndex < 0) {{
            subtitleDisplay.innerHTML = '<span class="context">...</span>';
            return;
        }}
        let html = '';
        const start = Math.max(0, currentSubIndex - 1);
        const end = Math.min(subtitles.length, currentSubIndex + 2);
        for (let i = start; i < end; i++) {{
            if (i === currentSubIndex) {{
                html += '<div class="current">' + subtitles[i].text + '</div>';
            }} else {{
                html += '<div class="context">' + subtitles[i].text + '</div>';
            }}
        }}
        subtitleDisplay.innerHTML = html;
    }}

    // --- Voice control via Web Speech API ---
    function toggleVoice() {{
        if (isListening) {{
            stopListening();
        }} else {{
            startListening();
        }}
    }}

    function startListening() {{
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            voiceStatus.textContent = 'Voice control not supported in this browser. Use Chrome or Edge.';
            return;
        }}

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {{
            isListening = true;
            voiceDot.classList.add('listening');
            voiceStatus.textContent = 'Listening... say "stop", "play", "rewind", "repeat", "explain"';
            voiceBtn.textContent = 'Stop Listening';
        }};

        recognition.onresult = (event) => {{
            const last = event.results[event.results.length - 1];
            if (last.isFinal) {{
                const text = last[0].transcript.trim().toLowerCase();
                logVoice('Heard: "' + text + '"');
                handleVoiceCommand(text);
            }}
        }};

        recognition.onerror = (event) => {{
            if (event.error === 'no-speech') return; // ignore silence
            logVoice('Voice error: ' + event.error);
        }};

        recognition.onend = () => {{
            // Auto-restart if still supposed to be listening
            if (isListening) {{
                try {{ recognition.start(); }} catch(e) {{}}
            }}
        }};

        recognition.start();
    }}

    function stopListening() {{
        isListening = false;
        if (recognition) {{
            recognition.stop();
            recognition = null;
        }}
        voiceDot.classList.remove('listening');
        voiceStatus.textContent = 'Voice control stopped';
        voiceBtn.textContent = 'Start Listening';
    }}

    function handleVoiceCommand(text) {{
        voiceDot.classList.add('heard');
        setTimeout(() => voiceDot.classList.remove('heard'), 500);

        if (text.includes('stop') || text.includes('pause')) {{
            video.pause();
            logVoice('Paused');
        }}
        else if (text.includes('play') || text.includes('go') || text.includes('continue') || text.includes('resume')) {{
            video.play();
            logVoice('Playing');
        }}
        else if (text.includes('rewind') || text.includes('back') || text.includes('go back')) {{
            rewind();
            logVoice('Rewound ' + REWIND_SECONDS + 's');
        }}
        else if (text.includes('forward') || text.includes('skip')) {{
            forward();
            logVoice('Forward ' + REWIND_SECONDS + 's');
        }}
        else if (text.includes('repeat') || text.includes('loop') || text.includes('again')) {{
            loopCurrentSentence();
            logVoice('Looping current sentence');
        }}
        else if (text.includes('stop loop') || text.includes('no loop')) {{
            isLooping = false;
            loopBtn.textContent = 'Loop Off';
            loopBtn.classList.remove('active');
            logVoice('Loop stopped');
        }}
        else if (text.includes('explain') || text.includes('what does') || text.includes('what did')) {{
            video.pause();
            // Send explain request to Streamlit
            if (currentSubIndex >= 0) {{
                window.parent.postMessage({{
                    type: 'explain_request',
                    index: currentSubIndex,
                    subIndex: subtitles[currentSubIndex].index
                }}, '*');
                logVoice('Requesting explanation...');
            }} else {{
                logVoice('No subtitle at current position');
            }}
        }}
        else if (text.includes('slow') || text.includes('slower')) {{
            video.playbackRate = Math.max(0.25, video.playbackRate - 0.25);
            document.getElementById('speedSelect').value = video.playbackRate;
            logVoice('Speed: ' + video.playbackRate + 'x');
        }}
        else if (text.includes('fast') || text.includes('faster')) {{
            video.playbackRate = Math.min(2, video.playbackRate + 0.25);
            document.getElementById('speedSelect').value = video.playbackRate;
            logVoice('Speed: ' + video.playbackRate + 'x');
        }}
        else {{
            // Treat as a question — send to Streamlit chat
            window.parent.postMessage({{
                type: 'chat_question',
                question: text
            }}, '*');
            logVoice('Sent to chat: "' + text + '"');
        }}
    }}

    function logVoice(msg) {{
        const div = document.createElement('div');
        div.className = 'voice-log';
        div.textContent = msg;
        voiceLog.prepend(div);
        // Keep only last 5 logs
        while (voiceLog.children.length > 5) {{
            voiceLog.removeChild(voiceLog.lastChild);
        }}
    }}
</script>
</body>
</html>
"""
