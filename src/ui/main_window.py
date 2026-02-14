import threading
from tkinter import *
from tkinter import ttk, messagebox
from tkinter.font import Font
from datetime import datetime
import numpy as np

from src.config import *
from src.data.stock_data import fetch_stock_data
from src.analysis.gemini import get_gemini_prediction, build_prompt
from src.analysis.technical import (
    calculate_technical_score, identify_support_resistance, 
    infer_timeframe, infer_price_target, interpret_signal
)
from src.utils.notifier import send_sms

class StockAIApp:
    def __init__(self, root):
        self.window = root
        self.window.title("Stock AI Advisor")
        self.window.geometry("800x600")
        self.window.configure(bg=BG_COLOR)
        
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        self.title_font = Font(family=FONT_FAMILY, size=18, weight="bold")
        self.button_font = Font(family=FONT_FAMILY, size=12)
        self.text_font = Font(family=FONT_FAMILY, size=11)

    def create_widgets(self):
        # Header Frame
        header_frame = Frame(self.window, bg=BG_COLOR)
        header_frame.pack(pady=20)

        # Google-style logo
        colors = [PRIMARY_COLOR, ACCENT_COLOR, "#FBBC05", PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR]
        logo_text = "Stock "
        for i, char in enumerate(logo_text):
            Label(header_frame, text=char, font=("Arial", 24, "bold"), 
                  fg=colors[i % len(colors)], bg=BG_COLOR).pack(side=LEFT, padx=0)

        Label(header_frame, text="Stock AI Advisor", font=self.title_font, 
              fg=TEXT_COLOR, bg=BG_COLOR).pack(side=LEFT, padx=10)

        # Company Entry Frame
        company_frame = Frame(self.window, bg=BG_COLOR)
        company_frame.pack(pady=10)
        Label(company_frame, text="Enter Company Name:", font=self.button_font, 
              fg=TEXT_COLOR, bg=BG_COLOR).pack(side=LEFT, padx=5)
        self.company_entry = Entry(company_frame, font=self.text_font, width=20)
        self.company_entry.pack(side=LEFT, padx=5)
        self.company_entry.insert(0, "Tesla")

        # Button Frame
        button_frame = Frame(self.window, bg=BG_COLOR)
        button_frame.pack(pady=10)

        self.analyze_button = Button(button_frame, text="Analyze & Send SMS", font=self.button_font, 
                                     bg=SECONDARY_COLOR, fg="white", relief=FLAT, 
                                     activebackground=SECONDARY_COLOR, activeforeground="white",
                                     command=self.analyze_and_notify)
        self.analyze_button.pack(side=LEFT, padx=15, pady=5)

        self.test_button = Button(button_frame, text="Test SMS", font=self.button_font, 
                                 bg=PRIMARY_COLOR, fg="white", relief=FLAT,
                                 activebackground=PRIMARY_COLOR, activeforeground="white",
                                 command=self.test_sms)
        self.test_button.pack(side=LEFT, padx=15, pady=5)

        # Progress Bar
        progress_frame = Frame(self.window, bg=BG_COLOR)
        progress_frame.pack(pady=10)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=HORIZONTAL, mode='indeterminate', length=400)
        self.progress_bar.pack()

        # Result Label
        self.result_label = Label(self.window, text="Enter a company name to start", 
                                  font=self.text_font, fg=TEXT_COLOR, bg=BG_COLOR, wraplength=700)
        self.result_label.pack(pady=10)

        # Result Text
        result_frame = Frame(self.window, bg=BG_COLOR)
        result_frame.pack(pady=10, padx=20, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.result_text = Text(result_frame, wrap=WORD, yscrollcommand=scrollbar.set, 
                                font=self.text_font, bg="white", fg=TEXT_COLOR, padx=15, pady=10,
                                height=12, relief=SOLID, borderwidth=1)
        self.result_text.pack(fill=BOTH, expand=True)

        scrollbar.config(command=self.result_text.yview)

        # Configure tags
        self.result_text.tag_config("error", foreground=ACCENT_COLOR)
        self.result_text.tag_config("buy", foreground=SECONDARY_COLOR)
        self.result_text.tag_config("sell", foreground=ACCENT_COLOR)
        self.result_text.tag_config("hold", foreground="#FBBC05")

        # Initial message
        self.result_text.config(state=NORMAL)
        self.result_text.insert(END, "Enter a company name and click 'Analyze & Send SMS'")
        self.result_text.config(state=DISABLED)

        # Status Bar
        status_frame = Frame(self.window, bg=BG_COLOR)
        status_frame.pack(fill=X, pady=(10, 0))
        self.status_label = Label(status_frame, text="Ready", font=self.text_font, 
                                  fg=LIGHT_TEXT, bg=BG_COLOR, anchor="w")
        self.status_label.pack(side=LEFT, padx=20)

        # Footer
        Label(self.window, text="© 2025 Stock AI Advisor | Powered by Gemini AI", 
              font=("Arial", 9), fg=LIGHT_TEXT, bg=BG_COLOR).pack(side=BOTTOM, pady=10)

    def test_sms(self):
        """Send test SMS to verify Twilio configuration."""
        def test_thread():
            self.progress_bar.start(10)
            self.status_label.config(text="Sending Test SMS...", fg=TEXT_COLOR)
            send_sms("Test message from Stock AI Advisor")
            self.status_label.config(text="Test SMS Sent", fg=SECONDARY_COLOR)
            self.progress_bar.stop()
        
        threading.Thread(target=test_thread, daemon=True).start()

    def analyze_and_notify(self):
        """Fetch stock data, analyze with Gemini AI, and send comprehensive SMS."""
        def analysis_thread():
            company = self.company_entry.get().strip().lower()
            if not company:
                self.update_result_text("Enter a valid company name", "error")
                return

            ticker = COMPANY_TO_TICKER.get(company)
            if not ticker:
                error_msg = f"Company '{company}' not found. Try 'Apple', 'Tesla', 'Microsoft'."
                self.update_result_text(error_msg, "error")
                return

            self.progress_bar.start(10)
            self.update_result_text(f"Fetching data for {company.capitalize()} ({ticker})...")
            
            df = fetch_stock_data(ticker)
            if df is None or df.empty:
                error_msg = f"Failed to fetch data for {company.capitalize()} ({ticker})"
                self.update_result_text(error_msg, "error")
                self.progress_bar.stop()
                return

            self.update_result_text("Analyzing with Gemini AI...")
            
            prompt = build_prompt(df, company.capitalize(), ticker)
            ai_result = get_gemini_prediction(prompt)

            if not ai_result or "error" in ai_result:
                error_msg = f"Gemini AI Error: {ai_result.get('error', 'Unknown')}\nRaw Response: {ai_result.get('raw', 'No response')}"
                self.update_result_text(error_msg, "error")
                self.progress_bar.stop()
                return

            # Technical score calculation
            indicators = {
                'close': df['Close'].values,
                'sma_10': df['SMA_10'].values, 'sma_20': df['SMA_20'].values,
                'ema_10': df['EMA_10'].values, 'ema_20': df['EMA_20'].values,
                'rsi': df['RSI'].values, 'macd': df['MACD'].values,
                'macd_signal': df['MACD_Signal'].values,
                'bb_upper': df['BB_Upper'].values, 'bb_lower': df['BB_Lower'].values,
                'stoch_k': df['Stoch_K'].values, 'stoch_d': df['Stoch_D'].values,
                'willr': df['Williams_R'].values, 'atr': df['ATR'].values,
                'volume': df['Volume'].values, 'volume_ma': df['Volume_MA'].values,
                'obv': df['OBV'].values, 'cci': df['CCI'].values,
                'adx': df['ADX'].values, 'mfi': df['MFI'].values,
                'roc': df['ROC'].values
            }
            technical_score = calculate_technical_score(df, indicators)
            signal_interpretation = interpret_signal(technical_score, ai_result['recommendation'])

            # Infer missing fields
            latest_data = df.tail(1).iloc[0]
            if ai_result['timeframe'] in ["Not specified", ""]:
                ai_result['timeframe'] = infer_timeframe(ai_result['recommendation'], technical_score)
            if ai_result['price_target'] in ["Not specified", "", "Current price range"]:
                support, resistance = identify_support_resistance(df)
                ai_result['price_target'] = infer_price_target(
                    latest_data['Close'], ai_result['recommendation'], technical_score,
                    resistance, support
                )

            # Update UI
            self.display_analysis_result(ai_result, technical_score, signal_interpretation, latest_data, company, ticker)
            
            # Send SMS
            self.send_analysis_sms(ai_result, technical_score, signal_interpretation, latest_data, company, ticker)
            
            self.progress_bar.stop()
            self.status_label.config(text="Analysis Complete", fg=SECONDARY_COLOR)

        threading.Thread(target=analysis_thread, daemon=True).start()

    def update_result_text(self, text, tag=None):
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        if tag:
            self.result_text.insert(END, text, tag)
            self.result_label.config(text=text, fg=ACCENT_COLOR if tag == "error" else TEXT_COLOR)
        else:
            self.result_text.insert(END, text)
        self.result_text.config(state=DISABLED)

    def display_analysis_result(self, ai_result, technical_score, signal_interpretation, latest_data, company, ticker):
        recommendation = ai_result['recommendation']
        rec_tag = recommendation.lower() if recommendation in ["BUY", "SELL", "HOLD"] else None
        rec_color = SECONDARY_COLOR if recommendation == "BUY" else ACCENT_COLOR if recommendation == "SELL" else "#FBBC05"

        self.result_label.config(text=f"Recommendation: {recommendation}", fg=rec_color)
        
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, "Recommendation: ")
        self.result_text.insert(END, f"{recommendation}\n", rec_tag)
        self.result_text.insert(END, f"Primary Factors: {ai_result['primary_factors']}\n")
        self.result_text.insert(END, f"Supporting Evidence: {ai_result['supporting_evidence']}\n")
        self.result_text.insert(END, f"Risk Assessment: {ai_result['risk_assessment']}\n")
        self.result_text.insert(END, f"Confidence: {ai_result['confidence']}\n")
        self.result_text.insert(END, f"Accuracy: {ai_result['accuracy']}%\n")
        self.result_text.insert(END, f"Timeframe: {ai_result['timeframe']}\n")
        self.result_text.insert(END, f"Price Target: {ai_result['price_target']}\n")
        self.result_text.insert(END, f"Technical Score: {technical_score:.2f}% ({signal_interpretation})\n")
        self.result_text.insert(END, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.result_text.insert(END, f"Current Price: ${latest_data['Close']:.2f}")
        self.result_text.config(state=DISABLED)

    def send_analysis_sms(self, ai_result, technical_score, signal_interpretation, latest_data, company, ticker):
        sms_message = (
            f"{company.capitalize()} ({ticker}): {ai_result['recommendation']}\n"
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
        send_sms(sms_message)

def run_app():
    root = Tk()
    app = StockAIApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
