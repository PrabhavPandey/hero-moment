import streamlit as st
import os
import tempfile
import subprocess
import json
import requests
import google.generativeai as genai

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

st.set_page_config(page_title="vibe check", page_icon="✦", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
    .stApp { background: #0a0a0b; }
    .main .block-container { max-width: 640px; padding: 3rem 1rem 4rem 1rem; }
    .hero-title { font-size: 2.2rem; font-weight: 600; color: #fafafa; letter-spacing: -0.03em; margin-bottom: 0.3rem; }
    .hero-subtitle { color: #6b6b6b; font-size: 1rem; margin-bottom: 2.5rem; }
    [data-testid="stFileUploader"] { background: #141415; border: 1px dashed #2a2a2b; border-radius: 12px; padding: 1rem; }
    .stButton > button { background: #fafafa; color: #0a0a0b; border: none; border-radius: 8px; font-weight: 500; padding: 0.6rem 1.5rem; width: 100%; margin-top: 1rem; }
    .stButton > button:hover { background: #e0e0e0; }
    .timestamp-pill { display: inline-block; background: #1a1a1b; color: #fafafa; padding: 0.4rem 0.9rem; border-radius: 100px; font-size: 0.85rem; font-weight: 500; font-family: monospace; margin-bottom: 1rem; }
    .context-box { background: #141415; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }
    .context-label { color: #4a4a4a; font-size: 0.7rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
    .context-text { color: #8a8a8a; font-size: 0.85rem; line-height: 1.4; }
    .bullet-list { list-style: none; padding: 0; margin: 0.3rem 0 0 0; }
    .bullet-list li { color: #d0d0d0; font-size: 1.05rem; line-height: 1.7; padding-left: 1.4rem; position: relative; margin-bottom: 0.6rem; }
    .bullet-list li::before { content: "→"; position: absolute; left: 0; color: #5a5a5a; }
    .section-label { color: #6b6b6b; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.05em; margin-bottom: 0.8rem; }
    .progress-step { color: #6b6b6b; font-size: 0.85rem; padding: 0.3rem 0; }
    .progress-step.done { color: #4ade80; }
    audio { width: 100%; border-radius: 8px; margin: 0.5rem 0 1rem 0; }
    .stDownloadButton > button { background: transparent; color: #6b6b6b; border: 1px solid #2a2a2b; font-size: 0.85rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; background: #141415; border-radius: 10px; padding: 4px; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #6b6b6b; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { background: #2a2a2b; color: #fafafa; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
    .stTextInput > div > div > input { background: #141415; border: 1px solid #2a2a2b; border-radius: 10px; color: #fafafa; padding: 0.8rem 1rem; }
    .stTextInput > div > div > input::placeholder { color: #4a4a4b; }
    #MainMenu, footer, header { visibility: hidden; }
    .stAlert { background: #1a1a1b; border: none; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="hero-title">✦ vibe check</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">find the most compelling 45 seconds from any Round1 audio.</p>', unsafe_allow_html=True)

PROMPT = """You're helping a hiring manager find the single most impressive ~45 second clip from this interview.

Listen to the ENTIRE interview first. Pick the absolute strongest moment where the candidate shines.

If a clip demonstrates any one or a combination of these, include it:
1. Shows they are truly hungry, or covers the "why" of why they want this role/this line of work.
2. Is genuinely good to speak to.
3. Clearly understands their work, is a top percentile performer in their field.

STRICT RULES:
1. CANDIDATE ONLY - never include interviewer's voice
2. ONE CONTINUOUS ~45 SECOND SEGMENT - no stitching, no dull moments
3. NO intros, bios, generic process descriptions, or surface-level answers
4. The verbatim MUST be the EXACT words spoken between start and end timestamps

Return JSON only:
{
  "start_time_seconds": number,
  "end_time_seconds": number,
  "context": "1-2 sentences: what role/company is this for, and what specific thing are they explaining in this clip",
  "verbatim": "EXACT transcript of what the candidate says in the clip",
  "vibe": ["trait 1", "trait 2"],
  "red_flag": "the red flag observation"
}

VIBE = 2 bullets about the candidate based on the ENTIRE interview:
- Two strengths (informal, lowercase, e.g. "knows their shit", "thinks like a founder")

RED FLAG⛳️ = 1 bullet about the candidate based on the ENTIRE interview:
- One weakness or area to improve, with brief advice.
- eg: he BS'd on his resume. when pressed on a key data loss metric, he admitted it was an 'estimation' because the prior system lacked observability, which is a major red flag for resume inflation.

"""

def extract_clip(input_path, start, end, output_path):
    """Extract audio clip using two-step process for ogg compatibility"""
    wav_path = output_path.replace('.mp3', '.wav')
    
    # Decode to wav first (avoids ogg seeking issues)
    if subprocess.run(['ffmpeg', '-y', '-i', input_path, '-ar', '44100', '-ac', '2', wav_path], 
                      capture_output=True).returncode != 0:
        return False
    
    # Extract segment from wav
    result = subprocess.run(['ffmpeg', '-y', '-ss', str(start), '-i', wav_path, '-t', str(end - start),
                            '-c:a', 'libmp3lame', '-q:a', '2', output_path], capture_output=True)
    os.unlink(wav_path)
    
    return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000


def analyze(audio_path, progress):
    """Send to Gemini and get hero moment"""
    progress.markdown('<p class="progress-step">🔍 gemini is doing its thing...</p>', unsafe_allow_html=True)
    progress.markdown('<img src="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZ2ZhZmk0M3I3MWNzbzU3bXkxcW84aWNtbmJwbnZ0M2Z6Nm0wZG1xYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/DfSXiR60W9MVq/giphy.gif" width="300" style="margin-bottom: 1rem; border-radius: 8px;">', unsafe_allow_html=True)
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    try:
        uploaded = genai.upload_file(audio_path)
        response = model.generate_content([uploaded, PROMPT], generation_config={"response_mime_type": "application/json"})
        text = response.text
        
        # Parse JSON
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def process(audio_path, progress):
    """Process audio and display results"""
    result = analyze(audio_path, progress)
    if not result:
        os.unlink(audio_path)
        return
    
    progress.empty()
    
    start, end = result.get('start_time_seconds'), result.get('end_time_seconds')
    if start is None or end is None:
        st.error("Invalid timestamps")
        os.unlink(audio_path)
        return
    
    # Timestamp pill
    st.markdown(f'<span class="timestamp-pill">{int(start//60)}:{int(start%60):02d} → {int(end//60)}:{int(end%60):02d}</span>', unsafe_allow_html=True)
    
    # Context
    if result.get('context'):
        st.markdown(f'<div class="context-box"><p class="context-label">context</p><p class="context-text">{result["context"]}</p></div>', unsafe_allow_html=True)
    
    # Extract and play audio
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        clip_path = f.name
    
    if extract_clip(audio_path, start, end, clip_path):
        with open(clip_path, 'rb') as f:
            audio_bytes = f.read()
        os.unlink(clip_path)
        st.audio(audio_bytes, format='audio/mp3')
        st.download_button("download clip", audio_bytes, "hero_clip.mp3", "audio/mp3")
    else:
        st.error("Failed to extract audio clip")
    
    # Verbatim
    if result.get('verbatim'):
        with st.expander("verbatim transcript"):
            st.markdown(f'*"{result["verbatim"]}"*')
    
    # Vibe
    if result.get('vibe'):
        st.markdown('<p class="section-label">vibe check</p>', unsafe_allow_html=True)
        bullets = ''.join(f'<li>{v.lower()}</li>' for v in result['vibe'])
        st.markdown(f'<ul class="bullet-list">{bullets}</ul>', unsafe_allow_html=True)

    # Red Flag
    if result.get('red_flag'):
        st.markdown('<p class="section-label" style="color: #ff4b4b; margin-top: 1rem;">red flag ⛳️</p>', unsafe_allow_html=True)
        st.markdown(f'<ul class="bullet-list"><li>{result["red_flag"].lower()}</li></ul>', unsafe_allow_html=True)
    
    os.unlink(audio_path)
    st.balloons()

def main():
    if not GEMINI_API_KEY:
        st.error("Set GEMINI_API_KEY in secrets")
        return
    
    if 'processed_url' not in st.session_state:
        st.session_state.processed_url = None

    tab1, tab2 = st.tabs(["paste link", "upload file"])
    
    with tab1:
        url = st.text_input("url", placeholder="https://...ogg", label_visibility="collapsed")
        if url and url.startswith('http') and url != st.session_state.processed_url:
            progress = st.container()
            progress.markdown('<p class="progress-step">⬇️ downloading...</p>', unsafe_allow_html=True)
            try:
                resp = requests.get(url, timeout=120, stream=True)
                ext = url.split('.')[-1].split('?')[0][:4] or 'ogg'
                with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                    progress.markdown('<p class="progress-step done">✓ downloaded</p>', unsafe_allow_html=True)
                    process(f.name, progress)
                    st.session_state.processed_url = url
            except Exception as e:
                st.error(f"Download failed: {e}")
    
    with tab2:
        uploaded = st.file_uploader("upload", type=['ogg', 'oga', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
        if uploaded and st.button("find hero moment"):
            progress = st.container()
            ext = uploaded.name.split('.')[-1].lower()
            with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
                f.write(uploaded.getvalue())
                process(f.name, progress)


if __name__ == "__main__":
    main()
