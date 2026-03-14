import tempfile

from openai import OpenAI

from srt_parser import Subtitle

EXPLAIN_SYSTEM_PROMPT = """You are an English language tutor helping a Chinese speaker improve their English listening skills.

When asked to explain a sentence, provide:
1. **Original**: The English sentence
2. **Key Vocabulary**: Difficult or notable words/phrases with simple English definitions
3. **Grammar Notes**: Brief grammar explanation if the sentence has interesting structure (skip if straightforward)

Respond in English only. Use simple, clear English. Only use Chinese if the user explicitly asks for Chinese translation."""

CHAT_SYSTEM_PROMPT = """You are an English language tutor helping a Chinese speaker improve their English listening skills.
You have access to the video transcript context below. Answer questions about vocabulary, grammar, expressions, pronunciation, or cultural context.
Respond in English only. Use simple, clear English. Only use Chinese if the user explicitly asks for it.

{nearby_context}
Full transcript context:
{context}"""


VOICE_COMMAND_PROMPT = """You are a voice command parser for an English learning app.
The user spoke a command while watching a video with subtitles. Classify their intent:

- If they want to explain/understand a sentence: respond with "EXPLAIN"
- If they want to repeat/loop: respond with "LOOP"
- If they are asking a question about the content: respond with "CHAT: <their question>"

Respond with ONLY the classification, nothing else."""


def get_client(api_key: str, base_url: str | None = None) -> OpenAI:
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def transcribe_audio(client: OpenAI, audio_bytes: bytes) -> str:
    """Transcribe audio bytes using Whisper API."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
        f.write(audio_bytes)
        f.flush()
        with open(f.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
    return transcript.text


def parse_voice_command(client: OpenAI, model: str, transcript: str) -> tuple[str, str]:
    """Parse a voice transcript into a command type and content.
    Returns (command_type, content) where command_type is EXPLAIN, LOOP, or CHAT.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VOICE_COMMAND_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0,
    )
    result = response.choices[0].message.content.strip()
    if result.startswith("CHAT:"):
        return "CHAT", result[5:].strip()
    return result, ""


def explain_subtitle(
    client: OpenAI,
    model: str,
    subtitle: Subtitle,
    context_subs: list[Subtitle],
) -> str:
    context_text = "\n".join(
        f"[{s.index}] {s.text}" for s in context_subs
    )
    user_msg = (
        f"Please explain this sentence from a video I'm watching:\n\n"
        f"\"{subtitle.text}\"\n\n"
        f"Surrounding context:\n{context_text}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def chat_about_content(
    client: OpenAI,
    model: str,
    question: str,
    context_subs: list[Subtitle],
    chat_history: list[dict],
    nearby_subs: list[Subtitle] | None = None,
) -> str:
    context_text = "\n".join(
        f"[{s.index}] {s.text}" for s in context_subs
    )
    nearby_text = ""
    if nearby_subs:
        nearby_lines = "\n".join(f"  > {s.text}" for s in nearby_subs)
        nearby_text = f"The user paused the video at this point. The subtitles around that moment are:\n{nearby_lines}\n\nUse this to understand what the user is referring to when they ask a question.\n"
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=context_text, nearby_context=nearby_text)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
    )
    return response.choices[0].message.content


def text_to_speech(client: OpenAI, text: str) -> bytes:
    """Convert text to speech using OpenAI TTS API. Returns MP3 audio bytes."""
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )
    return response.content
