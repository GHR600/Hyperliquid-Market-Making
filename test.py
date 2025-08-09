from hyperliquid.info import Info
from hyperliquid.utils import constants

account_address = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
#API_SECRET = "0xaf9fcec0eaefdded38e03236b70aa42bfde3f5145a2ca9e49f0687c012a9b1a5"


info = Info(constants.MAINNET_API_URL, skip_ws=True)
user_state = info.user_state(account_address)
print(user_state)