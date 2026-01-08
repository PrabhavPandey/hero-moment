import streamlit as st
import os
import tempfile
import requests
import re
import google.generativeai as genai
from pydub import AudioSegment

# Get API key from Streamlit secrets (for deployment) or fallback for local dev
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

st.set_page_config(
    page_title="Hero Moment",
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
    
    .section-label {
        color: #6b6b6b;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
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
st.markdown('<h1 class="hero-title">✦ Hero Moment</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Find the most compelling 30 seconds from any interview</p>', unsafe_allow_html=True)

def parse_timestamp(timestamp_str):
    """Parse timestamp string like '0:45' or '1:25' to seconds"""
    try:
        parts = timestamp_str.strip().split(':')
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return int(timestamp_str)
    except:
        return None

def extract_timestamps_from_response(response_text):
    """Extract start and end timestamps from Gemini response"""
    patterns = [
        r'(\d{1,2}:\d{2})\s*[-–to]+\s*(\d{1,2}:\d{2})',
        r'from\s*(\d{1,2}:\d{2})\s*to\s*(\d{1,2}:\d{2})',
        r'(\d{1,2}:\d{2})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple) and len(matches[0]) == 2:
                start_time = parse_timestamp(matches[0][0])
                end_time = parse_timestamp(matches[0][1])
                if start_time is not None and end_time is not None:
                    return start_time, end_time
            elif isinstance(matches[0], str):
                start_time = parse_timestamp(matches[0])
                if start_time is not None:
                    return start_time, start_time + 45
    
    return None, None

def extract_transcript_from_response(response_text):
    """Extract the transcript portion from the response"""
    # Look for text between quotes that's substantial
    quote_matches = re.findall(r'"([^"]{30,})"', response_text)
    if quote_matches:
        # Return the longest quote found
        return max(quote_matches, key=len)
    
    # Look for text after "Transcript:" until next section
    transcript_match = re.search(r'[Tt]ranscript[:\s]*\n+"?([^"]+)"?(?=\n\n|\n\d\.|\nWhy|\n\*\*)', response_text, re.DOTALL)
    if transcript_match:
        text = transcript_match.group(1).strip().strip('"')
        if len(text) > 30:
            return text
    
    return None

def extract_explanation_from_response(response_text):
    """Extract the explanation portion from the response"""
    # Look for "Why This Captures" section
    why_match = re.search(r'[Ww]hy\s+[Tt]his\s+[Cc]aptures[^:]*:?\s*\n*(.+?)(?:\n\n\d\.|\Z)', response_text, re.DOTALL)
    if why_match:
        return why_match.group(1).strip()
    
    # Look for any "Why" section
    why_match = re.search(r'\d\.\s*[Ww]hy[^:]*:?\s*\n*(.+?)(?:\n\n|\Z)', response_text, re.DOTALL)
    if why_match:
        return why_match.group(1).strip()
    
    # Look for explanation after the quote
    expl_match = re.search(r'"\s*\n\n(.{50,}?)(?:\n\n|\Z)', response_text, re.DOTALL)
    if expl_match:
        return expl_match.group(1).strip()
    
    return None

def extract_audio_segment(audio_path, start_seconds, end_seconds, output_path):
    """Extract a segment from the audio file"""
    try:
        audio = AudioSegment.from_ogg(audio_path)
        start_ms = int(start_seconds * 1000)
        end_ms = int(end_seconds * 1000)
        end_ms = min(end_ms, len(audio))
        
        segment = audio[start_ms:end_ms]
        segment.export(output_path, format="ogg")
        return True
    except Exception as e:
        st.error(f"Error extracting audio: {str(e)}")
        return False

def process_with_gemini(audio_path, api_key):
    """Process audio using Gemini API to find the hero moment"""
    try:
        genai.configure(api_key=api_key)
        
        audio_file = genai.upload_file(audio_path)
        
        prompt = """This is an interview. Find the hero moment — the top 30-45 seconds that best help me understand the VIBE of this person.

I want to know who this person really is. Find the part where they reveal their passion, their drive, what makes them tick.

The best hero moment is when they talk about things they've built, projects they've created, or their journey — with real numbers and genuine excitement.
Also parts where they talk about why they want to work at this company and why they are a good fit for the role.

Only include the CANDIDATE speaking. No interviewer. No back-and-forth.

Format:
1. Timestamp: [START]-[END]
2. Transcript: "[exact quote]"
3. Why this captures their vibe: [brief explanation]"""

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([audio_file, prompt])
        
        return response.text
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def main():
    # Check API key
    if not GEMINI_API_KEY:
        st.error("Please set GEMINI_API_KEY in Streamlit secrets")
        return

    # File upload
    uploaded_file = st.file_uploader(
        "Drop your interview audio here",
        type=['ogg', 'oga', 'mp3', 'wav', 'm4a'],
        help="Supports OGG, MP3, WAV, M4A",
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.markdown(f"<p style='color: #6b6b6b; font-size: 0.85rem;'>📎 {uploaded_file.name}</p>", unsafe_allow_html=True)

    # Process button
    if st.button("Find Hero Moment", disabled=not uploaded_file):
        if uploaded_file:
            with st.spinner("Analyzing..."):
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

        # Process with Gemini
        response_text = process_with_gemini(temp_file_path, GEMINI_API_KEY)
        
        if response_text:
            st.markdown('<div class="result-section">', unsafe_allow_html=True)
            
            # Extract timestamps
            start_time, end_time = extract_timestamps_from_response(response_text)
            
            if start_time is not None and end_time is not None:
                start_str = f"{int(start_time // 60)}:{int(start_time % 60):02d}"
                end_str = f"{int(end_time // 60)}:{int(end_time % 60):02d}"
                
                st.markdown(f'<span class="timestamp-pill">{start_str} → {end_str}</span>', unsafe_allow_html=True)
                
                # Extract the hero moment audio
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as hero_file:
                    hero_file_path = hero_file.name
                
                if extract_audio_segment(temp_file_path, start_time, end_time, hero_file_path):
                    st.audio(hero_file_path, format='audio/ogg')
                    
                    with open(hero_file_path, 'rb') as f:
                        st.download_button(
                            label="Download clip",
                            data=f,
                            file_name=f"hero_{filename}",
                            mime="audio/ogg"
                        )
                    
                    os.unlink(hero_file_path)
            
            # Extract and display transcript
            transcript = extract_transcript_from_response(response_text)
            explanation = extract_explanation_from_response(response_text)
            
            if transcript and len(transcript) > 50:
                st.markdown('<p class="section-label">The Clip</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="transcript-text">"{transcript}"</div>', unsafe_allow_html=True)
                
                if explanation:
                    st.markdown('<p class="section-label">Why This Captures Their Vibe</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="explanation-text">{explanation}</p>', unsafe_allow_html=True)
            else:
                # If parsing failed, show the full response nicely formatted
                st.markdown('<p class="section-label">Analysis</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="explanation-text">{response_text}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # Cleanup
        os.unlink(temp_file_path)

    except Exception as e:
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
