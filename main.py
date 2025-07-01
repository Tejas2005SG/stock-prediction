import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from tkinter import *
from tkinter import ttk, messagebox
from tkinter.font import Font
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import re
import threading
import uuid
from datetime import datetime
import numpy as np

# === CONFIGURATION ===
GEMINI_API_KEY = "AIzaSyDyujm50dHMYvn1V50dDDqcAhgUqCOuUGU"
TWILIO_SID = "AC2109d18b30f88881dd66b669a51a95cf"
TWILIO_AUTH_TOKEN = "8585fff96c35fc50ad168fa951603da1"
TWILIO_PHONE = "+16592006253"
YOUR_PHONE = "+918766816061"

# === STYLE CONSTANTS ===
BG_COLOR = "#f0f2f5"
PRIMARY_COLOR = "#4285f4"
SECONDARY_COLOR = "#34a853"
ACCENT_COLOR = "#ea4335"
TEXT_COLOR = "#202124"
LIGHT_TEXT = "#5f6368"
FONT_FAMILY = "Segoe UI"

# === COMPANY NAME TO TICKER MAPPING ===
COMPANY_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "tesla": "TSLA",
    "amazon": "AMZN",
    "google": "GOOGL",
    "meta": "META",
    "nvidia": "NVDA",
    "intel": "INTC",
    "ibm": "IBM",
    "oracle": "ORCL"
}

# === HELPER FUNCTIONS ===
def calculate_technical_score(df, indicators):
    """Calculate technical validation score based on indicator signals."""
    score = 0
    total_indicators = 0

    # SMA Crossover
    if indicators['sma_10'][-1] > indicators['sma_20'][-1]:
        score += 1
    elif indicators['sma_10'][-1] < indicators['sma_20'][-1]:
        score -= 1
    total_indicators += 1

    # EMA Crossover
    if indicators['ema_10'][-1] > indicators['ema_20'][-1]:
        score += 1
    elif indicators['ema_10'][-1] < indicators['ema_20'][-1]:
        score -= 1
    total_indicators += 1

    # RSI
    if 30 < indicators['rsi'][-1] < 70:
        score += 0.5
    elif indicators['rsi'][-1] > 75:
        score -= 0.5
    elif indicators['rsi'][-1] < 25:
        score += 0.5
    total_indicators += 1

    # MACD
    if indicators['macd'][-1] > indicators['macd_signal'][-1]:
        score += 1
    elif indicators['macd'][-1] < indicators['macd_signal'][-1]:
        score -= 1
    total_indicators += 1

    # Bollinger Bands
    if indicators['close'][-1] < indicators['bb_lower'][-1]:
        score += 0.5
    elif indicators['close'][-1] > indicators['bb_upper'][-1]:
        score -= 0.5
    total_indicators += 1

    # Stochastic
    if indicators['stoch_k'][-1] > indicators['stoch_d'][-1] and indicators['stoch_k'][-1] < 80:
        score += 0.5
    elif indicators['stoch_k'][-1] < indicators['stoch_d'][-1] and indicators['stoch_k'][-1] > 20:
        score -= 0.5
    total_indicators += 1

    # Williams %R
    if indicators['willr'][-1] < -80:
        score += 0.5
    elif indicators['willr'][-1] > -20:
        score -= 0.5
    total_indicators += 1

    # ATR (Volatility)
    if indicators['atr'][-1] < np.mean(indicators['atr'][-20:]):
        score += 0.3
    total_indicators += 1

    # Volume Trend
    if indicators['volume'][-1] > indicators['volume_ma'][-1]:
        score += 0.3
    total_indicators += 1

    # OBV Trend
    if indicators['obv'][-1] > indicators['obv'][-5]:
        score += 0.3
    total_indicators += 1

    # CCI
    if -100 < indicators['cci'][-1] < 100:
        score += 0.3
    elif indicators['cci'][-1] > 100:
        score -= 0.3
    elif indicators['cci'][-1] < -100:
        score += 0.3
    total_indicators += 1

    # ADX
    if indicators['adx'][-1] > 25:
        score += 0.3
    total_indicators += 1

    # MFI
    if 20 < indicators['mfi'][-1] < 80:
        score += 0.3
    elif indicators['mfi'][-1] > 80:
        score -= 0.3
    elif indicators['mfi'][-1] < 20:
        score += 0.3
    total_indicators += 1

    # ROC
    if indicators['roc'][-1] > 0:
        score += 0.3
    elif indicators['roc'][-1] < 0:
        score -= 0.3
    total_indicators += 1

    return (score / total_indicators) * 100 if total_indicators > 0 else 50

def identify_support_resistance(df):
    """Identify support and resistance levels using pivot points."""
    window = 20
    df['pivot'] = (df['High'].rolling(window=window).max() + 
                   df['Low'].rolling(window=window).min() + 
                   df['Close'].rolling(window=window).mean()) / 3
    support = df['pivot'].rolling(window=window).min()
    resistance = df['pivot'].rolling(window=window).max()
    return support[-1], resistance[-1]

def infer_timeframe(recommendation, technical_score):
    """Infer timeframe based on recommendation and technical score."""
    if recommendation == "BUY" and technical_score > 70:
        return "Long-term (3-12 months)"
    elif recommendation == "SELL" and technical_score < 30:
        return "Short-term (1-4 weeks)"
    else:
        return "Medium-term (1-3 months)"

def infer_price_target(current_price, recommendation, technical_score, resistance, support):
    """Infer price target based on current price, recommendation, and levels."""
    if recommendation == "BUY":
        target = resistance if technical_score > 70 else current_price * 1.05
    elif recommendation == "SELL":
        target = support if technical_score < 30 else current_price * 0.95
    else:
        target = (resistance + support) / 2
    return f"${target:.2f}"

def interpret_signal(technical_score, recommendation):
    """Interpret the technical score in context of AI recommendation."""
    if technical_score > 70 and recommendation == "BUY":
        return "Strong Buy Confirmation"
    elif technical_score < 30 and recommendation == "SELL":
        return "Strong Sell Confirmation"
    elif 40 <= technical_score <= 60:
        return "Neutral - Indicators Mixed"
    else:
        return "Moderate Confirmation"

# === GEMINI AI ===
def get_gemini_prediction(prompt):
    """Fetch stock recommendation from Gemini API with strict format enforcement."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt_text = (
        "You are a stock market expert with deep knowledge of technical analysis. Analyze the provided stock data and respond in the EXACT format shown below, with no extra text before or after, no additional commentary, and all fields populated:\n\n"
        "Recommendation: <BUY or SELL or HOLD>\n"
        "Primary Factors: <Key technical indicators driving the recommendation, max 100 chars>\n"
        "Supporting Evidence: <Additional data supporting the recommendation, max 100 chars>\n"
        "Risk Assessment: <Potential risks or counter-indicators, max 100 chars>\n"
        "Confidence Level: <Low|Medium|High>\n"
        "Estimated Accuracy: <A number between 60% and 95%>\n"
        "Timeframe: <Short-term (1-4 weeks)|Medium-term (1-3 months)|Long-term (3-12 months)>\n"
        "Price Target: <Estimated price target or range, e.g., $100-$120 or $100>\n\n"
        "Use the following stock data for your analysis:\n\n"
        f"{prompt}\n\n"
        "Analysis Guidelines:\n"
        "- Evaluate trend: SMA, EMA, MACD\n"
        "- Assess momentum: RSI, Stochastic, Williams %R, MFI, ROC\n"
        "- Analyze volatility: Bollinger Bands, ATR\n"
        "- Consider volume: Volume, OBV\n"
        "- Use support/resistance levels\n"
        "- Incorporate CCI, ADX\n"
        "- Ensure all fields are concise and populated\n"
        "- Output only the specified format\n"
    )

    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500,
            "topP": 0.9,
            "topK": 20,
            "stopSequences": ["\n\n", "END"]
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            error_msg = f"Gemini API request failed: {response.status_code}: {response.text}"
            print(error_msg)
            return {"error": error_msg}

        result = response.json()
        if "candidates" in result and len(result["candidates"]) > 0:
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            print("Gemini AI Raw Response:\n", content)
            return parse_gemini_response(content)
        elif "error" in result:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            print("Gemini API Error:", error_msg)
            return {"error": error_msg}
        else:
            return {"error": "Unexpected response format from Gemini"}

    except requests.exceptions.Timeout:
        error_msg = "Gemini API request timed out"
        print(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Exception during Gemini processing: {str(e)}"
        print(error_msg)
        return {"error": error_msg}

def parse_gemini_response(text):
    """Parse Gemini API response with robust handling and default values."""
    try:
        # Primary regex for 8-field response
        match = re.search(
            r"Recommendation:\s*(BUY|SELL|HOLD)\s*"
            r"Primary Factors:\s*(.*?)\s*"
            r"Supporting Evidence:\s*(.*?)\s*"
            r"Risk Assessment:\s*(.*?)\s*"
            r"Confidence Level:\s*(Low|Medium|High)\s*"
            r"Estimated Accuracy:\s*(\d+)%\s*"
            r"Timeframe:\s*(Short-term|Medium-term|Long-term|.*?)\s*"
            r"Price Target:\s*(.*?)\s*$",
            text, re.DOTALL | re.IGNORECASE
        )
        if match:
            accuracy = int(match.group(6))
            if not (60 <= accuracy <= 95):
                return {"raw": text, "error": "Accuracy must be between 60% and 95%"}
            return {
                "recommendation": match.group(1).upper(),
                "primary_factors": match.group(2).strip() or "Mixed technical signals",
                "supporting_evidence": match.group(3).strip() or "Recent price trends and volume",
                "risk_assessment": match.group(4).strip() or "Market volatility",
                "confidence": match.group(5).capitalize(),
                "accuracy": accuracy,
                "timeframe": match.group(7).capitalize() or "Medium-term",
                "price_target": match.group(8).strip() or "Current price range",
                "raw": text
            }
        
        # Fallback regex for partial responses
        fallback_match = re.search(
            r"Recommendation:\s*(BUY|SELL|HOLD)\s*"
            r"(?:Primary Factors|Reason):\s*(.*?)\s*"
            r"(?:Confidence Level)?:\s*(Low|Medium|High)?\s*"
            r"(?:Estimated Accuracy)?:\s*(\d+)%?",
            text, re.DOTALL | re.IGNORECASE
        )
        if fallback_match:
            accuracy = int(fallback_match.group(4)) if fallback_match.group(4) else 70
            if not (60 <= accuracy <= 95):
                return {"raw": text, "error": "Accuracy must be between 60% and 95%"}
            return {
                "recommendation": fallback_match.group(1).upper(),
                "primary_factors": fallback_match.group(2).strip() or "Mixed technical signals",
                "supporting_evidence": "Recent price trends and volume",
                "risk_assessment": "Market volatility",
                "confidence": (fallback_match.group(3).capitalize() if fallback_match.group(3) else "Medium"),
                "accuracy": accuracy,
                "timeframe": "Medium-term",
                "price_target": "Current price range",
                "raw": text
            }
        
        return {"raw": text, "error": "Could not parse response. Response format invalid."}
    
    except Exception as e:
        return {"raw": text, "error": f"Parsing error: {str(e)}"}

# === STOCK DATA ===
def fetch_stock_data(ticker):
    """Fetch 2 years of stock data and calculate comprehensive technical indicators."""
    try:
        stock = yf.Ticker(ticker.upper())
        df = stock.history(period="2y", interval="1d")
        if df.empty:
            raise ValueError(f"No data found for ticker {ticker}")
        
        # Calculate technical indicators
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_Signal'] = macd['MACDs_12_26_9']
        bb = ta.bbands(df['Close'], length=20)
        df['BB_Upper'] = bb['BBU_20_2.0']
        df['BB_Lower'] = bb['BBL_20_2.0']
        stoch = ta.stoch(df['High'], df['Low'], df['Close'])
        df['Stoch_K'] = stoch['STOCHk_14_3_3']
        df['Stoch_D'] = stoch['STOCHd_14_3_3']
        df['Williams_R'] = ta.willr(df['High'], df['Low'], df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['CCI'] = ta.cci(df['High'], df['Low'], df['Close'], length=20)
        df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'], length=14)['ADX_14']
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['ROC'] = ta.roc(df['Close'], length=12)
        
        print(f"Stock data fetched successfully for {ticker}")
        return df.dropna()
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {str(e)}")
        return None

# === PROMPT GENERATION ===
def build_prompt(df, company, ticker):
    """Build a comprehensive prompt for Gemini API with enhanced data formatting."""
    latest_data = df.tail(1).iloc[0]
    recent_data = df.tail(10)
    
    # Calculate trends and metrics
    trend = "Bullish" if latest_data['SMA_10'] > latest_data['SMA_20'] else "Bearish"
    volume_trend = "Increasing" if latest_data['Volume'] > latest_data['Volume_MA'] else "Decreasing"
    volatility = latest_data['ATR']
    support, resistance = identify_support_resistance(df)
    
    # Recent performance
    one_month_return = ((df['Close'].iloc[-1] - df['Close'].iloc[-21]) / df['Close'].iloc[-21]) * 100 if len(df) >= 21 else 0
    three_month_return = ((df['Close'].iloc[-1] - df['Close'].iloc[-63]) / df['Close'].iloc[-63]) * 100 if len(df) >= 63 else 0
    six_month_return = ((df['Close'].iloc[-1] - df['Close'].iloc[-126]) / df['Close'].iloc[-126]) * 100 if len(df) >= 126 else 0
    
    prompt = (
        f"Stock Analysis for {company} ({ticker})\n"
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Current Price: ${latest_data['Close']:.2f}\n\n"
        f"Summary:\n"
        f"- Trend: {trend}\n"
        f"- Volume Trend: {volume_trend}\n"
        f"- Volatility (ATR): {volatility:.2f}\n"
        f"- Support: ${support:.2f}\n"
        f"- Resistance: ${resistance:.2f}\n"
        f"- 1-Month Return: {one_month_return:.2f}%\n"
        f"- 3-Month Return: {three_month_return:.2f}%\n"
        f"- 6-Month Return: {six_month_return:.2f}%\n"
        f"- ADX: {latest_data['ADX']:.2f}\n"
        f"- CCI: {latest_data['CCI']:.2f}\n"
        f"- MFI: {latest_data['MFI']:.2f}\n"
        f"- ROC: {latest_data['ROC']:.2f}\n\n"
        "Recent Indicators (Last 10 Days):\n"
        "Date | Close | SMA_10 | SMA_20 | EMA_10 | RSI | MACD | MACD Signal | BB Upper | BB Lower | Stochastic K | Stochastic D | Williams %R | ATR | Volume | OBV | CCI | ADX | MFI | ROC\n"
    )
    
    for idx, row in recent_data.iterrows():
        prompt += (
            f"{idx.date()} | {row['Close']:.2f} | {row['SMA_10']:.2f} | {row['SMA_20']:.2f} | "
            f"{row['EMA_10']:.2f} | {row['RSI']:.2f} | {row['MACD']:.2f} | {row['MACD_Signal']:.2f} | "
            f"{row['BB_Upper']:.2f} | {row['BB_Lower']:.2f} | {row['Stoch_K']:.2f} | "
            f"{row['Stoch_D']:.2f} | {row['Williams_R']:.2f} | {row['ATR']:.2f} | "
            f"{int(row['Volume'])} | {int(row['OBV'])} | {row['CCI']:.2f} | {row['ADX']:.2f} | "
            f"{row['MFI']:.2f} | {row['ROC']:.2f}\n"
        )
    
    prompt += "\nGuidelines:\n"
    prompt += "- Golden Cross (SMA_10 > SMA_20): Bullish\n"
    prompt += "- Death Cross (SMA_10 < SMA_20): Bearish\n"
    prompt += "- RSI > 70: Overbought, < 30: Oversold\n"
    prompt += "- MACD > Signal: Bullish, < Signal: Bearish\n"
    prompt += "- Price near BB Lower: Bullish, BB Upper: Bearish\n"
    prompt += "- Stochastic K > D, < 80: Bullish; K < D, > 20: Bearish\n"
    prompt += "- Williams %R < -80: Oversold, > -20: Overbought\n"
    prompt += "- High ATR: High volatility\n"
    prompt += "- Increasing OBV: Confirms trend\n"
    prompt += "- CCI > 100: Overbought, < -100: Oversold\n"
    prompt += "- ADX > 25: Strong trend\n"
    prompt += "- MFI > 80: Overbought, < 20: Oversold\n"
    prompt += "- Positive ROC: Upward momentum\n"
    
    print(f"Prompt built for {company} ({ticker})")
    return prompt

# === SMS FUNCTION ===
def send_sms(message):
    """Send SMS using Twilio with debugging and DLT compliance."""
    try:
        print(f"\n=== Sending SMS ===\nFrom: {TWILIO_PHONE}\nTo: {YOUR_PHONE}\nMessage: {message}\nLength: {len(message)} chars")
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        account = client.api.accounts(TWILIO_SID).fetch()
        print(f"Twilio account status: {account.status}")
        
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=YOUR_PHONE
        )
        
        print(f"SMS sent! SID: {message_obj.sid}, Status: {message_obj.status}")
        messagebox.showinfo("SMS Status", f"SMS sent!\nSID: {message_obj.sid}\nStatus: {message_obj.status}")
        return True
        
    except TwilioRestException as e:
        error_msg = f"Twilio Error: {e.msg}\nCode: {e.code}\nStatus: {e.status}"
        print(error_msg)
        messagebox.showerror("SMS Error", error_msg)
        return False
    except Exception as e:
        error_msg = f"SMS Error: {str(e)}"
        print(error_msg)
        messagebox.showerror("SMS Error", error_msg)
        return False

# === TEST SMS ===
def test_sms():
    """Send test SMS to verify Twilio configuration."""
    def test_thread():
        progress_bar.start(10)
        status_label.config(text="Sending Test SMS...", fg=TEXT_COLOR)
        send_sms("Test message from Stock AI Advisor")
        status_label.config(text="Test SMS Sent", fg=SECONDARY_COLOR)
        progress_bar.stop()
    
    threading.Thread(target=test_thread, daemon=True).start()

# === ANALYSIS + NOTIFICATION ===
def analyze_and_notify():
    """Fetch stock data, analyze with Gemini AI, and send comprehensive SMS."""
    def analysis_thread():
        company = company_entry.get().strip().lower()
        if not company:
            result_label.config(text="Enter a valid company name", fg=ACCENT_COLOR)
            result_text.config(state=NORMAL)
            result_text.delete(1.0, END)
            result_text.insert(END, "Enter a valid company name", "error")
            result_text.config(state=DISABLED)
            progress_bar.stop()
            return

        ticker = COMPANY_TO_TICKER.get(company)
        if not ticker:
            error_msg = f"Company '{company}' not found. Try 'Apple', 'Tesla', 'Microsoft'."
            result_label.config(text=error_msg, fg=ACCENT_COLOR)
            result_text.config(state=NORMAL)
            result_text.delete(1.0, END)
            result_text.insert(END, error_msg, "error")
            result_text.config(state=DISABLED)
            progress_bar.stop()
            return

        progress_bar.start(10)
        result_label.config(text=f"Fetching data for {company.capitalize()} ({ticker})...", fg=TEXT_COLOR)
        result_text.config(state=NORMAL)
        result_text.delete(1.0, END)
        result_text.insert(END, f"Fetching data for {company.capitalize()} ({ticker})...")
        result_text.config(state=DISABLED)
        
        df = fetch_stock_data(ticker)
        if df is None or df.empty:
            error_msg = f"Failed to fetch data for {company.capitalize()} ({ticker})"
            result_label.config(text=error_msg, fg=ACCENT_COLOR)
            result_text.config(state=NORMAL)
            result_text.delete(1.0, END)
            result_text.insert(END, error_msg, "error")
            result_text.config(state=DISABLED)
            progress_bar.stop()
            return

        result_label.config(text="Analyzing with Gemini AI...", fg=TEXT_COLOR)
        result_text.config(state=NORMAL)
        result_text.delete(1.0, END)
        result_text.insert(END, "Analyzing with Gemini AI...")
        result_text.config(state=DISABLED)
        
        prompt = build_prompt(df, company.capitalize(), ticker)
        ai_result = get_gemini_prediction(prompt)

        if not ai_result or "error" in ai_result:
            error_msg = f"Gemini AI Error: {ai_result.get('error', 'Unknown')}\nRaw Response: {ai_result.get('raw', 'No response')}"
            result_label.config(text="Analysis Failed", fg=ACCENT_COLOR)
            result_text.config(state=NORMAL)
            result_text.delete(1.0, END)
            result_text.insert(END, error_msg, "error")
            result_text.config(state=DISABLED)
            progress_bar.stop()
            return

        # Calculate technical score
        latest_data = df.tail(1).iloc[0]
        indicators = {
            'close': df['Close'].values,
            'sma_10': df['SMA_10'].values,
            'sma_20': df['SMA_20'].values,
            'ema_10': df['EMA_10'].values,
            'ema_20': df['EMA_20'].values,
            'rsi': df['RSI'].values,
            'macd': df['MACD'].values,
            'macd_signal': df['MACD_Signal'].values,
            'bb_upper': df['BB_Upper'].values,
            'bb_lower': df['BB_Lower'].values,
            'stoch_k': df['Stoch_K'].values,
            'stoch_d': df['Stoch_D'].values,
            'willr': df['Williams_R'].values,
            'atr': df['ATR'].values,
            'volume': df['Volume'].values,
            'volume_ma': df['Volume_MA'].values,
            'obv': df['OBV'].values,
            'cci': df['CCI'].values,
            'adx': df['ADX'].values,
            'mfi': df['MFI'].values,
            'roc': df['ROC'].values
        }
        technical_score = calculate_technical_score(df, indicators)
        signal_interpretation = interpret_signal(technical_score, ai_result['recommendation'])

        # Infer missing fields if necessary
        if ai_result['timeframe'] in ["Not specified", ""]:
            ai_result['timeframe'] = infer_timeframe(ai_result['recommendation'], technical_score)
        if ai_result['price_target'] in ["Not specified", "", "Current price range"]:
            ai_result['price_target'] = infer_price_target(
                latest_data['Close'], ai_result['recommendation'], technical_score,
                identify_support_resistance(df)[1], identify_support_resistance(df)[0]
            )

        # Format output
        recommendation = ai_result['recommendation']
        if recommendation == "BUY":
            rec_color = ["buy", SECONDARY_COLOR]
        elif recommendation == "SELL":
            rec_color = ["sell", ACCENT_COLOR]
        else:
            rec_color = ["hold", "#FBBC05"]

        output = (
            f"Recommendation: {recommendation}\n"
            f"Primary Factors: {ai_result['primary_factors']}\n"
            f"Supporting Evidence: {ai_result['supporting_evidence']}\n"
            f"Risk Assessment: {ai_result['risk_assessment']}\n"
            f"Confidence: {ai_result['confidence']}\n"
            f"Accuracy: {ai_result['accuracy']}%\n"
            f"Timeframe: {ai_result['timeframe']}\n"
            f"Price Target: {ai_result['price_target']}\n"
            f"Technical Score: {technical_score:.2f}% ({signal_interpretation})\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Current Price: ${latest_data['Close']:.2f}"
        )

        result_label.config(text=f"Recommendation: {recommendation}", fg=rec_color[1])
        result_text.config(state=NORMAL)
        result_text.delete(1.0, END)
        result_text.insert(END, f"Recommendation: ")
        result_text.insert(END, recommendation + "\n", rec_color[0])
        result_text.insert(END, f"Primary Factors: {ai_result['primary_factors']}\n")
        result_text.insert(END, f"Supporting Evidence: {ai_result['supporting_evidence']}\n")
        result_text.insert(END, f"Risk Assessment: {ai_result['risk_assessment']}\n")
        result_text.insert(END, f"Confidence: {ai_result['confidence']}\n")
        result_text.insert(END, f"Accuracy: {ai_result['accuracy']}%\n")
        result_text.insert(END, f"Timeframe: {ai_result['timeframe']}\n")
        result_text.insert(END, f"Price Target: {ai_result['price_target']}\n")
        result_text.insert(END, f"Technical Score: {technical_score:.2f}% ({signal_interpretation})\n")
        result_text.insert(END, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        result_text.insert(END, f"Current Price: ${latest_data['Close']:.2f}")
        result_text.config(state=DISABLED)
        
        status_label.config(text="Analysis Complete", fg=SECONDARY_COLOR)
        
        # Comprehensive SMS message
        sms_message = (
            f"{company.capitalize()} ({ticker}): {recommendation}\n"
            f"Factors: {ai_result['primary_factors'][:80]}\n"
            f"Evidence: {ai_result['supporting_evidence'][:80]}\n"
            f"Risks: {ai_result['risk_assessment'][:80]}\n"
            f"Conf: {ai_result['confidence']}, Acc: {ai_result['accuracy']}%\n"
            f"Time: {ai_result['timeframe']}\n"
            f"Target: {ai_result['price_target']}\n"
            f"Tech: {technical_score:.2f}% ({signal_interpretation})\n"
            f"Price: ${latest_data['Close']:.2f}\n"
            f"TS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if len(sms_message) > 1600:
            sms_message = sms_message[:1597] + "..."
            print("SMS truncated to 1600 chars")
        
        print(f"SMS Content: {sms_message}")
        send_sms(sms_message)
        progress_bar.stop()

    threading.Thread(target=analysis_thread, daemon=True).start()

# === TKINTER UI ===
window = Tk()
window.title("Stock AI Advisor")
window.geometry("800x600")
window.configure(bg=BG_COLOR)

# Custom fonts
title_font = Font(family=FONT_FAMILY, size=18, weight="bold")
button_font = Font(family=FONT_FAMILY, size=12)
text_font = Font(family=FONT_FAMILY, size=11)

# Header Frame
header_frame = Frame(window, bg=BG_COLOR)
header_frame.pack(pady=20)

# Google-style logo
logo_label = Label(header_frame, text="S", font=("Arial", 24, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR)
logo_label.pack(side=LEFT, padx=5)
logo_label = Label(header_frame, text="t", font=("Arial", 24, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
logo_label.pack(side=LEFT, padx=0)
logo_label = Label(header_frame, text="o", font=("Arial", 24, "bold"), fg="#FBBC05", bg=BG_COLOR)
logo_label.pack(side=LEFT, padx=0)
logo_label = Label(header_frame, text="c", font=("Arial", 24, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR)
logo_label.pack(side=LEFT, padx=0)
logo_label = Label(header_frame, text="k", font=("Arial", 24, "bold"), fg=SECONDARY_COLOR, bg=BG_COLOR)
logo_label.pack(side=LEFT, padx=0)
logo_label = Label(header_frame, text=" ", font=("Arial", 24, "bold"), fg=ACCENT_COLOR, bg=BG_COLOR)
logo_label.pack(side=LEFT)

title_label = Label(header_frame, text="Stock AI Advisor", font=title_font, fg=TEXT_COLOR, bg=BG_COLOR)
title_label.pack(side=LEFT, padx=10)

# Company Entry Frame
company_frame = Frame(window, bg=BG_COLOR)
company_frame.pack(pady=10)
company_label = Label(company_frame, text="Enter Company Name:", font=button_font, fg=TEXT_COLOR, bg=BG_COLOR)
company_label.pack(side=LEFT, padx=5)
company_entry = Entry(company_frame, font=text_font, width=20)
company_entry.pack(side=LEFT, padx=5)
company_entry.insert(0, "Tesla")

# Button Frame
button_frame = Frame(window, bg=BG_COLOR)
button_frame.pack(pady=10)

analyze_button = Button(button_frame, text="Analyze & Send SMS", font=button_font, 
                        bg=SECONDARY_COLOR, fg="white", relief=FLAT, 
                        activebackground=SECONDARY_COLOR, activeforeground="white",
                        command=analyze_and_notify)
analyze_button.pack(side=LEFT, padx=15, pady=5)

test_button = Button(button_frame, text="Test SMS", font=button_font, 
                    bg=PRIMARY_COLOR, fg="white", relief=FLAT,
                    activebackground=PRIMARY_COLOR, activeforeground="white",
                    command=test_sms)
test_button.pack(side=LEFT, padx=15, pady=5)

# Progress Bar
progress_frame = Frame(window, bg=BG_COLOR)
progress_frame.pack(pady=10)
progress_bar = ttk.Progressbar(progress_frame, orient=HORIZONTAL, mode='indeterminate', length=400)
progress_bar.pack()

# Result Label
result_label = Label(window, text="Enter a company name to start", font=text_font, fg=TEXT_COLOR, bg=BG_COLOR, wraplength=700)
result_label.pack(pady=10)

# Result Text
result_frame = Frame(window, bg=BG_COLOR)
result_frame.pack(pady=10, padx=20, fill=BOTH, expand=True)

scrollbar = ttk.Scrollbar(result_frame)
scrollbar.pack(side=RIGHT, fill=Y)

result_text = Text(result_frame, wrap=WORD, yscrollcommand=scrollbar.set, 
                   font=text_font, bg="white", fg=TEXT_COLOR, padx=15, pady=10,
                   height=12, relief=SOLID, borderwidth=1)
result_text.pack(fill=BOTH, expand=True)

scrollbar.config(command=result_text.yview)

# Configure tags
result_text.tag_config("error", foreground=ACCENT_COLOR)
result_text.tag_config("buy", foreground=SECONDARY_COLOR)
result_text.tag_config("sell", foreground=ACCENT_COLOR)
result_text.tag_config("hold", foreground="#FFD700")

# Initial message
result_text.config(state=NORMAL)
result_text.insert(END, "Enter a company name and click 'Analyze & Send SMS'")
result_text.config(state=DISABLED)

# Status Bar
status_frame = Frame(window, bg=BG_COLOR)
status_frame.pack(fill=X, pady=(10, 0))
status_label = Label(status_frame, text="Ready", font=text_font, fg=LIGHT_TEXT, bg=BG_COLOR, anchor="w")
status_label.pack(side=LEFT, padx=20)

# Footer
footer_label = Label(window, text="© 2025 Stock AI Advisor | Powered by Gemini AI", 
                     font=("Arial", 9), fg=LIGHT_TEXT, bg=BG_COLOR)
footer_label.pack(side=BOTTOM, pady=10)

window.mainloop()