import yfinance as yf
import pandas_ta as ta

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
