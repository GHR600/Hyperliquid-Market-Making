
import os
from dataclasses import dataclass
from typing import List

@dataclass
class TradingConfig:
    # Exchange settings - SDK handles authentication automatically
    PRIVATE_KEY: str = "0xaf9fcec0eaefdded38e03236b70aa42bfde3f5145a2ca9e49f0687c012a9b1a5"#os.getenv('HYPERLIQUID_PRIVATE_KEY', '')  # Your wallet private key
    # Account data - Master wallet address for balance/position queries  
    MASTER_WALLET_ADDRESS: str = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"  # Master wallet with funds
    
    TESTNET: bool = False #os.getenv('HYPERLIQUID_TESTNET', 'false').lower() == 'true'
    
    # Trading parameters
    SYMBOL: str = "AAVE"  # Hyperliquid uses coin symbols like "BTC", "ETH"
    BASE_SPREAD: float = 0.001  # 0.1% spread
    
    # Position sizing (choose ONE approach)
    USE_PERCENTAGE_SIZING: bool = True  # Set to False for fixed sizing
    
    # Percentage-based sizing (when USE_PERCENTAGE_SIZING = True)
    ORDER_SIZE_PCT: float = 10.0  # 25% of account value per order
    MAX_POSITION_PCT: float = 40.0  # 99% of account value max position

    # Fixed sizing (when USE_PERCENTAGE_SIZING = False)
   # ORDER_SIZE: float = 0.01    # Fixed order size in base currency
   # MAX_POSITION: float = 0.1   # Fixed maximum position size
    
    # Risk management
    MAX_ORDERS_PER_SIDE: int = 3
    REBALANCE_THRESHOLD: float = 0.0005  # 0.05%
    MIN_ORDER_SIZE: float = 1.0  # Minimum order size
    MIN_ACCOUNT_VALUE: float = 1.0  # Minimum account value to trade
    
    # Timing
    UPDATE_INTERVAL: float = 2.0  # seconds
    ORDER_REFRESH_INTERVAL: float = 30.0  # seconds
    
    # Safety
    ENABLE_TRADING: bool = True  # Set to True when ready
    LOG_LEVEL: str = "INFO"
    
    # Order types
    ORDER_TYPE: str = "limit"  # limit, market, etc.
    TIME_IN_FORCE: str = "Gtc"  # Good till cancelled