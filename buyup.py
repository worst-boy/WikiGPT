from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai

# Configure the Gemini API
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


def fetch_transcript(video_id):
    """
    Fetches the transcript for the given video ID.
    """
    return YouTubeTranscriptApi.get_transcript(video_id)


def chat_with_video(transcript):
    """
    Initiates a conversation with Gemini AI using the video transcript.
    """
    # Initial message to Gemini AI
    initial_prompt = f"This is the YouTube video transcript. You should answer questions about it based on this transcript only:\n\n{transcript}"
    response = model.generate_content(initial_prompt)
    print("Gemini AI is ready. You can now ask questions about the video.")

    # Start conversation loop
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting the conversation. Goodbye!")
            break
        follow_up_response = model.generate_content(user_input)
        print(f"Gemini AI: {follow_up_response.text}")


def main():
    # Get the YouTube video URL from the user
    video_url = input("Enter the YouTube video URL: ")
    video_id = extract_video_id(video_url)

    if not video_id:
        print("Invalid YouTube URL. Please try again.")
        return

    try:
        # Fetch the transcript
        transcript_data = fetch_transcript(video_id)
        transcript = "\n".join([
            f"[{entry['start']:.2f}s]: {entry['text']}"
            for entry in transcript_data
        ])

        # Start the chat
        chat_with_video(transcript)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
