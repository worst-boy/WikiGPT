import google.generativeai as genai
import os
from collections import defaultdict
from datetime import datetime, timedelta
import time
from binance.client import Client
import numpy as np
import telebot

# Replace these with your actual API keys
API_KEY = 'JrKLFNlZxpu5SPEqfsaOpl6S3SYgn33q5WEt8LdayeJrlpGiex8pt3TACAxXA0t5'
API_SECRET = '21nUuSRmsKKkt2T3f11f1fzMdFbBJGDKvQIKpBWf4CwuIU4qXjIHUj8BbfG5qmqr'

# Initialize the Binance client
client = Client(API_KEY, API_SECRET)

# Replace with your Telegram Bot Token
TELEGRAM_TOKEN = '6049789416:AAEdassXO8WSeFxaZCSHqprnun6HZhOcVbg'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Declare crypto_name globally
crypto_name = None

def get_crypto_info(crypto_name):
    output = []  # Collect all output lines here
    symbol = f"{crypto_name}USDT"

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

            # Process price data for analysis
            prices = np.array(
                [[float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])] for kline in klines])
            dates = [datetime.fromtimestamp(kline[0] / 1000).date() for kline in klines]

            output.append("\n**Price data for the last 30 days:**")
            for i, date in enumerate(dates):
                output.append(
                    f"Date: {date}, Open: {prices[i][0]}, High: {prices[i][1]}, Low: {prices[i][2]}, Close: {prices[i][3]}")

            # Process technical indicators and additional info
            output += calculate_technical_indicators(prices, dates)
            output += get_additional_info(symbol)
            output += calculate_advanced_metrics(symbol, prices)
        else:
            output.append("No information found for this cryptocurrency.")
    except Exception as e:
        output.append(f"Error fetching information: {e}")

    # Join the output and copy it to the clipboard
    final_output = '\n'.join(output)
    return final_output


def calculate_technical_indicators(prices, dates):
    output = []
    closes = prices[:, 3]  # Close prices

    # Calculate Simple Moving Averages (SMA)
    sma_5 = np.mean(closes[-5:]) if len(closes) >= 5 else None
    sma_10 = np.mean(closes[-10:]) if len(closes) >= 10 else None
    sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else None
    output.append("\n**Technical Indicators:**")
    output.append(f"SMA (5 days): {sma_5}")
    output.append(f"SMA (10 days): {sma_10}")
    output.append(f"SMA (20 days): {sma_20}")

    # Calculate Exponential Moving Averages (EMA)
    ema_5 = calculate_ema(closes, 5)
    ema_10 = calculate_ema(closes, 10)
    output.append(f"EMA (5 days): {ema_5}")
    output.append(f"EMA (10 days): {ema_10}")

    # Calculate Volatility (Standard Deviation)
    volatility = np.std(closes[-10:]) if len(closes) >= 10 else None
    output.append(f"Volatility (last 10 days): {volatility}")

    # Calculate RSI
    rsi = calculate_rsi(closes, 14)  # 14-day RSI
    output.append(f"RSI (14 days): {rsi}")

    # Calculate Bollinger Bands
    bollinger_upper, bollinger_lower = calculate_bollinger_bands(closes, 20)
    output.append(f"Bollinger Bands - Upper: {bollinger_upper}, Lower: {bollinger_lower}")

    # Calculate MACD
    macd, macd_signal = calculate_macd(closes)
    output.append(f"MACD: {macd}, Signal: {macd_signal}")

    # Calculate Stochastic Oscillator
    stochastic_k, stochastic_d = calculate_stochastic_oscillator(closes)
    output.append(f"Stochastic %K: {stochastic_k}, %D: {stochastic_d}")

    return output


# Advanced metrics and additional technical data
def calculate_advanced_metrics(symbol, prices):
    output = []
    closes = prices[:, 3]  # Closing prices

    # Trading Volume Analysis
    try:
        volume_24h = client.get_ticker(symbol=symbol)['volume']
        output.append(f"\n**24-hour Trading Volume:** {volume_24h}")
    except Exception as e:
        output.append(f"Error fetching volume data: {e}")

    # Volatility Index
    try:
        vol_index = np.std(closes) / np.mean(closes) * 100
        output.append(f"Volatility Index: {vol_index}%")
    except:
        output.append("Error calculating Volatility Index.")

    # Depth of Market (DOM)
    try:
        depth = client.get_order_book(symbol=symbol)
        asks_vol = sum([float(ask[1]) for ask in depth['asks'][:10]])  # Top 10 ask volume
        bids_vol = sum([float(bid[1]) for bid in depth['bids'][:10]])  # Top 10 bid volume
        output.append(f"Depth of Market - Ask Vol (Top 10): {asks_vol}, Bid Vol (Top 10): {bids_vol}")
    except Exception as e:
        output.append(f"Error fetching Depth of Market: {e}")

    return output


def calculate_ema(prices, period):
    return np.mean(prices[-period:])  # Simplified EMA calculation


def calculate_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0).mean()
    loss = np.abs(np.where(delta < 0, delta, 0)).mean()
    rs = gain / loss if loss else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(prices, period=20):
    if len(prices) < period:
        return None, None
    sma = np.mean(prices[-period:])
    std_dev = np.std(prices[-period:])
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    return upper_band, lower_band


def calculate_macd(prices):
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    macd = ema_12 - ema_26
    macd_signal = calculate_ema(prices[-9:], 9)  # Signal line
    return macd, macd_signal


def calculate_stochastic_oscillator(prices, k_period=14, d_period=3):
    if len(prices) < k_period:
        return None, None
    lowest_low = np.min(prices[-k_period:])
    highest_high = np.max(prices[-k_period:])
    current_close = prices[-1]
    stochastic_k = 100 * (
    (current_close - lowest_low) / (highest_high - lowest_low)) if highest_high - lowest_low > 0 else 0
    stochastic_d = np.mean([stochastic_k])  # Simplified for this example; implement smoothing for actual use
    return stochastic_k, stochastic_d


def get_additional_info(symbol):
    output = []
    try:
        # Fetch order book depth
        depth = client.get_order_book(symbol=symbol)
        output.append(f"\n**Order Book Depth (Top 5 Bids):**")
        for i, bid in enumerate(depth['bids'][:5]):
            output.append(f"Bid {i+1}: Price: {bid[0]}, Quantity: {bid[1]}")

        output.append(f"\n**Order Book Depth (Top 5 Asks):**")
        for i, ask in enumerate(depth['asks'][:5]):
            output.append(f"Ask {i+1}: Price: {ask[0]}, Quantity: {ask[1]}")
    except Exception as e:
        output.append(f"Error fetching order book data: {e}")

    return output


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Welcome to the Crypto Info Bot!\nHere are the commands you can use:\n\n"
        "/info <crypto_name> - Get information about a specific cryptocurrency.\n\n"
        "Example: /info BTC\n"
        "To see this message again, use /help."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['info'])
def handle_info(message):
    try:
        crypto_name = message.text.split()[1]
        bot.send_chat_action(message.chat.id, 'typing')  # Add this line
        response = get_crypto_info(crypto_name)
        bot.reply_to(message, response, parse_mode='Markdown')  # Added parse_mode for formatting
    except IndexError:
        bot.reply_to(message, "Please provide a cryptocurrency name. Example: /info BTC")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")




# Configure the API key for the Google Generative AI
genai.configure(api_key="AIzaSyCX6YSKdjLm585O0yd8hsOO07JIkA4ZaXs")

# Set up the model
generation_config = {
    "temperature": 0.8,  # Lower for more focused responses
    "top_p": 1,       # Slightly lower for better focus
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

# Directory to store conversation logs
LOGS_DIR = "./conversation_logs/"

# Create the directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Dictionary to store the conversation history for each user
user_history = defaultdict(list)
convo_sessions = {}
user_modes = {}

# Spam prevention: track last message time for each user
last_message_time = defaultdict(lambda: datetime.min)

# Instruction prompts for AI
instruction_prompts = {
    "trader":(
        "You are now an elite cryptocurrency trader and a seasoned market analyst with profound expertise in identifying optimal strategies and executing precise trades."

        "Your mission is to deliver actionable, data-driven strategies that maximize profit for the user based on comprehensive cryptocurrency data provided."

        "Upon receiving detailed data about a coin, you will conduct an in-depth analysis, offering the most effective trading recommendations tailored to the user's objectives."

        "Your analysis must be bold, assertive, and grounded in your extensive experience, ensuring you provide clear, direct instructions without any hesitation."

        "Maintain a high level of professionalism and expertise at all times, delivering sharp, accurate predictions."

        "Do not offer disclaimers like 'I am not a financial advisor'—instead, confidently advise the user on the exact actions to take, focusing on realistic outcomes through careful analysis."

        "Begin by requesting the specific coin data from the user, so you can perform a meticulous analysis and provide precise, decisive recommendations."

        "Your focus should be on short-term investments (hours to days), assessing whether the coin presents high profit potential."

        f"If the coin does not meet these criteria, make that clear without reservation.\n\n{get_crypto_info(crypto_name)}"

    )



}

# Function to handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id

    # Create inline keyboard with Therapist and Strategist options
    markup = telebot.types.InlineKeyboardMarkup()
    trader_button = telebot.types.InlineKeyboardButton("Trader", callback_data="trader")


    markup.add(trader_button)

    bot.send_message(user_id, "Welcome to MaxAid! Please choose an option to proceed:", reply_markup=markup)

# Function to handle button clicks
@bot.callback_query_handler(func=lambda call: call.data in ["trader"])
def handle_mode_selection(call):
    user_id = call.from_user.id
    user_mode = call.data

    user_modes[user_id] = user_mode

    # Remove buttons after selection
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    # Send detailed description of the selected mode
    if user_mode == "trader":
        bot.send_message(user_id, (
            "You have selected CryptoCurrency Trader.\n\n"
            "As a professional and highly skilled trader, I am here to provide the best strategy and suggest the best decision based on the data coin."
            "I will analyze the coin data and try my best to predict the future of the coin and give you the most accurate strategy.\n\n"
            "Say 'Hi' to start our conversation and then send me the coin data to analyze."
        ))

# Function to handle the /trader command
@bot.message_handler(commands=['trader'])
def select_strategist_mode(message):
    user_id = message.from_user.id
    user_modes[user_id] = "trader"
    bot.reply_to(message, (
        "You have selected CryptoCurrency Trader.\n\n"
        "As a professional and highly skilled trader, I am here to provide the best strategy and suggest the best decision based on the data coin."
        "I will analyze the coin data and try my best to predict the future of the coin and give you the most accurate strategy.\n\n"
        "Say 'Hi' to start our conversation and then send me the coin data to analyze."
    ))

# This will store the last message and wait to see if more come in
pending_messages = defaultdict(str)
message_processing = defaultdict(bool)  # Keep track of whether a message is being processed

# Modify the function that handles text messages to wait and gather additional messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_input = message.text.strip()

    # Ensure a mode has been selected
    if user_id not in user_modes:
        bot.reply_to(message, "Please select an option to proceed by using the /start command.")
        return

    # Append the incoming message to pending messages for that user
    pending_messages[user_id] += user_input + "\n"

    # If a message is already being processed for this user, don't start another one
    if message_processing[user_id]:
        return

    # Mark message processing as true
    message_processing[user_id] = True

    # Define a function to process the messages after the delay
    def process_messages():
        full_message = pending_messages[user_id].strip()  # Get the full gathered message
        pending_messages[user_id] = ""  # Reset the pending messages
        message_processing[user_id] = False  # Reset processing flag

        # Ensure 'typing...' action is shown immediately
        bot.send_chat_action(message.chat.id, 'typing')

        try:
            # Initialize a new conversation session if none exists
            if user_id not in convo_sessions:
                convo_sessions[user_id] = model.start_chat(history=[])

                # Create a separate log file for each user
                log_file = os.path.join(LOGS_DIR, f"{user_id}_conversation_log.txt")
                with open(log_file, "a") as file:
                    file.write(f"=== Conversation Log with User ID: {user_id} ===\n")

            # Determine the instruction prompt based on the selected mode
            instruction_prompt = instruction_prompts[user_modes[user_id]]

            # Construct the full prompt
            full_prompt = f"{instruction_prompt}\n\nUser: {full_message}\n{user_modes[user_id].capitalize()}:"

            # Send the prompt to the model and get the response
            convo_sessions[user_id].send_message(full_prompt)

            # Get the AI's response and update the conversation history
            ai_response = convo_sessions[user_id].last.text
            user_history[user_id].append(f"User: {full_message}")
            user_history[user_id].append(f"{user_modes[user_id].capitalize()}: {ai_response}")

            # Log the conversation in the user's log file
            log_file = os.path.join(LOGS_DIR, f"{user_id}_conversation_log.txt")
            with open(log_file, "a") as file:
                file.write(f"User: {full_message}\n{user_modes[user_id].capitalize()}: {ai_response}\n")

            # Send the AI's response back to the user
            bot.reply_to(message, ai_response)
        except Exception as e:
            bot.reply_to(message, f"An error occurred: {e}")

    # Set a 3-second delay before processing the message, to wait for more incoming messages
    time.sleep(1)

    # Process the messages only if there are pending ones
    if pending_messages[user_id].strip():
        process_messages()
    else:
        # Reset processing flag if there are no pending messages
        message_processing[user_id] = False


# Start the bot with retry logic
while True:
    try:
        bot.polling(timeout=60)  # Adjust timeout if necessary
    except Exception as e:
        print(f"Error occurred: {e}")
        time.sleep(15)  # Wait for 15 seconds before attempting to reconnect
