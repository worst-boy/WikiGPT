import google.generativeai as genai
import os
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
import telebot
from binance.client import Client

# Replace these with your actual API keys
API_KEY = 'JrKLFNlZxpu5SPEqfsaOpl6S3SYgn33q5WEt8LdayeJrlpGiex8pt3TACAxXA0t5'
API_SECRET = '21nUuSRmsKKkt2T3f11f1fzMdFbBJGDKvQIKpBWf4CwuIU4qXjIHUj8BbfG5qmqr'

# Initialize the Binance client
client = Client(API_KEY, API_SECRET)

# Replace with your Telegram Bot Token
TELEGRAM_TOKEN = '6049789416:AAEdassXO8WSeFxaZCSHqprnun6HZhOcVbg'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Configure the API key for the Google Generative AI
genai.configure(api_key="AIzaSyCX6YSKdjLm585O0yd8hsOO07JIkA4ZaXs")

# Set up the model
generation_config = {
    "temperature": 0.8,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config=generation_config,
    safety_settings=safety_settings,
)

# Store user requests
user_requests = {}

def get_crypto_info(crypto_name):
    output = []
    symbol = f"{crypto_name.upper()}USDT"

    try:
        info = client.get_symbol_info(symbol)
        if info:
            output.append(f"**Symbol:** {info['symbol']}")
            output.append(f"**Status:** {info['status']}")
            output.append(f"**Base Asset:** {info['baseAsset']}")
            output.append(f"**Quote Asset:** {info['quoteAsset']}")

            filters = {f['filterType']: f for f in info['filters']}
            if 'PRICE_FILTER' in filters:
                price_filter = filters['PRICE_FILTER']
                output.append(f"**Min Price:** {price_filter['minPrice']}")
                output.append(f"**Max Price:** {price_filter['maxPrice']}")
                output.append(f"**Tick Size:** {price_filter['tickSize']}")

            if 'LOT_SIZE' in filters:
                lot_size_filter = filters['LOT_SIZE']
                output.append(f"**Min Quantity:** {lot_size_filter['minQty']}")
                output.append(f"**Max Quantity:** {lot_size_filter['maxQty']}")

            # Fetch historical price data for the last 30 days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY,
                                                  start_time.strftime("%d %b, %Y"),
                                                  end_time.strftime("%d %b, %Y"))

            prices = np.array([[float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])] for kline in klines])
            dates = [datetime.fromtimestamp(kline[0] / 1000).date() for kline in klines]

            output.append("\n**Price data for the last 30 days:**")
            for i, date in enumerate(dates):
                output.append(
                    f"Date: {date}, Open: {prices[i][0]}, High: {prices[i][1]}, Low: {prices[i][2]}, Close: {prices[i][3]}")

        else:
            output.append("No information found for this cryptocurrency.")
    except Exception as e:
        output.append(f"Error fetching information: {e}")

    return '\n'.join(output)

def pass_to_ai(crypto_data):
    prompt = f"Provide analysis on the following cryptocurrency data:\n\n{crypto_data}"
    response = model.generate_text(prompt)
    return response['text']

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Welcome to the Crypto Info Bot!\nHere are the commands you can use:\n\n"
        "/info - Get information about a specific cryptocurrency. The bot will ask you for the coin symbol.\n"
        "/help - See this help message again."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['info'])
def ask_for_crypto(message):
    bot.send_message(message.chat.id, "Please enter the cryptocurrency symbol (e.g., BTC, ETH, etc.):")
    bot.register_next_step_handler(message, fetch_crypto_info)

def fetch_crypto_info(message):
    crypto_name = message.text.strip().upper()
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        crypto_data = get_crypto_info(crypto_name)

        if "No information found" in crypto_data:
            bot.reply_to(message, f"No data available for {crypto_name}.")
        else:
            bot.send_message(message.chat.id, "Fetching AI analysis, please wait...")
            ai_response = pass_to_ai(crypto_data)
            bot.reply_to(message, f"Here is the AI's analysis for {crypto_name}:\n\n{ai_response}")

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")

# Start the bot
bot.polling()
