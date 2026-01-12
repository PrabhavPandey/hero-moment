import streamlit as st
import os
import tempfile
import subprocess
import json
import requests
import google.generativeai as genai

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

st.set_page_config(
    page_title="vibe check",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    .stApp { background: #0a0a0b; }
    .main .block-container { max-width: 640px; padding: 3rem 1rem 4rem 1rem; }
    
    .hero-title {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 2.2rem; font-weight: 600; color: #fafafa;
        letter-spacing: -0.03em; margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #6b6b6b; font-size: 1rem; font-weight: 400; margin-bottom: 2.5rem;
    }
    
    [data-testid="stFileUploader"] {
        background: #141415; border: 1px dashed #2a2a2b;
        border-radius: 12px; padding: 1rem;
    }
    [data-testid="stFileUploader"]:hover { border-color: #3a3a3b; }
    
    .stButton > button {
        background: #fafafa; color: #0a0a0b; border: none;
        border-radius: 8px; font-weight: 500; font-size: 0.9rem;
        padding: 0.6rem 1.5rem; width: 100%; margin-top: 1rem;
    }
    .stButton > button:hover { background: #e0e0e0; }
    
    .result-section { margin-top: 2.5rem; padding-top: 2rem; border-top: 1px solid #1a1a1b; }
    
    .timestamp-pill {
        display: inline-block; background: #1a1a1b; color: #fafafa;
        padding: 0.4rem 0.9rem; border-radius: 100px; font-size: 0.85rem;
        font-weight: 500; font-family: 'SF Mono', monospace; margin-bottom: 1rem;
    }
    
    .context-box {
        background: #141415; border-radius: 10px; padding: 1rem;
        margin-bottom: 1rem;
    }
    .context-label {
        color: #4a4a4a; font-size: 0.7rem; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem;
    }
    .context-text {
        color: #8a8a8a; font-size: 0.85rem; line-height: 1.4;
    }
    .context-list {
        list-style: none; padding: 0; margin: 0.3rem 0 0 0;
    }
    .context-list li {
        color: #8a8a8a; font-size: 0.85rem; line-height: 1.5;
        padding-left: 1rem; position: relative; margin-bottom: 0.2rem;
    }
    .context-list li::before {
        content: "•"; position: absolute; left: 0; color: #5a5a5a;
    }
    
    .section-label {
        color: #6b6b6b; font-size: 0.75rem; font-weight: 500;
        letter-spacing: 0.05em; margin-bottom: 0.8rem;
    }
    
    .vibe-list { list-style: none; padding: 0; margin: 0; }
    .vibe-list li {
        color: #d0d0d0; font-size: 1.05rem; line-height: 1.7;
        padding-left: 1.4rem; position: relative; margin-bottom: 0.6rem;
    }
    .vibe-list li::before { content: "→"; position: absolute; left: 0; color: #5a5a5a; }
    
    .progress-step {
        color: #6b6b6b; font-size: 0.85rem; padding: 0.3rem 0;
    }
    .progress-step.done { color: #4ade80; }
    
    audio { width: 100%; border-radius: 8px; margin: 0.5rem 0 1rem 0; }
    
    .stDownloadButton > button {
        background: transparent; color: #6b6b6b;
        border: 1px solid #2a2a2b; font-size: 0.85rem;
    }
    .stDownloadButton > button:hover {
        background: #141415; color: #fafafa; border-color: #3a3a3b;
    }
    
    .streamlit-expanderHeader {
        background: #141415; border-radius: 8px;
        color: #6b6b6b; font-size: 0.85rem;
    }
    .streamlit-expanderContent {
        background: #141415; border-radius: 0 0 8px 8px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0; background: #141415; border-radius: 10px; padding: 4px; margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #6b6b6b; border-radius: 8px;
        padding: 0.5rem 1rem; font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] { background: #2a2a2b; color: #fafafa; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
    
    /* Text input */
    .stTextInput > div > div > input {
        background: #141415; border: 1px solid #2a2a2b; border-radius: 10px;
        color: #fafafa; padding: 0.8rem 1rem; font-size: 0.9rem;
    }
    .stTextInput > div > div > input:focus { border-color: #3a3a3b; box-shadow: none; }
    .stTextInput > div > div > input::placeholder { color: #4a4a4b; }
    
    #MainMenu, footer, header { visibility: hidden; }
    .stAlert { background: #1a1a1b; border: none; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="hero-title">✦ vibe check</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">find the most compelling 45 seconds from any Round1 audio.</p>', unsafe_allow_html=True)

def parse_response(text):
    """Parse JSON from Gemini response"""
    try:
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except:
        try:
            start, end = text.find('{'), text.rfind('}')
            if start != -1 and end > start:
                return json.loads(text[start:end+1])
        except:
            pass
    return None


def download_audio(url, progress_container):
    """Download audio from URL"""
    try:
        progress_container.markdown('<p class="progress-step">⬇️ downloading audio...</p>', unsafe_allow_html=True)
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        ext = url.split('.')[-1].split('?')[0][:4] or 'ogg'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
            progress_container.markdown('<p class="progress-step done">✓ downloaded</p>', unsafe_allow_html=True)
            return f.name
    except Exception as e:
        st.error(f"download failed: {e}")
        return None


def extract_audio(input_path, start, end, output_path):
    """Extract audio segment using ffmpeg"""
    cmd = [
        'ffmpeg', '-y', '-accurate_seek',
        '-ss', str(start), '-i', input_path,
        '-t', str(end - start),
        '-c:a', 'libmp3lame', '-q:a', '2',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        st.error(f"ffmpeg failed: {result.stderr[:500]}")
        return False
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        st.error("ffmpeg produced empty file")
        return False
    return True


def analyze_interview(audio_path, progress_container):
    """Send audio to Gemini and get hero moment"""
    progress_container.markdown('''
        <p class="progress-step">🔍 analyzing with gemini...</p>
        <img src="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2ZhZmk0M3I3MWNzbzU3bXkxcW84aWNtbmJwbnZ0M2Z6Nm0wZG1xYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/DfSXiR60W9MVq/giphy.gif" style="width: 200px; margin: 1rem 0; border-radius: 8px;">
    ''', unsafe_allow_html=True)
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    prompt = """Listen to this interview and pick the single best ~45 second clip that shows the candidate at their most impressive — the moment that would make any hiring manager say "I need to meet this person."

STRICT GUARDRAILS:
1. The clip must START and END with the candidate speaking. Never include the interviewer's voice.
2. CRITICAL: start_time_seconds and end_time_seconds must EXACTLY match the verbatim_snippet. The audio between those timestamps should contain precisely those words, nothing more, nothing less.

Return JSON only:
{
  "start_time_seconds": number (exact timestamp where verbatim_snippet begins),
  "end_time_seconds": number (exact timestamp where verbatim_snippet ends),
  "question": "the interviewer's question that prompted this answer (short)",
  "context": ["company/role context", "what they're explaining", "key detail"],
  "verbatim_snippet": "EXACT words spoken by the candidate between start and end timestamps",
  "vibe": ["what's great about them", "another strength", "growth area + how to work with it"]
}"""

    model = genai.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content([genai.upload_file(audio_path), prompt])
    
    progress_container.markdown('<p class="progress-step done">✓ analysis complete</p>', unsafe_allow_html=True)
    return response.text


def process_audio(audio_path, progress_container):
    """Process audio file and display results"""
    raw = analyze_interview(audio_path, progress_container)
    result = parse_response(raw)
    
    if not result:
        st.error("failed to parse response")
        os.unlink(audio_path)
        return
    
    # Clear progress
    progress_container.empty()
    
    st.markdown('<div class="result-section">', unsafe_allow_html=True)
    
    start = result.get('start_time_seconds')
    end = result.get('end_time_seconds')
    
    if start is not None and end is not None:
        st.markdown(f'<span class="timestamp-pill">{int(start//60)}:{int(start%60):02d} → {int(end//60)}:{int(end%60):02d}</span>', unsafe_allow_html=True)
        
        # Context box
        question = result.get('question', '')
        context = result.get('context', [])
        
        st.markdown('<div class="context-box">', unsafe_allow_html=True)
        if question:
            st.markdown(f'<p class="context-label">question</p><p class="context-text">{question}</p>', unsafe_allow_html=True)
        if context:
            st.markdown('<p class="context-label" style="margin-top: 0.8rem;">context</p>', unsafe_allow_html=True)
            bullets = ''.join(f'<li>{c}</li>' for c in context)
            st.markdown(f'<ul class="context-list">{bullets}</ul>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Extract and play audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            clip_path = f.name
        
        if extract_audio(audio_path, start, end, clip_path):
            with open(clip_path, 'rb') as f:
                audio_bytes = f.read()
            os.unlink(clip_path)
            
            st.audio(audio_bytes, format='audio/mp3')
            st.download_button("download clip", audio_bytes, "hero_clip.mp3", "audio/mp3")
    
    # Transcript (collapsible)
    if result.get('verbatim_snippet'):
        with st.expander("the clip's verbatim (tap to read)"):
            st.markdown(f'*"{result["verbatim_snippet"]}"*')
    
    # Vibe
    vibe = result.get('vibe') or result.get('vibe_bullets')
    if vibe:
        st.markdown('<p class="section-label">what\'s their vibe</p>', unsafe_allow_html=True)
        bullets = ''.join(f'<li>{b.lower()}</li>' for b in vibe)
        st.markdown(f'<ul class="vibe-list">{bullets}</ul>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.balloons()
    
    os.unlink(audio_path)


def is_valid_audio_url(url):
    """Check if URL looks like an audio file"""
    if not url:
        return False
    url_lower = url.lower()
    # Check for audio extensions OR known audio hosting patterns (like Azure blob with ai-interviews)
    has_audio_ext = any(ext in url_lower for ext in ['.ogg', '.mp3', '.wav', '.m4a', '.oga'])
    is_known_audio_host = 'ai-interviews' in url_lower or 'audio' in url_lower
    return url_lower.startswith('http') and (has_audio_ext or is_known_audio_host)


def main():
    if not GEMINI_API_KEY:
        st.error("set GEMINI_API_KEY in secrets")
        return
    
    # Initialize session state
    if 'processed_url' not in st.session_state:
        st.session_state.processed_url = None

    tab1, tab2 = st.tabs(["paste link", "upload file"])
    
    with tab1:
        st.markdown("<p style='color: #6b6b6b; font-size: 0.9rem; margin-bottom: 0.5rem;'>drop any round1 audio file link below</p>", unsafe_allow_html=True)
        url = st.text_input("audio url", placeholder="https://...ogg", label_visibility="collapsed", key="url_input")
        
        # Auto-process when valid URL is pasted
        if is_valid_audio_url(url) and url != st.session_state.processed_url:
            progress = st.container()
            audio_path = download_audio(url, progress)
            if audio_path:
                process_audio(audio_path, progress)
                st.session_state.processed_url = url
    
    with tab2:
        uploaded = st.file_uploader("upload", type=['ogg', 'oga', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
        if uploaded:
            st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>📎 {uploaded.name}</p>", unsafe_allow_html=True)
        
        if st.button("find hero moment", key="upload_btn", disabled=not uploaded):
            progress = st.container()
            progress.markdown('<p class="progress-step">🔍 analyzing...</p>', unsafe_allow_html=True)
            
            ext = uploaded.name.split('.')[-1].lower()
            with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
                f.write(uploaded.getvalue())
                audio_path = f.name
            process_audio(audio_path, progress)


if __name__ == "__main__":
    main()
