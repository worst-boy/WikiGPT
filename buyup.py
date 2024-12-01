from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai

# Configure Gemini AI
genai.configure(api_key="AIzaSyBTMCZkNWBmMA3OwGD9HPu84Tlh47q-LFY") 
model = genai.GenerativeModel("gemini-1.5-flash")

def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    query = urlparse(url)
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        return parse_qs(query.query).get('v', [None])[0]
    elif query.hostname == 'youtu.be':
        return query.path[1:]
    return None

def send_transcript_to_gemini(transcript):
    """
    Sends the transcript to Gemini AI and initializes the discussion.
    """
    prompt = "This is the YouTube video transcript. You should answer questions about it just based on this transcript:\n\n"
    prompt += "\n".join([f"[{entry['start']:.2f}s]: {entry['text']}" for entry in transcript])
    response = model.generate_content(prompt)
    print("\nGemini's response:")
    print(response.text)
    return response

def main():
    # Get the YouTube video URL from the user
    video_url = input("Enter the YouTube video URL: ")
    video_id = extract_video_id(video_url)

    if not video_id:
        print("Invalid YouTube URL. Please try again.")
        return

    try:
        # Fetch the transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Send transcript to Gemini AI
        gemini_response = send_transcript_to_gemini(transcript)
        
        # Enable user to interact with Gemini about the video
        print("\nYou can now ask questions about the video.")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting the discussion. Goodbye!")
                break

            follow_up_response = model.generate_content(f"{gemini_response.text}\n\nQuestion: {user_input}")
            print(f"Gemini: {follow_up_response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
