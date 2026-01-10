import streamlit as st
import os
import tempfile
import re
import subprocess
import json
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
        font-weight: 500; font-family: 'SF Mono', monospace; margin-bottom: 1.2rem;
    }
    .context-text {
        color: #6b6b6b; font-size: 0.85rem; font-style: italic;
        margin-bottom: 0.5rem; padding-left: 0.2rem;
    }
    .section-label {
        color: #6b6b6b; font-size: 0.75rem; font-weight: 500;
        letter-spacing: 0.05em; margin-bottom: 0.8rem;
    }
    .transcript-text {
        background: #141415; border-radius: 10px; padding: 1.2rem;
        color: #d4d4d4; font-size: 0.95rem; line-height: 1.7;
        font-style: italic; margin-bottom: 1.5rem;
    }
    .vibe-list { list-style: none; padding: 0; margin: 0; }
    .vibe-list li {
        color: #a0a0a0; font-size: 0.9rem; line-height: 1.6;
        padding-left: 1.2rem; position: relative; margin-bottom: 0.5rem;
    }
    .vibe-list li::before { content: "→"; position: absolute; left: 0; color: #4a4a4a; }
    
    audio { width: 100%; border-radius: 8px; margin: 1rem 0; }
    
    .stDownloadButton > button {
        background: transparent; color: #6b6b6b;
        border: 1px solid #2a2a2b; font-size: 0.85rem;
    }
    .stDownloadButton > button:hover {
        background: #141415; color: #fafafa; border-color: #3a3a3b;
    }
    
    #MainMenu, footer, header { visibility: hidden; }
    .stAlert { background: #1a1a1b; border: none; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="hero-title">✦ hero moment</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">find the most compelling 30 seconds from any interview</p>', unsafe_allow_html=True)


def parse_response(text):
    """Parse JSON from Gemini response"""
    try:
        # Strip markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return json.loads(text.strip())
    except:
        # Fallback: find JSON object
        try:
            start, end = text.find('{'), text.rfind('}')
            if start != -1 and end > start:
                return json.loads(text[start:end+1])
        except:
            pass
    return None


def extract_audio(input_path, start, end, output_path):
    """Extract audio segment using ffmpeg"""
    cmd = ['ffmpeg', '-y', '-i', input_path, '-ss', str(start), '-t', str(end - start), '-c:a', 'libvorbis', '-q:a', '4', output_path]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def analyze_interview(audio_path):
    """Send audio to Gemini and get hero moment"""
    genai.configure(api_key=GEMINI_API_KEY)
    
    prompt = """You're a hiring manager. Find the ~45 second clip from this interview that would most convince you to hire this person.

What clip best shows their vibe — their passion, how they think, and whether they'd be hungry to solve your problems?

Return JSON only:
{
  "start_time_seconds": number,
  "end_time_seconds": number,
  "context": "what they're responding to (so a listener has context)",
  "verbatim_snippet": "exact words spoken",
  "vibe_bullets": ["what stands out 1", "what stands out 2", "what stands out 3"]
}"""

    model = genai.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content([genai.upload_file(audio_path), prompt])
    return response.text


def main():
    if not GEMINI_API_KEY:
        st.error("set GEMINI_API_KEY in secrets")
        return

    uploaded = st.file_uploader("upload", type=['ogg', 'oga', 'mp3', 'wav', 'm4a'], label_visibility="collapsed")
    
    if uploaded:
        st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>📎 {uploaded.name}</p>", unsafe_allow_html=True)

    if st.button("find hero moment", disabled=not uploaded):
        with st.spinner("analyzing..."):
            # Save uploaded file
            ext = uploaded.name.split('.')[-1].lower()
            with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
                f.write(uploaded.getvalue())
                audio_path = f.name
            
            # Get analysis
            raw = analyze_interview(audio_path)
            
            # Debug
            with st.expander("debug"):
                st.code(raw)
            
            result = parse_response(raw)
            if not result:
                st.error("failed to parse response")
                os.unlink(audio_path)
                return
            
            # Display results
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            
            start = result.get('start_time_seconds')
            end = result.get('end_time_seconds')
            
            if start is not None and end is not None:
                st.markdown(f'<span class="timestamp-pill">{int(start//60)}:{int(start%60):02d} → {int(end//60)}:{int(end%60):02d}</span>', unsafe_allow_html=True)
                
                # Extract clip
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
                    clip_path = f.name
                
                if extract_audio(audio_path, start, end, clip_path):
                    if result.get('context'):
                        st.markdown(f'<p class="context-text">{result["context"]}</p>', unsafe_allow_html=True)
                    
                    st.audio(clip_path, format='audio/ogg')
                    
                    with open(clip_path, 'rb') as f:
                        st.download_button("download clip", f, f"hero_{uploaded.name}", "audio/ogg")
                    
                    os.unlink(clip_path)
            
            # Transcript
            if result.get('verbatim_snippet'):
                st.markdown('<p class="section-label">the clip</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="transcript-text">"{result["verbatim_snippet"]}"</div>', unsafe_allow_html=True)
            
            # Vibe
            if result.get('vibe_bullets'):
                st.markdown('<p class="section-label">what\'s their vibe</p>', unsafe_allow_html=True)
                bullets = ''.join(f'<li>{b}</li>' for b in result['vibe_bullets'])
                st.markdown(f'<ul class="vibe-list">{bullets}</ul>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.balloons()
            
            os.unlink(audio_path)


if __name__ == "__main__":
    main()
