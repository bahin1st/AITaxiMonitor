import requests

def send_telegram_alert(chat_id, message):
    
    bot_token = "7880331751:AAFjx7puCAbce9Eq4KfkWkEiw-B8OpBv5Z8"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")
    else:
        print(f"Message sent to {chat_id}")
