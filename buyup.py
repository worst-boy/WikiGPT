import telebot
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai

# Configure Gemini AI
genai.configure(api_key="AIzaSyBTMCZkNWBmMA3OwGD9HPu84Tlh47q-LFY") 
model = genai.GenerativeModel("gemini-1.5-flash")

# Configure Telegram Bot
API_TOKEN = "8155634930:AAFYhwBGAWBic-j9FTHf5uB19wG164BHZ2c"
bot = telebot.TeleBot(API_TOKEN)

# Store user states for interaction
user_states = {}

def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    try:
        query = urlparse(url)
        if query.hostname in ('www.youtube.com', 'youtube.com'):
            return parse_qs(query.query).get('v', [None])[0]
        elif query.hostname == 'youtu.be':
            return query.path[1:]
    except Exception as e:
        print(f"Error extracting video ID: {e}")
    return None

def send_transcript_to_gemini(transcript):
    """
    Sends the transcript to Gemini AI and initializes the discussion.
    """
    try:
        prompt = (
            "This is the YouTube video transcript. You should answer questions about it just based on this transcript "
            "(Do not add anything of your own and just answer solely based on the transcript):\n\n"
        )
        prompt += "\n".join([f"[{entry['start']:.2f}s]: {entry['text']}" for entry in transcript])
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error interacting with Gemini AI: {e}")
        return "An error occurred while interacting with Gemini AI."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me a YouTube video URL to get started.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.chat.id
        if user_id not in user_states:
            # Step 1: Extract video ID
            video_url = message.text
            video_id = extract_video_id(video_url)

            if not video_id:
                bot.reply_to(message, "Invalid YouTube URL. Please send a valid one.")
                return

            # Step 2: Fetch transcript
            bot.reply_to(message, "Fetching the transcript...")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Step 3: Send transcript to Gemini AI
            bot.reply_to(message, "Processing transcript with Gemini AI...")
            gemini_response = send_transcript_to_gemini(transcript)

            # Step 4: Save state and allow interaction
            user_states[user_id] = {
                "gemini_context": gemini_response
            }
            bot.reply_to(message, "Transcript processed. You can now ask questions about the video.")
        else:
            # User interaction with Gemini AI
            gemini_context = user_states[user_id]["gemini_context"]
            user_question = message.text
            gemini_response = model.generate_content(f"{gemini_context}\n\nQuestion: {user_question}")
            bot.reply_to(message, gemini_response.text)
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")
        print(f"Error in handle_message: {e}")

# Error handling for unexpected issues
@bot.message_handler(func=lambda message: True, content_types=['text'])
def fallback_handler(message):
    bot.reply_to(message, "Sorry, I couldn't process that. Please try again.")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot polling error: {e}")
