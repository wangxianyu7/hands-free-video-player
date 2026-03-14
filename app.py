import glob
import os

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from explainer import chat_about_content, explain_subtitle, get_client
from srt_parser import format_timestamp, parse_srt
from video_player import get_player_html
from video_server import get_video_url, start_video_server

load_dotenv()

st.set_page_config(page_title="HeyTutor", layout="wide")
st.title("HeyTutor")


# --- Session state init ---
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


init_state("chat_history", [])
init_state("chat_messages", [])
init_state("explanation", "")
init_state("selected_sub_index", None)
init_state("last_viewed_sub", 0)


# --- Sidebar: settings & file selection ---
st.sidebar.header("Settings")

api_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=os.getenv("OPENAI_API_KEY", ""),
    type="password",
)
base_url = st.sidebar.text_input(
    "API Base URL (optional, for DeepSeek etc.)",
    value=os.getenv("OPENAI_BASE_URL", ""),
)
model = st.sidebar.text_input("Model", value="gpt-4o-mini")

# Find available video and subtitle files
video_files = sorted(glob.glob("*.mp4") + glob.glob("*.mkv") + glob.glob("*.webm"))
srt_files = sorted(glob.glob("*.srt"))

if not video_files:
    st.error("No video files (.mp4, .mkv, .webm) found in the current directory.")
    st.stop()
if not srt_files:
    st.error("No subtitle files (.srt) found in the current directory.")
    st.stop()

selected_video = st.sidebar.selectbox("Video File", video_files)
selected_srt = st.sidebar.selectbox("Subtitle File", srt_files)

# --- Parse subtitles ---
subtitles = parse_srt(selected_srt)

# --- Start local video server ---
video_dir = os.path.abspath(os.path.dirname(selected_video) or ".")
start_video_server(video_dir, port=8502)
video_url = get_video_url(selected_video)

# --- Layout: two columns ---
col_video, col_subs = st.columns([3, 2])

# --- Left column: Custom HTML5 Video Player ---
with col_video:
    player_html = get_player_html(video_url, subtitles)
    components.html(player_html, height=620, scrolling=False)

    st.caption(
        "Voice commands: **stop/pause** | **play/go** | **rewind/back** | "
        "**forward/skip** | **repeat/loop/again** | **explain** | **slower** | **faster**"
    )

# --- Right column: Subtitles + Explain + Chat ---
with col_subs:
    # --- Subtitle panel ---
    st.subheader("Subtitles")

    sub_container = st.container(height=300)
    with sub_container:
        for sub in subtitles:
            timestamp = f"{format_timestamp(sub.start_seconds)} - {format_timestamp(sub.end_seconds)}"
            cols = st.columns([5, 1])
            with cols[0]:
                st.markdown(
                    f"**[{timestamp}]** {sub.text}",
                    help=f"Subtitle #{sub.index}",
                )
            with cols[1]:
                if st.button("Explain", key=f"explain_{sub.index}"):
                    st.session_state.selected_sub_index = sub.index

    # --- Explanation area ---
    if st.session_state.selected_sub_index is not None:
        st.subheader("Explanation")

        target_sub = None
        context_subs = []
        for i, sub in enumerate(subtitles):
            if sub.index == st.session_state.selected_sub_index:
                target_sub = sub
                start = max(0, i - 3)
                end = min(len(subtitles), i + 4)
                context_subs = subtitles[start:end]
                break

        if target_sub and api_key:
            with st.spinner("Generating explanation..."):
                client = get_client(api_key, base_url if base_url else None)
                explanation = explain_subtitle(client, model, target_sub, context_subs)
                st.session_state.explanation = explanation
            st.markdown(st.session_state.explanation)
            st.session_state.selected_sub_index = None
        elif not api_key:
            st.warning("Please enter your OpenAI API key in the sidebar.")
            st.session_state.selected_sub_index = None

    elif st.session_state.explanation:
        st.subheader("Explanation")
        st.markdown(st.session_state.explanation)

    # --- Chat box ---
    st.subheader("Chat")
    st.caption("Ask any question about what you heard")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if question := st.chat_input("Ask about the content..."):
        if not api_key:
            st.warning("Please enter your OpenAI API key in the sidebar.")
        else:
            st.session_state.chat_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            context_window = subtitles[:200] if len(subtitles) > 200 else subtitles

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    client = get_client(api_key, base_url if base_url else None)
                    answer = chat_about_content(
                        client, model, question, context_window, st.session_state.chat_history
                    )
                st.markdown(answer)

            st.session_state.chat_history.append({"role": "user", "content": question})
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
