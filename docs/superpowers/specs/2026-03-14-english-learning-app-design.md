# English Learning App — Design Spec

## Overview

A Streamlit-based English listening/speaking practice app that plays downloaded YouTube videos with synchronized subtitles, segment looping, and on-demand bilingual (English/Chinese) explanations powered by OpenAI GPT-4o-mini.

## Architecture

### Components

1. **SRT Parser** — Parse `.srt` subtitle files into timestamped segments
2. **Video Player** — Streamlit video player with playback controls
3. **Subtitle Panel** — Scrollable, clickable subtitle list synced to video position
4. **Explanation Engine** — OpenAI GPT-4o-mini for bilingual sentence explanations
5. **Chat Box** — Free-form Q&A about the content

### Data Flow

```
Video file (.mp4) + Subtitle file (.srt)
        ↓
   SRT Parser → list of {index, start, end, text}
        ↓
   Streamlit GUI
   ├── Left: Video player + controls
   └── Right: Subtitle panel + Explain + Chat
        ↓ (on user action)
   OpenAI API → bilingual explanation / chat response
```

### Tech Stack

- Python 3.10+
- Streamlit
- OpenAI Python SDK (GPT-4o-mini, Whisper as fallback)
- `pysrt` for SRT parsing
- `python-dotenv` for API key management

## UI Layout

### Left Column (~60%)
- Video player
- Playback controls: rewind 5s, forward 5s, speed control (0.5x, 0.75x, 1x, 1.25x)
- Loop toggle for current segment

### Right Column (~40%)
- **Subtitle panel**: scrollable list, auto-highlighted to current position
  - Click any line → jump to timestamp
  - "Loop" button → repeat that segment
  - "Explain" button → trigger explanation
- **Explanation area**: shows LLM response
- **Chat box**: free-form input for deeper questions

## Explanation Format

When user clicks "Explain" on a subtitle line:

1. **Original sentence** — English text
2. **Chinese translation** — 中文翻译
3. **Key vocabulary** — difficult words with Chinese meaning
4. **Grammar notes** — brief structural explanation (if relevant)

Context: LLM receives ~5 surrounding subtitle lines for conversational context.

## Chat Box

Free-form questions about the content. Examples:
- "What does 'piece this together' mean?"
- "Is this formal or casual English?"
- "Can you give me similar expressions?"

## API Configuration

- OpenAI API key stored in `.env` file
- Model: `gpt-4o-mini` (swappable to DeepSeek or others later)
- Whisper API as fallback when no SRT file is available

## File Structure

```
plugin/
├── app.py                 # Main Streamlit app
├── srt_parser.py          # SRT file parsing
├── explainer.py           # OpenAI explanation engine
├── .env                   # API key (gitignored)
├── .gitignore
├── requirements.txt
├── docs/
│   └── superpowers/specs/
│       └── 2026-03-14-english-learning-app-design.md
├── *.mp4                  # Video files
└── *.srt                  # Subtitle files
```
