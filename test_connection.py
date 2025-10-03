#!/usr/bin/env python3
"""Test Hyperliquid connection with .env credentials"""

import asyncio
import sys
import os

# Fix encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from config import TradingConfig
from trading_client import TradingClient

async def test_connection():
    print("Testing Hyperliquid Connection...")
    print("=" * 50)

    # Load config (reads from .env)
    config = TradingConfig()

    # Check if credentials are loaded
    if not config.PRIVATE_KEY:
        print("[ERROR] PRIVATE_KEY not found in .env file")
        return False

    if not config.MASTER_WALLET_ADDRESS:
        print("[ERROR] MASTER_WALLET_ADDRESS not found in .env file")
        return False

    print(f"[OK] Private key loaded: {config.PRIVATE_KEY[:6]}...{config.PRIVATE_KEY[-4:]}")
    print(f"[OK] Wallet address: {config.MASTER_WALLET_ADDRESS}")
    print(f"[OK] Account address: {config.account_address}")
    print(f"[OK] Testnet mode: {config.TESTNET}")
    print(f"[OK] Symbol: {config.SYMBOL}")
    print()

    # Initialize trading client
    try:
        client = TradingClient(config)
        print("[OK] Trading client initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return False

    # Test connection by fetching account info using Info API
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants

        base_url = constants.TESTNET_API_URL if config.TESTNET else constants.MAINNET_API_URL
        info = Info(base_url=base_url, skip_ws=True)

        print("\nFetching account information...")
        user_state = info.user_state(client.user_address)

        # Extract account value
        account_value = float(user_state.get('marginSummary', {}).get('accountValue', 0))
        print(f"[OK] Account Value: ${account_value:,.2f}")

        # Extract and display margin info
        margin_summary = user_state.get('marginSummary', {})
        total_margin = float(margin_summary.get('totalMarginUsed', 0))
        total_ntl_pos = float(margin_summary.get('totalNtlPos', 0))
        print(f"[OK] Total Margin Used: ${total_margin:,.2f}")
        print(f"[OK] Total Notional Position: ${total_ntl_pos:,.2f}")

        print("\nFetching positions...")
        positions = user_state.get('assetPositions', [])
        if positions:
            print(f"[OK] Active Positions: {len(positions)}")
            for pos in positions:
                position_data = pos.get('position', {})
                coin = position_data.get('coin', 'N/A')
                size = position_data.get('szi', 0)
                entry_px = position_data.get('entryPx', 0)
                unrealized_pnl = position_data.get('unrealizedPnl', 0)
                print(f"   - {coin}: {size} @ ${entry_px} (PnL: ${unrealized_pnl})")
        else:
            print("[OK] No active positions")

        print("\nFetching open orders...")
        open_orders = info.open_orders(client.user_address)
        if open_orders:
            print(f"[OK] Open Orders: {len(open_orders)}")
            for order in open_orders[:5]:  # Show first 5
                coin = order.get('coin', 'N/A')
                side = order.get('side', 'N/A')
                sz = order.get('sz', 0)
                limit_px = order.get('limitPx', 0)
                oid = order.get('oid', 'N/A')
                print(f"   - [{oid}] {coin}: {side} {sz} @ ${limit_px}")
        else:
            print("[OK] No open orders")

        print("\n" + "=" * 50)
        print("[SUCCESS] CONNECTION TEST SUCCESSFUL!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n[ERROR] Connection test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
