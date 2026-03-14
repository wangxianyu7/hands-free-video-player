# HeyTutor

A hands-free video player for English listening practice. Watch YouTube videos with voice-controlled playback, AI-powered explanations, and real-time conversation with an AI tutor.

## Features

- **YouTube Integration** — Paste any YouTube URL, video streams directly with auto-downloaded subtitles
- **Hands-Free Voice Control** — Say "stop", "play", "rewind", "repeat" for instant playback control via Web Speech API
- **AI Tutor Conversation** — Say "hey tutor" then ask any question about what you heard. Your speech is transcribed by Whisper and answered by GPT with text-to-speech response
- **Synchronized Subtitles** — Auto-highlighted subtitle panel synced to video position. Click any line to jump, loop, or explain
- **Time Jump & Speed Control** — Voice commands like "jump to 5 minutes", "speed 0.75", "slower", "faster"
- **Sound Feedback** — Distinct ding sounds for command confirmation, wake word detection, and processing status

## How It Works

```
Your Voice → Web Speech API (instant commands)
           → "hey tutor" → Whisper API → GPT-4o-mini → TTS → Audio response
```

- **Simple commands** (stop, play, rewind) are handled locally by the browser — zero latency
- **Questions** are routed through Whisper for accurate transcription (accent-friendly), then GPT for explanation, then TTS to speak the answer back

## Setup

### Requirements

- Python 3.10+
- Chrome or Edge browser (for Web Speech API)
- OpenAI API key
- Headphones recommended (prevents mic from picking up video audio)

### Install

```bash
git clone https://github.com/wangxianyu7/hands-free-video-player.git
cd hands-free-video-player
pip install -r requirements.txt
```

### Configure

Create a `.env` file:

```
OPENAI_API_KEY=your-api-key-here

# Optional: use a different provider (e.g., DeepSeek)
# OPENAI_BASE_URL=https://api.deepseek.com
# MODEL=deepseek-chat
```

### Run

```bash
python server.py
```

Open http://127.0.0.1:5000 in Chrome or Edge.

## Usage

1. Paste a YouTube URL and click **Load**
2. Click **Enable Hands-Free** to activate voice control
3. Use voice commands to control playback:

| Command | Action |
|---------|--------|
| stop / pause / wait | Pause video |
| play / go / continue | Resume video |
| rewind / back | Rewind 5 seconds |
| forward / skip | Forward 5 seconds |
| repeat / again | Loop current sentence |
| slower / faster | Adjust playback speed |
| speed 0.75 | Set specific speed |
| jump to 2 minutes | Seek to timestamp |

4. Say **"hey tutor"** to activate the AI tutor, then ask your question
5. The tutor responds with voice and text in the Chat panel

## Tech Stack

- **Flask** — Web server with video streaming and API endpoints
- **yt-dlp** — YouTube subtitle downloading
- **YouTube IFrame API** — Embedded video playback
- **Web Speech API** — Browser-based speech recognition for instant commands
- **OpenAI Whisper** — Accurate speech-to-text for questions
- **OpenAI GPT-4o-mini** — AI tutor for explanations and conversation
- **OpenAI TTS** — Text-to-speech for tutor responses

## License

MIT
