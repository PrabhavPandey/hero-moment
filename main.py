import streamlit as st
import os
import tempfile
import re
import subprocess
import json
import google.generativeai as genai

# Get API key from Streamlit secrets (for deployment) or fallback for local dev
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

st.set_page_config(
    page_title="hero moment",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar completely and apply minimal dark theme
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    
    .stApp {
        background: #0a0a0b;
    }
    
    .main .block-container {
        max-width: 640px;
        padding: 3rem 1rem 4rem 1rem;
    }
    
    /* Typography */
    .hero-title {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 2.2rem;
        font-weight: 600;
        color: #fafafa;
        letter-spacing: -0.03em;
        margin-bottom: 0.3rem;
    }
    
    .hero-subtitle {
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #6b6b6b;
        font-size: 1rem;
        font-weight: 400;
        margin-bottom: 2.5rem;
    }
    
    /* Upload area */
    [data-testid="stFileUploader"] {
        background: #141415;
        border: 1px dashed #2a2a2b;
        border-radius: 12px;
        padding: 1rem;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #3a3a3b;
    }
    
    /* Button */
    .stButton > button {
        background: #fafafa;
        color: #0a0a0b;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.9rem;
        padding: 0.6rem 1.5rem;
        transition: all 0.15s ease;
        width: 100%;
        margin-top: 1rem;
    }
    
    .stButton > button:hover {
        background: #e0e0e0;
        color: #0a0a0b;
    }
    
    /* Results section */
    .result-section {
        margin-top: 2.5rem;
        padding-top: 2rem;
        border-top: 1px solid #1a1a1b;
    }
    
    .timestamp-pill {
        display: inline-block;
        background: #1a1a1b;
        color: #fafafa;
        padding: 0.4rem 0.9rem;
        border-radius: 100px;
        font-size: 0.85rem;
        font-weight: 500;
        font-family: 'SF Mono', 'Menlo', monospace;
        margin-bottom: 1.2rem;
    }
    
    .context-text {
        color: #6b6b6b;
        font-size: 0.85rem;
        font-style: italic;
        margin-bottom: 0.5rem;
        padding-left: 0.2rem;
    }
    
    .section-label {
        color: #6b6b6b;
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.05em;
        margin-bottom: 0.8rem;
    }
    
    .transcript-text {
        background: #141415;
        border-radius: 10px;
        padding: 1.2rem;
        color: #d4d4d4;
        font-size: 0.95rem;
        line-height: 1.7;
        font-style: italic;
        margin-bottom: 1.5rem;
    }
    
    .explanation-text {
        color: #a0a0a0;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    
    .vibe-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .vibe-list li {
        color: #a0a0a0;
        font-size: 0.9rem;
        line-height: 1.6;
        padding-left: 1.2rem;
        position: relative;
        margin-bottom: 0.5rem;
    }
    
    .vibe-list li::before {
        content: "→";
        position: absolute;
        left: 0;
        color: #4a4a4a;
    }
    
    /* Audio player */
    audio {
        width: 100%;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #fafafa transparent transparent transparent;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: transparent;
        color: #6b6b6b;
        border: 1px solid #2a2a2b;
        font-size: 0.85rem;
    }
    
    .stDownloadButton > button:hover {
        background: #141415;
        color: #fafafa;
        border-color: #3a3a3b;
    }
    
    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: transparent;
        color: #6b6b6b;
        font-size: 0.85rem;
    }
    
    /* Error/warning boxes */
    .stAlert {
        background: #1a1a1b;
        border: none;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="hero-title">✦ hero moment</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">find the most compelling 30 seconds from any interview</p>', unsafe_allow_html=True)

def parse_json_response(response_text):
    """Parse JSON response from Gemini"""
    try:
        # Clean up markdown code blocks
        clean_text = response_text.strip()
        if '```json' in clean_text:
            clean_text = clean_text.split('```json')[1]
        if '```' in clean_text:
            clean_text = clean_text.split('```')[0]
        clean_text = clean_text.strip()
        
        # Try parsing as JSON
        if clean_text.startswith('{'):
            return json.loads(clean_text)
        
        # Try to find JSON object in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx + 1]
            return json.loads(json_str)
        
        return None
    except:
        return None

def normalize_timestamps(result):
    """Ensure timestamps are numeric seconds"""
    start = result.get('start_time_seconds')
    end = result.get('end_time_seconds')
    
    # Convert string timestamps like "1:30" to seconds
    if isinstance(start, str) and ':' in start:
        parts = start.split(':')
        start = int(parts[0]) * 60 + int(parts[1])
    if isinstance(end, str) and ':' in end:
        parts = end.split(':')
        end = int(parts[0]) * 60 + int(parts[1])
    
    # Ensure they're numbers
    try:
        result['start_time_seconds'] = float(start) if start is not None else None
        result['end_time_seconds'] = float(end) if end is not None else None
    except:
        pass
    
    return result

def fallback_parse_response(response_text):
    """Fallback parsing for non-JSON responses"""
    result = {
        'start_time_seconds': None,
        'end_time_seconds': None,
        'context': None,
        'verbatim_snippet': None,
        'vibe_bullets': None
    }
    
    # Try JSON-style extraction for each field
    start_match = re.search(r'"start_time_seconds"\s*:\s*(\d+(?:\.\d+)?)', response_text)
    end_match = re.search(r'"end_time_seconds"\s*:\s*(\d+(?:\.\d+)?)', response_text)
    if start_match and end_match:
        result['start_time_seconds'] = float(start_match.group(1))
        result['end_time_seconds'] = float(end_match.group(1))
    
    # Extract verbatim_snippet specifically (not just any quote)
    snippet_match = re.search(r'"verbatim_snippet"\s*:\s*"([^"]+)"', response_text)
    if snippet_match:
        result['verbatim_snippet'] = snippet_match.group(1)
    
    # Extract context
    context_match = re.search(r'"context"\s*:\s*"([^"]+)"', response_text)
    if context_match:
        result['context'] = context_match.group(1)
    
    # Extract vibe_bullets array
    bullets_match = re.search(r'"vibe_bullets"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
    if bullets_match:
        bullets_str = bullets_match.group(1)
        bullets = re.findall(r'"([^"]+)"', bullets_str)
        if bullets:
            result['vibe_bullets'] = bullets
    
    return result

def extract_audio_segment(audio_path, start_seconds, end_seconds, output_path):
    """Extract a segment from the audio file using ffmpeg"""
    try:
        duration = end_seconds - start_seconds
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-ss', str(start_seconds),
            '-t', str(duration),
            '-c:a', 'libvorbis',
            '-q:a', '4',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        st.error(f"Error extracting audio: {str(e)}")
        return False

def process_with_gemini(audio_path, api_key):
    """Process audio using Gemini API to find the hero moment"""
    try:
        genai.configure(api_key=api_key)
        
        audio_file = genai.upload_file(audio_path)
        
        prompt = """Find the single best "hero moment" (30–45 seconds) from this interview.

Find moments where the candidate:
- Shows ownership (built something, led a project, took initiative)
- Demonstrates impact (real numbers, outcomes, growth)
- Reveals their vibe: energy, clarity, storytelling, passion

Prefer concrete examples over vague claims. Only include the CANDIDATE speaking.

Return in JSON format:
{
  "start_time_seconds": <number>,
  "end_time_seconds": <number>,
  "verbatim_snippet": "<exact transcript>",
  "context": "<1-2 sentences explaining what question was asked or what topic the candidate is responding to — so a listener understands what they're about to hear>",
  "vibe_bullets": ["<punchy bullet 1>", "<punchy bullet 2>", "<punchy bullet 3>"]
}

Constraints:
- Duration: 30-45 seconds
- Only the CANDIDATE speaking (no interviewer)"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([audio_file, prompt])
        
        return response.text
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def main():
    if not GEMINI_API_KEY:
        st.error("Please set GEMINI_API_KEY in Streamlit secrets")
        return

    uploaded_file = st.file_uploader(
        "Drop your interview audio here",
        type=['ogg', 'oga', 'mp3', 'wav', 'm4a'],
        help="Supports OGG, MP3, WAV, M4A",
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>📎 {uploaded_file.name}</p>", unsafe_allow_html=True)

    if st.button("find hero moment", disabled=not uploaded_file):
        if uploaded_file:
            with st.spinner("analyzing..."):
                process_audio(uploaded_file)

def process_audio(uploaded_file):
    """Process the uploaded audio file"""
    try:
        audio_data = uploaded_file.getvalue()
        filename = uploaded_file.name
        file_ext = filename.split('.')[-1].lower()

        with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        response_text = process_with_gemini(temp_file_path, GEMINI_API_KEY)
        
        if response_text:
            # Debug: show raw response in expander
            with st.expander("debug: raw response"):
                st.code(response_text)
            
            # Try JSON parsing first, fallback to regex
            result = parse_json_response(response_text)
            if not result:
                st.warning("JSON parsing failed, using fallback")
                result = fallback_parse_response(response_text)
            
            # Normalize timestamps to ensure they're numeric
            result = normalize_timestamps(result)
            
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            
            start_time = result.get('start_time_seconds')
            end_time = result.get('end_time_seconds')
            
            if start_time is not None and end_time is not None:
                start_str = f"{int(start_time // 60)}:{int(start_time % 60):02d}"
                end_str = f"{int(end_time // 60)}:{int(end_time % 60):02d}"
                
                st.markdown(f'<span class="timestamp-pill">{start_str} → {end_str}</span>', unsafe_allow_html=True)
                
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as hero_file:
                    hero_file_path = hero_file.name
                
                if extract_audio_segment(temp_file_path, start_time, end_time, hero_file_path):
                    # Display context first (so listener knows what they're about to hear)
                    context = result.get('context')
                    if context:
                        st.markdown(f'<p class="context-text">{context}</p>', unsafe_allow_html=True)
                    
                    st.audio(hero_file_path, format='audio/ogg')
                    
                    with open(hero_file_path, 'rb') as f:
                        st.download_button(
                            label="download clip",
                            data=f,
                            file_name=f"hero_{filename}",
                            mime="audio/ogg"
                        )
                    
                    os.unlink(hero_file_path)
            
            # Display transcript
            transcript = result.get('verbatim_snippet')
            if transcript and len(transcript) > 30:
                st.markdown('<p class="section-label">the clip</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="transcript-text">"{transcript}"</div>', unsafe_allow_html=True)
            
            # Display vibe bullets
            vibe_bullets = result.get('vibe_bullets') or result.get('reason')
            if vibe_bullets:
                st.markdown('<p class="section-label">what\'s their vibe</p>', unsafe_allow_html=True)
                if isinstance(vibe_bullets, list):
                    bullets_html = ''.join([f'<li>{bullet}</li>' for bullet in vibe_bullets])
                    st.markdown(f'<ul class="vibe-list">{bullets_html}</ul>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="explanation-text">{vibe_bullets}</p>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Confetti celebration
            st.balloons()

        os.unlink(temp_file_path)

    except Exception as e:
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
