from binance.client import Client
from datetime import datetime, timedelta
import numpy as np
import telebot
import pyperclip

# Replace these with your actual API keys
API_KEY = 'JrKLFNlZxpu5SPEqfsaOpl6S3SYgn33q5WEt8LdayeJrlpGiex8pt3TACAxXA0t5'
API_SECRET = '21nUuSRmsKKkt2T3f11f1fzMdFbBJGDKvQIKpBWf4CwuIU4qXjIHUj8BbfG5qmqr'

# Initialize the Binance client
client = Client(API_KEY, API_SECRET)

# Replace with your Telegram Bot Token
TELEGRAM_TOKEN = '6049789416:AAEdassXO8WSeFxaZCSHqprnun6HZhOcVbg'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_crypto_info(crypto_name):
    output = []  # Collect all output lines here
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

            # Process price data for analysis
            prices = np.array([[float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])] for kline in klines])
            dates = [datetime.fromtimestamp(kline[0] / 1000).date() for kline in klines]

            output.append("\n**Price data for the last 30 days:**")
            for i, date in enumerate(dates):
                output.append(f"Date: {date}, Open: {prices[i][0]}, High: {prices[i][1]}, Low: {prices[i][2]}, Close: {prices[i][3]}")

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
    pyperclip.copy(final_output)  # Copy the output to the clipboard
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
    stochastic_k = 100 * ((current_close - lowest_low) / (highest_high - lowest_low)) if highest_high - lowest_low > 0 else 0
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


@bot.message_handler(func=lambda message: True)
def handle_invalid_input(message):
    bot.reply_to(message, "Invalid command. Please use /help to see available commands.")

# Start the bot
if __name__ == '__main__':
    bot.polling(none_stop=True)
