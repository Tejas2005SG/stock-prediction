import requests
import re
from datetime import datetime
from src.config import GEMINI_API_KEY
from src.analysis.technical import identify_support_resistance

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
