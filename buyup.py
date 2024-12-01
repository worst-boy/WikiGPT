import telebot
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
import time

# Configure Gemini AI
genai.configure(api_key="AIzaSyDsb9SBBzTAQ6DYnq0tnlDoElzNMdNYHDw") 
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
            "This is a transcript extracted from a YouTube video. Your task is to act as an expert analyst and answer any questions  "
            "solely based on the content of this transcript. Follow these guidelines for your responses:\n\n"
            "1. Stay Within the Transcript: Do not add any external information, personal opinions, or assumptions. Your answers "
            "Here is the transcript for your reference:\n\n"
        )
        prompt += "\n".join([f"[{entry['start']:.2f}s]: {entry['text']}" for entry in transcript])
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error interacting with Gemini AI: {e}")
        return "An error occurred while interacting with Gemini AI."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Send me a YouTube video URL to get started.\nUse /restart to start over with a new video. 🎥")

@bot.message_handler(commands=['restart'])
def restart_session(message):
    """
    Clears the user state to allow a new session.
    """
    user_id = message.chat.id
    if user_id in user_states:
        del user_states[user_id]
    bot.reply_to(message, "🔄 Session restarted. Send a new YouTube video URL to begin. 🚀")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.chat.id

        if user_id not in user_states:
            # Step 1: Extract video ID
            video_url = message.text
            video_id = extract_video_id(video_url)

            if not video_id:
                bot.reply_to(message, "❌ Invalid YouTube URL. Please send a valid one. 🌐")
                return

            # Step 2: Fetch transcript
            fetching_msg = bot.reply_to(message, "⏳ Fetching the transcript... 🔍")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Step 3: Send transcript to Gemini AI
            processing_msg = bot.reply_to(message, "🔄 Processing transcript with Gemini AI... 🤖")
            gemini_response = send_transcript_to_gemini(transcript)

            # Step 4: Save transcript and allow interaction
            user_states[user_id] = {
                "gemini_context": gemini_response,
                "transcript": transcript
            }
            bot.edit_message_text("✅ Transcript processed. You can now ask questions about the video. 🎤", 
                                  message.chat.id, processing_msg.message_id)
            bot.delete_message(message.chat.id, fetching_msg.message_id)

        else:
            # User interaction with Gemini AI
            gemini_context = user_states[user_id]["gemini_context"]
            user_question = message.text

            # Typing indicator
            bot.send_chat_action(user_id, 'typing')
            time.sleep(.5)  # Simulates typing delay

            gemini_response = model.generate_content(f"{gemini_context}\n\nQuestion: {user_question}")
            user_states[user_id]["gemini_context"] += f"\n\n{user_question}: {gemini_response.text}"
            bot.reply_to(message, gemini_response.text)

    except Exception as e:
        bot.reply_to(message, f"⚠️ An error occurred: {e}. Please try again. 🙇")
        print(f"Error in handle_message: {e}")

# Error handling for unexpected issues
@bot.message_handler(func=lambda message: True, content_types=['text'])
def fallback_handler(message):
    bot.reply_to(message, "Sorry, I couldn't process that. Please try again. 🤔")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot polling error: {e}")
