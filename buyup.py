import telebot
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import google.generativeai as genai
import time

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
system_instruction = "This is a transcript extracted from a YouTube video. Your task is to act as an expert analyst and answer any questions based solely on the content of this transcript. \nFollow these guidelines: \n\n1. Stay within the transcript: Do not add any external information, personal opinions, or assumptions. \nYour answers must strictly adhere to the information provided. \n2. Provide accurate and concise responses: Answer directly and clearly, focusing on the specific details in the transcript. \nAvoid unnecessary elaboration or unrelated details. \n3. Contextualize as needed: If the question refers to a part of the transcript, include relevant quotes or paraphrase key sections to provide context. \n4. Organize your answers: Present responses logically and use bullet points or lists if there are multiple parts. Ensure explanations flow naturally. \n5. Acknowledge uncertainty: If the transcript does not contain the information needed to answer, state: 'The transcript does not provide information on this topic.'.\n Remember your responses should be organized and clean not just paragraphs, focus on details too. (You speak in to languages English and Persian, if user interacted with English you speak English else if Persian, you speak in Persian.)"

# Initialize the Gemini AI model
model = initialize_model(api_key, system_instruction)

# Configure Telegram Bot
API_TOKEN = "8155634930:AAFYhwBGAWBic-j9FTHf5uB19wG164BHZ2c"
bot = telebot.TeleBot(API_TOKEN)

# Store user states for interaction
user_states = {}

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
            "This is a transcript extracted from a YouTube video\n Now, proceed to answer questions accurately based on the transcript(Your responses should be clean, organized and detailed not in paragraphs).\n\n"
            + "\n".join([f"[{entry['start']:.2f}s]: {entry['text']}" for entry in transcript])
        )
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
    user_id = message.chat.id
    if user_id in user_states:
        del user_states[user_id]
    bot.reply_to(message, "🔄 Session restarted. Send a new YouTube video URL to begin. 🚀")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.chat.id

        if user_id not in user_states:
            video_url = message.text
            video_id = extract_video_id(video_url)

            if not video_id:
                bot.reply_to(message, "❌ Invalid YouTube URL. Please send a valid one. 🌐")
                return

            fetching_msg = bot.reply_to(message, "⏳ Fetching the transcript... 🔍")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            processing_msg = bot.reply_to(message, "🔄 Processing transcript with Gemini AI... 🤖")
            gemini_response = send_transcript_to_gemini(transcript)

            user_states[user_id] = {
                "gemini_context": gemini_response,
                "transcript": transcript
            }
            bot.edit_message_text("✅ Transcript processed. You can now ask questions about the video. 🎤", 
                                  message.chat.id, processing_msg.message_id)
            bot.delete_message(message.chat.id, fetching_msg.message_id)

        else:
            gemini_context = user_states[user_id]["gemini_context"]
            user_question = message.text

            bot.send_chat_action(user_id, 'typing')
            time.sleep(.5)

            gemini_response = model.generate_content(f"{gemini_context}\n\nQuestion: {user_question}")
            user_states[user_id]["gemini_context"] += f"\n\n{user_question}: {gemini_response.text}"
            bot.reply_to(message, gemini_response.text)

    except Exception as e:
        bot.reply_to(message, f"⚠️ An error occurred: {e}. Please try again. 🙇")
        print(f"Error in handle_message: {e}")

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot polling error: {e}")
