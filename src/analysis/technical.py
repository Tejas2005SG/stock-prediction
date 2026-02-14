import numpy as np

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
