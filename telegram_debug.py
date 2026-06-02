import requests
import time

TOKEN = "PASTE_YOUR_TOKEN_HERE"

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

print("Listening for Telegram messages...")

while True:
    r = requests.get(url)
    print(r.json())
    time.sleep(3)
