import streamlit as st
import yt_dlp
import requests
import re
from google import genai

# --- Helper Functions ---

def get_youtube_transcript(url):
    """Fetches transcript using yt-dlp to bypass IP blocks."""
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'th'], # Prioritize English or Thai
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Look for manual subtitles first, then auto-generated
            subs = info.get('requested_subtitles') or info.get('automatic_captions')
            
            if not subs:
                return None, "No captions found for this video."
            
            # Get the URL for the subtitle file (usually VTT format)
            # If 'en' or 'th' isn't available, just grab the first available language
            lang = 'en' if 'en' in subs else list(subs.keys())[0]
            sub_url = subs[lang]['url']
            
            # Download the VTT file content
            vtt_content = requests.get(sub_url).text
            
            # Clean up the VTT formatting
            lines = vtt_content.split('\n')
            text = []
            for line in lines:
                if '-->' in line or line.strip() == '' or line.startswith('WEBVTT') or line.isdigit():
                    continue
                # Remove HTML tags like <c> or <00:00:00.000>
                clean_line = re.sub(r'<[^>]+>', '', line)
                text.append(clean_line.strip())
                
            full_text = " ".join(text)
            return full_text, None
            
    except Exception as e:
        return None, f"Error fetching video: {str(e)}"

# --- Streamlit App UI ---

st.set_page_config(page_title="HamMed", page_icon="🐹🩺")
st.title("🐹🩺 HamMed: YouTube Lecture to Easy Study Guide")
st.write("Paste a YouTube lecture link to generate structured study notes, flashcards, and a quiz.")

# User Inputs
url = st.text_input("Paste YouTube Lecture URL here:")

if st.button("Generate Study Guide"):
    
    if not url:
        st.warning("Please paste a YouTube URL first.")
    else:
        with st.spinner("Fetching transcript... (This might take 10-20 seconds)"):
            try:
                # 1. Get Transcript via yt-dlp
                full_transcript, error = get_youtube_transcript(url)
                
                if error:
                    st.error(error)
                else:
                    st.success("Transcript fetched successfully! Analyzing with AI...")
                    
                    # 2. Initialize Gemini
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # 3. Create AI Prompt
                    prompt = f"""
                    You are an expert medical educator. Based on the following lecture transcript, 
                    create a structured study guide for a medical student.
                    Be clinically accurate and high-yield. Use standard medical terminology.
                    If the transcript is in Thai, translate the concepts into English for the study guide.

                    Transcript:
                    {full_transcript[:30000]}  # Limit length to avoid token limits

                    Output format:
                    1. **Summary:** A concise, bulleted summary of the key concepts.
                    2. **High-Yield Flashcards:** Generate 10 flashcards in "Q: [Question] A: [Answer]" format.
                    3. **Practice Quiz:** Create 5 multiple-choice questions with 4 options each. Indicate the correct answer.
                    """

                    # 4. Call the AI
                    response = client.models.generate_content(
                        model="gemini-3.8-flash", # Using the stable fast model
                        contents=prompt
                    )

                    # 5. Display the Result
                    st.markdown("---")
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"An AI error occurred: {e}")