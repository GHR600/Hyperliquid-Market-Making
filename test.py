from hyperliquid.info import Info
from hyperliquid.utils import constants
import requests

account_address = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
#API_SECRET = "0xaf9fcec0eaefdded38e03236b70aa42bfde3f5145a2ca9e49f0687c012a9b1a5"


info = Info(constants.MAINNET_API_URL, skip_ws=True)
user_state = info.user_state(account_address)
print(user_state)

import requests

def get_sz_decimals(asset_name="BTC"):
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    payload = {
        "type": "metaAndAssetCtxs"
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    # Ensure we have a dictionary to work with
    if isinstance(data, list):
        # If API returned a list, take the first element (usually the dict with "universe")
        if len(data) > 0 and isinstance(data[0], dict):
            data = data[0]
        else:
            raise ValueError("Unexpected API response format.")

    for asset in data.get("universe", []):
        if asset.get("name") == asset_name:
            return asset_name, asset.get("szDecimals")

    return asset_name, None


# Example usage
asset, decimals = get_sz_decimals("BTC")
print(f"Asset: {asset}, Size decimals (szDecimals): {decimals}")
