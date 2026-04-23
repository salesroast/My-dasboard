import requests
from dotenv import load_dotenv
import os

load_dotenv()

SHOP = os.environ.get("SHOPIFY_SHOP_DOMAIN")
CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET")

print("SHOP:", SHOP)
print("CLIENT_ID:", CLIENT_ID)
print("SECRET cargado:", bool(CLIENT_SECRET))

url = f"https://{SHOP}/admin/oauth/access_token"
payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials"
}

r = requests.post(url, json=payload)
print("Status:", r.status_code)
print("Respuesta:", r.text)