"""
AI Video Summarizer Streamlit App with Mindmap

Features:
- Fetches transcript from YouTube videos using Supadata.
- Summarizes video content using OpenAI.
- Generates mindmap diagrams from transcripts.
- Allows AI chat on the video transcript for questions, summaries, main ideas and quizzes.
"""
import streamlit as st
import os
import time
import json
import tempfile
import io
from dotenv import load_dotenv
from supadata import Supadata
from supadata.types import BatchJob
from openai import OpenAI
import graphviz

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

if "mindmap_data" not in st.session_state:
    st.session_state.mindmap_data = None

if "mindmap_dot" not in st.session_state:
    st.session_state.mindmap_dot = None

if "generating_mindmap" not in st.session_state:
    st.session_state.generating_mindmap = False

def generate_mindmap_structure(transcript):
    """Generate mindmap structure from transcript using OpenAI"""
    prompt = f"""
    Analyze this video transcript and create a hierarchical mindmap structure.
    The mindmap should have:
    1. A central node with the main topic
    2. 3-5 main branches (key themes/concepts)
    3. 2-3 sub-branches for each main branch
    4. Use concise labels (max 3-4 words each)
    
    Return ONLY a valid JSON structure like this:
    {{
        "central_topic": "Main Topic",
        "branches": [
            {{
                "name": "Branch 1",
                "color": "#FF6B6B",
                "children": [
                    {{"name": "Sub-topic 1", "color": "#FF8E8E"}},
                    {{"name": "Sub-topic 2", "color": "#FF8E8E"}}
                ]
            }},
            {{
                "name": "Branch 2", 
                "color": "#4ECDC4",
                "children": [
                    {{"name": "Sub-topic 3", "color": "#7FE0DB"}},
                    {{"name": "Sub-topic 4", "color": "#7FE0DB"}}
                ]
            }}
        ]
    }}
    
    Use different colors for different branches. Make it colorful!
    
    Transcript:
    {transcript[:3000]}  # Limit transcript length for API
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a mindmap structure generator. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        mindmap_json = response.choices[0].message.content.strip()
        mindmap_json = mindmap_json.replace('```json', '').replace('```', '').strip()
        
        return json.loads(mindmap_json)
    except Exception as e:
        st.error(f"Error generating mindmap: {e}")
        return None

def create_mindmap_diagram(mindmap_data):
    """Create Graphviz diagram from mindmap data"""
    try:
        dot = graphviz.Digraph(comment='Video Mindmap', format='png')
        dot.attr(bgcolor='transparent')
        dot.attr('node', shape='rectangle', style='filled', fontname='Arial', fontsize='10')
        dot.attr('edge', color='gray50', arrowsize='0.5')
        
        dot.node('center', mindmap_data['central_topic'], 
                shape='circle', style='filled', 
                fillcolor='#FFD700', fontsize='14', fontname='Arial Bold')
        
        for i, branch in enumerate(mindmap_data['branches']):
            branch_id = f"branch_{i}"
            
            dot.node(branch_id, branch['name'], 
                    fillcolor=branch['color'], 
                    fontcolor='white' if is_dark_color(branch['color']) else 'black')
            dot.edge('center', branch_id)
            
            for j, child in enumerate(branch.get('children', [])):
                child_id = f"{branch_id}_child_{j}"
                dot.node(child_id, child['name'], 
                        fillcolor=child.get('color', lighten_color(branch['color'])),
                        fontcolor='white' if is_dark_color(child.get('color', branch['color'])) else 'black')
                dot.edge(branch_id, child_id)
        
        return dot
    except Exception as e:
        st.error(f"Error creating mindmap diagram: {e}")
        return None

def create_simple_mindmap_html(mindmap_data):
    """Create a simple HTML/visual mindmap as fallback"""
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background: white; border-radius: 10px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="background: #FFD700; color: black; padding: 15px; border-radius: 50%; 
                        display: inline-block; width: 150px; height: 150px; 
                        display: flex; align-items: center; justify-content: center;
                        font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                {mindmap_data['central_topic']}
            </div>
        </div>
        
        <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 40px;">
    """
    
    for i, branch in enumerate(mindmap_data['branches']):
        html += f"""
            <div style="flex: 1; min-width: 200px; max-width: 300px;">
                <div style="background: {branch['color']}; color: white; padding: 12px; 
                            border-radius: 8px; margin-bottom: 15px; font-weight: bold;
                            text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    {branch['name']}
                </div>
                <div style="padding-left: 20px;">
        """
        
        for child in branch.get('children', []):
            html += f"""
                    <div style="background: {child.get('color', '#f0f0f0')}; padding: 8px; 
                                margin-bottom: 8px; border-radius: 5px; border-left: 4px solid {branch['color']};
                                font-size: 14px;">
                        {child['name']}
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
    
    html += """
        </div>
    </div>
    """
    
    return html

def is_dark_color(hex_color):
    """Check if a color is dark"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5

def lighten_color(hex_color, factor=0.3):
    """Lighten a hex color"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    
    return f"#{r:02x}{g:02x}{b:02x}"

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

def generate_mindmap():
    """Generate mindmap in the background"""
    if not st.session_state.plain_transcript:
        return
    
    st.session_state.generating_mindmap = True
    
    mindmap_data = generate_mindmap_structure(st.session_state.plain_transcript)
    
    if mindmap_data:
        st.session_state.mindmap_data = mindmap_data
        
        try:
            mindmap_dot = create_mindmap_diagram(mindmap_data)
            if mindmap_dot:
                st.session_state.mindmap_dot = mindmap_dot
        except Exception:
            st.session_state.mindmap_dot = None
    
    st.session_state.generating_mindmap = False

if st.session_state.pending_prompt and st.session_state.plain_transcript:
    with st.spinner("Processing..."):
        ask_ai(st.session_state.pending_prompt)

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
        st.session_state.mindmap_data = None
        st.session_state.mindmap_dot = None

        st.success("✓ Transcript ready! Mindmap will be generated...")

if st.session_state.transcript_chunks:
    if not st.session_state.mindmap_data and not st.session_state.generating_mindmap:
        placeholder = st.empty()
        with placeholder:
            with st.spinner("🎨 Generating mindmap..."):
                generate_mindmap()
        placeholder.empty()
    
    left, right = st.columns([1.2, 1])

    with left:
        tabs = st.tabs(["Transcript", "Subtitles", "Mind Map"])
        
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
        
        with tabs[2]: 
            if st.session_state.mindmap_data:
                if st.session_state.mindmap_dot:
                    try:
                        st.graphviz_chart(st.session_state.mindmap_dot, use_container_width=True)
                        
                        try:
                            from graphviz import Digraph
                            import tempfile
                            
                            temp_dir = tempfile.mkdtemp()
                            file_path = os.path.join(temp_dir, "mindmap")
                            
                            st.session_state.mindmap_dot.render(file_path, format='png', cleanup=True)
                            
                            with open(file_path + ".png", "rb") as f:
                                png_data = f.read()
                            
                            st.download_button(
                                label="⬇️ Download Mindmap (PNG)",
                                data=png_data,
                                file_name="mindmap.png",
                                mime="image/png"
                            )
                            
                        except Exception as e:
                            pass
                            
                    except Exception:
                        st.warning("⚠️ Graphviz not available. Showing simplified mindmap.")
                        html_mindmap = create_simple_mindmap_html(st.session_state.mindmap_data)
                        st.markdown(html_mindmap, unsafe_allow_html=True)
                
                else:
                    st.info("📊 Showing simplified mindmap (Graphviz not available)")
                    html_mindmap = create_simple_mindmap_html(st.session_state.mindmap_data)
                    st.markdown(html_mindmap, unsafe_allow_html=True)
                    
            elif st.session_state.generating_mindmap:
                st.info("🎨 Generating mindmap... Please wait.")
            else:
                if st.button("🔄 Regenerate Mindmap", type="primary"):
                    st.session_state.mindmap_data = None
                    st.session_state.mindmap_dot = None
                    st.rerun()

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
        if "chat_input_key" not in st.session_state:
            st.session_state.chat_input_key = 0
        
        user_input = st.text_input(
            "Ask anything about the video",
            key=f"user_question_{st.session_state.chat_input_key}",
            placeholder="Ask anything about the video...",
            disabled=st.session_state.processing
        )
        
        if st.button("Ask", key="ask_button", disabled=st.session_state.processing or not user_input):
            if user_input:
                st.session_state.processing = True
                st.session_state.pending_prompt = user_input
                st.session_state.chat_input_key += 1
                st.rerun()

else:
    st.info("👆 Fetch a transcript to get started")