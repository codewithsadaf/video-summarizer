"""
AI Video Summarizer Streamlit App

Features:
- Fetches transcript from YouTube videos using Supadata.
- Summarizes video content using OpenAI.
- Allows AI chat on the video transcript for questions, summaries, main ideas and quizzes.
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

if "processing" not in st.session_state:
    st.session_state.processing = False

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

def ask_ai(prompt):
    """Process AI request and add to chat history"""
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
    st.session_state.processing = False
    st.session_state.pending_prompt = None

if st.session_state.pending_prompt and st.session_state.plain_transcript:
    with st.spinner("Processing..."):
        ask_ai(st.session_state.pending_prompt)

# Video URL input
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
        st.session_state.chat = []  

        st.success("Transcript ready!")

if st.session_state.transcript_chunks:
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("📜 Transcript")
        
        tabs = st.tabs(["Transcript", "Subtitles"])
        with tabs[0]:
            st.text_area(
                "",
                st.session_state.plain_transcript,
                height=400,
                key="transcript_display"
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

    with right:
        st.subheader("🤖 AI Agent")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📝 Summary", key="btn_summary", disabled=st.session_state.processing):
                st.session_state.processing = True
                st.session_state.pending_prompt = "Give a concise summary of this video."
                st.rerun()

        with col2:
            if st.button("🧠 Main Idea", key="btn_main", disabled=st.session_state.processing):
                st.session_state.processing = True
                st.session_state.pending_prompt = "Explain the main idea of this video."
                st.rerun()

        with col3:
            if st.button("❓ Quiz", key="btn_quiz", disabled=st.session_state.processing):
                st.session_state.processing = True
                st.session_state.pending_prompt = "Create 5 MCQs from this video. Provide answers at the end."
                st.rerun()
                
        with col4:
            if st.button("📊 Presentation", key="btn_presentation", disabled=st.session_state.processing):
                st.session_state.processing = True
                st.session_state.pending_prompt = "Prepare a slide-wise presentation outline of this video transcript. Use bullet points for each slide."
                st.rerun()

        if st.session_state.chat:
            st.markdown("---")
            for i in range(0, len(st.session_state.chat), 2):
                if i + 1 < len(st.session_state.chat):
                    user_msg = st.session_state.chat[i][1]
                    ai_msg = st.session_state.chat[i + 1][1]

                    expanded = (i >= len(st.session_state.chat) - 2)

                    with st.expander(f"💬 {user_msg}", expanded=expanded):
                        st.markdown(f"**AI:** {ai_msg}")

        st.markdown("---")
        user_input = st.text_input(
            "Ask anything about the video",
            key="user_question",
            placeholder="Ask anything about the video...",
            disabled=st.session_state.processing
        )
        
        if st.button("Ask", key="ask_button", disabled=st.session_state.processing or not user_input):
            if user_input:
                st.session_state.processing = True
                st.session_state.pending_prompt = user_input
                st.rerun()

else:
    st.info("👆 Fetch a transcript to get started")