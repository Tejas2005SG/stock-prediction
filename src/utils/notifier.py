from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from tkinter import messagebox
from src.config import TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE, YOUR_PHONE

def send_sms(message):
    """Send SMS using Twilio with debugging and DLT compliance."""
    try:
        print(f"\n=== Sending SMS ===\nFrom: {TWILIO_PHONE}\nTo: {YOUR_PHONE}\nMessage: {message}\nLength: {len(message)} chars")
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        # account = client.api.accounts(TWILIO_SID).fetch()
        # print(f"Twilio account status: {account.status}")
        
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
