import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
import time
import re

# Configure Gemini AI
genai.configure(api_key="AIzaSyDsb9SBBzTAQ6DYnq0tnlDoElzNMdNYHDw")

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

generation_config = {
    "temperature": 0.8,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

def escape_markdown(text):
    """Remove unnecessary special characters for Markdown in Telegram by replacing them with spaces."""
    return re.sub(r"([_[\]()~>#+-=|{}])", " ", text)



def split_message_into_chunks(text, max_length=4000):
    """Split a long message into smaller chunks, avoiding broken Markdown formatting."""
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind('\n', 0, max_length)  # Find a newline character to split
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index])
        text = text[split_index:].lstrip()
    chunks.append(text)
    return chunks

# Initialize the model
def initialize_model(api_key, system_instruction):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash-002",
        generation_config=generation_config,
        safety_settings=safety_settings,
        system_instruction=system_instruction
    )

# Define the API key and system instruction
api_key = "AIzaSyDsb9SBBzTAQ6DYnq0tnlDoElzNMdNYHDw"
system_instruction = (
    "You are now a professional. YouTube video transcript will be provided to you, "
    "and you will respond with the most organized, clean, complete, and detailed responses. "
    "Your responses are organized and detailed, always using lists, numbers, headers, etc. "
    "You only respond based on the transcript and do not add anything else from yourself! "
    "You can speak in Persian as well and can respond in Persian too!"
)

# Initialize the Gemini AI model
model = initialize_model(api_key, system_instruction)

# Configure Telegram Bot
API_TOKEN = "7734180840:AAEevTIVXIv2VAozec9Y8Qx3B2DM2AhrIkQ"
bot = telebot.TeleBot(API_TOKEN)

# Store user states for interaction
user_states = {}

# Predefined phrases
PREDEFINED_PHRASES = [
    "Explain the context of the video for me",
    "Give me a complete summary of the video",
    "List the most important parts",
    "Tell me what the video is about",
    "Highlight the key insights"
]

def extract_video_id(url):
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
    try:
        prompt = (
            "This is a transcript extracted from a YouTube video.\n"
            "Now, proceed to respond accurately based on the transcript. "
            "You can respond in Persian as well and are not limited! "
            "(Your responses should be Clean, Organized, and Detailed. "
            "Do not put everything in paragraphs but make them organized!)\n\n"
            + "\n".join([f"[{entry['start']:.2f}s]: {escape_markdown(entry['text'])}" for entry in transcript])
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error interacting with Gemini AI: {e}")
        return "An error occurred while interacting with Gemini AI."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Create a custom keyboard with predefined phrases
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for phrase in PREDEFINED_PHRASES:
        keyboard.add(KeyboardButton(phrase))

    welcome_message = (
        "👋 *Welcome to the YouTube Transcript AI Bot!*\n\n"
        "📜 *What This Bot Can Do:*\n"
        "- Extracts the transcript from a YouTube video.\n"
        "- Processes the transcript with advanced AI for analysis.\n"
        "- Answers questions based solely on the video content.\n\n"
        "🎯 *How to Use:*\n"
        "1️⃣ Send a valid YouTube video URL.\n"
        "2️⃣ Use the predefined phrases below or ask your custom questions! 🚀"
    )
    bot.reply_to(message, welcome_message, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['restart'])
def restart_session(message):
    user_id = message.chat.id
    if user_id in user_states:
        del user_states[user_id]
    bot.reply_to(message, "🔄 Session restarted. Send a new YouTube video URL to begin. 🚀")

@bot.message_handler(func=lambda message: message.text in PREDEFINED_PHRASES)
def handle_predefined_phrases(message):
    try:
        user_id = message.chat.id

        if user_id not in user_states:
            bot.reply_to(
                message,
                "⚠️ Please send a YouTube video URL first. I'll process the transcript, and then you can use these options. 📥",
                parse_mode='Markdown'
            )
            return

        phrase = message.text
        gemini_context = user_states[user_id]["gemini_context"]

        bot.send_chat_action(user_id, 'typing')
        time.sleep(0.5)

        # Generate response based on the selected phrase
        gemini_response = model.generate_content(f"{gemini_context}\n\n{phrase}:")
        user_states[user_id]["gemini_context"] += f"\n\n{phrase}: {gemini_response.text}"
        response_text = escape_markdown(gemini_response.text)

        # Send the response in chunks if too long
        for chunk in split_message_into_chunks(response_text):
            bot.reply_to(message, chunk, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(
            message,
            f"⚠️ *An error occurred:* {escape_markdown(str(e))}\n"
            "Please try again or contact support. 🙇",
            parse_mode='Markdown'
        )
        print(f"Error in handle_predefined_phrases: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.chat.id

        if user_id not in user_states:
            video_url = message.text
            video_id = extract_video_id(video_url)

            if not video_id:
                bot.reply_to(
                    message,
                    "❌ *Invalid YouTube URL!*\n"
                    "Please send a valid YouTube video link (e.g., https://youtu.be/abc123). 🌐",
                    parse_mode='Markdown'
                )
                return

            fetching_msg = bot.reply_to(message, "⏳ *Fetching the transcript...* 🔍", parse_mode='Markdown')
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            processing_msg = bot.reply_to(message, "🔄 *Processing transcript with Gemini AI...* 🤖", parse_mode='Markdown')
            gemini_response = send_transcript_to_gemini(transcript)

            user_states[user_id] = {
                "gemini_context": gemini_response,
                "transcript": transcript
            }
            bot.edit_message_text(
                "✅ *Transcript processed!*\nYou can now ask questions about the video. 🎤",
                message.chat.id,
                processing_msg.message_id,
                parse_mode='Markdown'
            )
            bot.delete_message(message.chat.id, fetching_msg.message_id)

        else:
            gemini_context = user_states[user_id]["gemini_context"]
            user_question = escape_markdown(message.text)

            bot.send_chat_action(user_id, 'typing')
            time.sleep(.5)

            gemini_response = model.generate_content(f"{gemini_context}\n\nQuestion: {user_question}")
            user_states[user_id]["gemini_context"] += f"\n\n{user_question}: {gemini_response.text}"
            response_text = escape_markdown(gemini_response.text)

            # Send in chunks if too long
            for chunk in split_message_into_chunks(response_text):
                bot.reply_to(message, chunk, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(
            message,
            f"⚠️ *An error occurred:* {escape_markdown(str(e))}\n"
            "Please try again or contact support. 🙇",
            parse_mode='Markdown'
        )
        print(f"Error in handle_message: {e}")

# Polling to keep the bot running
bot.infinity_polling()
