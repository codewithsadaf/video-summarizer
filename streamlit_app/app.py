"""
AI Video Summarizer Streamlit App

Features:
- Fetches transcript from YouTube videos using Supadata.
- Summarizes video content using OpenAI.
- Allows AI chat on the video transcript for questionns, summaries, main ideas and quizzes.
"""
import streamlit as st
import os
import time
from dotenv import load_dotenv
from supadata import Supadata
from supadata.types import BatchJob
from openai import OpenAI

load_dotenv()

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supadata = Supadata(api_key=SUPADATA_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="AI Video Summarizer", layout="wide")

st.title("🎥 AI Video Summarizer")

if "transcript_chunks" not in st.session_state:
    st.session_state.transcript_chunks = None

if "plain_transcript" not in st.session_state:
    st.session_state.plain_transcript = ""

if "chat" not in st.session_state:
    st.session_state.chat = []

video_url = st.text_input(
    "YouTube / Video URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

if st.button("Fetch Transcript"):
    if not video_url:
        st.warning("Enter a video URL")
        st.stop()

    with st.spinner("Fetching transcript..."):
        job = supadata.transcript(
            url=video_url,
            text=False,
            mode="auto"
        )

        if isinstance(job, BatchJob):
            while True:
                job = supadata.jobs.get(job.id)
                if job.status == "completed":
                    result = job.result
                    break
                if job.status == "failed":
                    st.error("Transcript failed")
                    st.stop()
                time.sleep(2)
        else:
            result = job

        st.session_state.transcript_chunks = result.content
        st.session_state.plain_transcript = " ".join(
            [c.text for c in result.content]
        )

        st.success("Transcript ready!")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("📜 Transcript")

    if st.session_state.transcript_chunks:
        tabs = st.tabs(["Transcript", "Subtitles"])
        with tabs[0]:
            st.text_area(
                "",
                st.session_state.plain_transcript,
                height=400
            )
            st.download_button(
                "⬇️ Download Transcript",
                data=st.session_state.plain_transcript,
                file_name="transcript.txt",
                mime="text/plain"
            )

        with tabs[1]:
            timestamped_text = []
            for chunk in st.session_state.transcript_chunks:
                sec = chunk.offset // 1000
                ts_line = f"[{sec//60:02d}:{sec%60:02d}] {chunk.text}"
                timestamped_text.append(ts_line)
                st.markdown(ts_line)

            st.download_button(
                "⬇️ Download Subtitles",
                data="\n".join(timestamped_text),
                file_name="subtitles.txt",
                mime="text/plain"
            )

            
    else:
        st.info("Fetch a transcript to view it here")

with right:
    st.subheader("🤖 AI Agent")

    if not st.session_state.plain_transcript:
        st.info("Transcript required for AI chat")
        st.stop()

    # Default prompts
    col1, col2, col3 = st.columns(3)

    def ask_ai(prompt):
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant helping analyze a video transcript."
            },
            {
                "role": "user",
                "content": f"Transcript:\n{st.session_state.plain_transcript}\n\n{prompt}"
            }
        ]

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        answer = response.choices[0].message.content
        st.session_state.chat.append(("user", prompt))
        st.session_state.chat.append(("assistant", answer))

    with col1:
        if st.button("📝 Summary"):
            ask_ai("Give a concise summary of this video.")

    with col2:
        if st.button("🧠 Main Idea"):
            ask_ai("Explain the main idea of this video.")

    with col3:
        if st.button("❓ Quiz"):
            ask_ai(
                "Create 5 MCQs from this video. Provide answers at the end."
            )

    user_prompt = st.text_input("Ask something about the video")

    if st.button("Ask"):
        if user_prompt:
            ask_ai(user_prompt)

    for role, msg in st.session_state.chat:
        if role == "user":
            st.markdown(f"**You:** {msg}")
        else:
            st.markdown(f"**AI:** {msg}")
