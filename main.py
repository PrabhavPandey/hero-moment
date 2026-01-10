import streamlit as st
import os
import tempfile
import subprocess
import json
import requests
import google.generativeai as genai

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

st.set_page_config(
    page_title="hero moment",
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
        color: #8a8a8a; font-size: 0.85rem; line-height: 1.5;
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

st.markdown('<h1 class="hero-title">✦ hero moment</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">find the most compelling 30 seconds from any interview</p>', unsafe_allow_html=True)


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


def download_audio(url):
    """Download audio from URL"""
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        ext = url.split('.')[-1].split('?')[0][:4] or 'ogg'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
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


def analyze_interview(audio_path):
    """Send audio to Gemini and get hero moment"""
    genai.configure(api_key=GEMINI_API_KEY)
    
    prompt = """You're a hiring manager. Find the ~45 second clip that would most convince you to hire this person.

Return JSON only:
{
  "start_time_seconds": number,
  "end_time_seconds": number,
  "question": "the interviewer's question that prompted this answer",
  "summary": "one line: what the candidate is talking about",
  "verbatim_snippet": "exact words spoken",
  "vibe": ["short punchy insight", "another insight", "third insight"]
}

For vibe: be concise, lowercase, no fluff. what actually stands out about this person."""

    model = genai.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content([genai.upload_file(audio_path), prompt])
    return response.text


def process_audio(audio_path):
    """Process audio file and display results"""
    raw = analyze_interview(audio_path)
    result = parse_response(raw)
    
    if not result:
        st.error("failed to parse response")
        os.unlink(audio_path)
        return
    
    st.markdown('<div class="result-section">', unsafe_allow_html=True)
    
    start = result.get('start_time_seconds')
    end = result.get('end_time_seconds')
    
    if start is not None and end is not None:
        st.markdown(f'<span class="timestamp-pill">{int(start//60)}:{int(start%60):02d} → {int(end//60)}:{int(end%60):02d}</span>', unsafe_allow_html=True)
        
        # Context box
        question = result.get('question', '')
        summary = result.get('summary', '')
        if question or summary:
            st.markdown('<div class="context-box">', unsafe_allow_html=True)
            if question:
                st.markdown(f'<p class="context-label">question</p><p class="context-text">{question}</p>', unsafe_allow_html=True)
            if summary:
                st.markdown(f'<p class="context-label" style="margin-top: 0.8rem;">what they\'re saying</p><p class="context-text">{summary}</p>', unsafe_allow_html=True)
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
        with st.expander("the clip (tap to read)"):
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


def main():
    if not GEMINI_API_KEY:
        st.error("set GEMINI_API_KEY in secrets")
        return

    tab1, tab2 = st.tabs(["paste link", "upload file"])
    
    with tab1:
        url = st.text_input("audio url", placeholder="https://...ogg", label_visibility="collapsed")
        if url:
            st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>🔗 {url[:50]}...</p>", unsafe_allow_html=True)
        
        if st.button("find hero moment", key="url_btn", disabled=not url):
            with st.spinner("downloading..."):
                audio_path = download_audio(url)
            if audio_path:
                with st.spinner("analyzing..."):
                    process_audio(audio_path)
    
    with tab2:
        uploaded = st.file_uploader("upload", type=['ogg', 'oga', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
        if uploaded:
            st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>📎 {uploaded.name}</p>", unsafe_allow_html=True)
        
        if st.button("find hero moment", key="upload_btn", disabled=not uploaded):
            with st.spinner("analyzing..."):
                ext = uploaded.name.split('.')[-1].lower()
                with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
                    f.write(uploaded.getvalue())
                    audio_path = f.name
                process_audio(audio_path)


if __name__ == "__main__":
    main()
