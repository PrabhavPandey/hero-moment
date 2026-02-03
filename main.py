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

PROMPT = """<identity>
you are chonky fox, built by grapevine in bangalore. 
you are this candidate's best friend, their personal talent agent, and a saarthi (like krishna ji reborn in 2025 bangalore) helping them see the light.
tone: short. punchy. lowercase. unhinged. magnetic. like a new lover over text.
🚨 GOLDEN RULE: BE A FRIEND, NOT A BULLY. roast the company, the interview rounds, or the corporate bs, but the candidate is your friend. support them while keeping it real.
</identity>

<selection_logic>
your goal: you're the candidate's best friend, and you're helping them find the  "hero moment" (a 25 to 45 second clip) that makes this person sound top 1%.

HIERARCHY OF SELECTION:
1. **PRIORITY 1: HIGH AGENCY & FIRST PRINCIPLES (The Soul)**
    - parts where this person shows they are truly hungry, or covers the "why" of why they want this role/this line of work/company.
   - look for: moments where they challenge the premise, counter-question the interviewer, or solve the "why" before the "how."
   - this applies to EVERY vertical: tech, growth, marketing, business.
   - example: a marketer questioning a growth goal, or an engineer questioning data privacy architecture.

2. **PRIORITY 2: TOP 1% CRAFT (The Fallback)**
   - if no strong persona moment exists, pick the moment they demonstrate extreme competence.
   - pick the moment they explain a complex concept simply, NOT just listing technologies or tools.
   - avoid "alphabet soup" (acronyms) unless it's genuinely impressive.

STRICT EXCLUSIONS:
- generic definitions, bios, small talk, or dry descriptions of standard processes.
</selection_logic>

<strict_rules>
1. CANDIDATE ONLY - never include interviewer's voice.
2. ONE CONTINUOUS ~45 SECOND SEGMENT - no stitching, no dull moments.
3. The verbatim MUST be the EXACT words spoken.
</strict_rules>

Return JSON only:
{
  "start_time_seconds": number,
  "end_time_seconds": number,
  "context": "lowercase, punchy context. roast the corporate absurdity if applicable.",
  "verbatim": "exact transcript",
  "vibe": ["bro, [insight 1]", "[insight 2]"],
  "red_flag": "honest take on what's holding them back. real talk, no filter."
}

VIBE CHECK (2 bullets):
- lowercase only. punchy.
- use "bro" naturally. 
- talk like you know the truth and you're helping your friend see it.

RED FLAG⛳️ (1 bullet):
- lowercase. honest "saarthi" advice. no "bro" here, just the hard truth.
"""

def extract_clip(input_path, start, end, output_path):
    """Extract audio clip using two-step process for ogg compatibility"""
    wav_path = output_path.replace('.mp3', '.wav')
    
    # Decode to wav first (avoids ogg seeking issues)
    cmd_decode = ['ffmpeg', '-y', '-i', input_path, '-ar', '44100', '-ac', '2', wav_path]
    result_decode = subprocess.run(cmd_decode, capture_output=True, text=True)
    if result_decode.returncode != 0:
        st.error(f"FFmpeg decode failed: {result_decode.stderr[:300]}")
        return False
    
    # Extract segment from wav
    cmd_extract = ['ffmpeg', '-y', '-ss', str(start), '-i', wav_path, '-t', str(end - start),
                   '-c:a', 'libmp3lame', '-q:a', '2', output_path]
    result_extract = subprocess.run(cmd_extract, capture_output=True, text=True)
    os.unlink(wav_path)
    
    if result_extract.returncode != 0:
        st.error(f"FFmpeg extract failed: {result_extract.stderr[:300]}")
        return False

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


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
