# 🎯 Hero Moment Finder

A Streamlit app that uses Gemini AI to find the most compelling 30-40 seconds from any interview recording.

## What it does

1. Upload an interview audio file (OGG, MP3, WAV, M4A)
2. Gemini AI analyzes the entire interview
3. Identifies the "hero moment" - the best segment that captures the person's vibe
4. Extracts that specific audio segment
5. Plays the hero clip directly in your browser
6. Lets you download the extracted clip

## Setup Instructions

### 1. Install FFmpeg (Required for audio processing)

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

### 2. Install Python dependencies

```bash
cd /Users/prabhavpandey/Documents/hero
pip install -r requirements.txt
```

### 3. Get your Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API key"
3. Copy the key

### 4. Run the app

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. Paste your Gemini API key in the sidebar
2. (Optional) Add context about the interview (e.g., "Interview for Growth Associate role")
3. Upload your audio file
4. Click "Find Hero Moment"
5. Listen to the extracted hero clip
6. Download if needed

## Example

For an interview audio, the app will:
- Analyze the full recording
- Return something like: **Hero Moment: 0:45 - 1:25**
- Extract and play that specific 40-second segment
- Show the transcript and explanation of why it's compelling

## Requirements

- Python 3.8+
- FFmpeg installed on system
- Gemini API key
- Internet connection