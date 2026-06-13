import requests
import logging

class WhatsAppNotifier:
    def __init__(self, token, phone_id, recipient_phone):
        self.token = token
        self.phone_id = phone_id
        self.recipient_phone = recipient_phone
        self.url = f"https://graph.facebook.com/v17.0/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def send_message(self, text):
        if not self.token or self.token == "YOUR_WHATSAPP_ACCESS_TOKEN":
            logging.warning("WhatsApp token not configured. Message not sent.")
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": self.recipient_phone,
            "type": "text",
            "text": {"body": text}
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Failed to send WhatsApp message: {e}")
            return False

    def notify_trade_opened(self, symbol, trade_type, entry, sl, tp, risk):
        msg = (
            f"🔔 *TRADE OPENED*\n\n"
            f"Symbol: {symbol}\n"
            f"Type: {trade_type}\n"
            f"Entry: {entry}\n"
            f"SL: {sl}\n"
            f"TP: {tp}\n"
            f"Risk: {risk}%"
        )
        return self.send_message(msg)

    def notify_trade_closed(self, symbol, profit):
        status = "✅ PROFIT" if profit > 0 else "❌ LOSS"
        msg = (
            f"🏁 *TRADE CLOSED*\n\n"
            f"Symbol: {symbol}\n"
            f"Result: {status}\n"
            f"Profit/Loss: ${profit:.2f}"
        )
        return self.send_message(msg)

    def notify_alert(self, title, message):
        msg = f"⚠️ *{title.upper()}*\n\n{message}"
        return self.send_message(msg)
