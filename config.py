import os
from dataclasses import dataclass
from typing import List

@dataclass
class TradingConfig:
    # Exchange settings - SDK handles authentication automatically
    PRIVATE_KEY: str = "0xaf9fcec0eaefdded38e03236b70aa42bfde3f5145a2ca9e49f0687c012a9b1a5"
    # Account data - Master wallet address for balance/position queries  
    MASTER_WALLET_ADDRESS: str = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
    account_address = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
    TESTNET: bool = False
    
    # Trading parameters
    SYMBOL: str = "LINK"  # Hyperliquid uses coin symbols like "BTC", "ETH"
    BASE_SPREAD: float = 0.003  # 0.1% spread
    
    # Symbol-specific parameters (will be auto-fetched)
    SIZE_DECIMALS: int = 2  # Will be updated from API
    PRICE_DECIMALS: int = 8 - SIZE_DECIMALS  # Will be updated from API - NEW
    MAX_LEVERAGE: float = 8000.0  # Will be updated from API
    
    # Position sizing (choose ONE approach)
    USE_PERCENTAGE_SIZING: bool = True  # Set to False for fixed sizing
    
    # Percentage-based sizing (when USE_PERCENTAGE_SIZING = True)
    ORDER_SIZE_PCT: float = 300.0  # 1% of account value per order
    MAX_POSITION_PCT: float = 8000.0  # Will be set to max leverage from API

    # Risk management
    MAX_ORDERS_PER_SIDE: int = 3
    REBALANCE_THRESHOLD: float = 0.01  # 0.05%
    MIN_ORDER_SIZE: float = 0.00000001  # Minimum order size
    MIN_ACCOUNT_VALUE: float = 1.0  # Minimum account value to trade
    
    
    # =================== FASTER ORDER MANAGEMENT ===================
    
    # Timing - Make these much faster
    UPDATE_INTERVAL: float = 1.0  # Reduced from 5.0 to 1.0 seconds
    ORDER_REFRESH_INTERVAL: float = 0.5  # New: How often to check/refresh orders
    QUICK_CANCEL_THRESHOLD: float = 0.02  # 2% - Cancel orders faster when price moves
    
    # Order Management Strategy
    ENABLE_AGGRESSIVE_REFRESH: bool = True  # Enable fast order refresh
    MAX_ORDER_AGE_SECONDS: float = 10.0  # Cancel orders after 10 seconds regardless
    PRICE_MOVEMENT_CANCEL_THRESHOLD: float = 0.005  # 0.5% price movement triggers cancel
    
    # Performance Optimizations
    BATCH_ORDER_OPERATIONS: bool = True  # Cancel and place orders in batches
    SKIP_ACCOUNT_UPDATE_FREQUENCY: int = 3  # Only update account every 3rd loop
    ENABLE_FAST_MODE: bool = True  # Skip some heavy calculations when needed
    
    # Microstructure-based order refresh
    HIGH_VELOCITY_THRESHOLD: float = 0.05  # When to refresh orders more aggressively
    FLOW_CHANGE_THRESHOLD: float = 0.3  # Significant flow change triggers refresh
    
    # Safety
    ENABLE_TRADING: bool = True  # Set to True when ready
    LOG_LEVEL: str = "INFO"
    
    # Order types
    ORDER_TYPE: str = "limit"  # limit, market, etc.
    TIME_IN_FORCE: str = "Gtc"  # Good till cancelled
    
    # =================== MICROSTRUCTURE ANALYSIS PARAMETERS ===================
    
    # Data Collection Windows
    ORDERBOOK_HISTORY_SIZE: int = 100  # Number of orderbook snapshots to keep
    TRADE_HISTORY_SIZE: int = 500     # Number of recent trades to analyze
    MICROSTRUCTURE_UPDATE_INTERVAL: float = 1.0  # How often to update analysis
    
    # Order Flow Imbalance Detection
    IMBALANCE_DEPTH_LEVELS: int = 15   # How many price levels to analyze for imbalance
    LARGE_ORDER_THRESHOLD: float = 5.0  # Multiple of average order size to consider "large"
    VOLUME_IMBALANCE_THRESHOLD: float = 1.5  # Ratio threshold for bid/ask imbalance
    DEPTH_PRESSURE_THRESHOLD: float = 0.3  # Threshold for detecting depth pressure
    
    # Orderbook Dynamics
    ORDER_VELOCITY_WINDOW: int = 30   # Snapshots to analyze for order add/remove velocity
    SPREAD_VOLATILITY_WINDOW: int = 20  # Window for spread dynamics analysis
    LEVEL_STICKINESS_THRESHOLD: float = 0.7  # Persistence required to consider level "sticky"
    LEVEL_STICKINESS_WINDOW: int = 30  # Snapshots to check for level persistence
    
    # Trade Flow Analysis
    TRADE_SIZE_PERCENTILES: List[float] = None  # Will be set to [25, 50, 75, 90, 95]
    VWAP_WINDOW: int = 150  # Number of trades for VWAP calculation
    MOMENTUM_WINDOW: int = 150  # Number of trades for momentum calculation
    ACCUMULATION_WINDOW: int = 150  # Trades to analyze for accumulation/distribution
    TRADE_VELOCITY_WINDOW: int = 150  # Trades to measure velocity
    
    # Signal Generation Thresholds
    STRONG_MOMENTUM_THRESHOLD: float = 0.7  # Threshold for "strong" momentum signal
    FLOW_CONFIDENCE_THRESHOLD: float = 0.6  # Min confidence for acting on flow signals
    ADVERSE_SELECTION_THRESHOLD: float = 0.8  # Threshold for adverse selection risk
    
    # Dynamic Strategy Adjustments
    SPREAD_ADJUSTMENT_MULTIPLIER: float = 0.5  # How much to adjust spreads based on signals
    SIZE_ADJUSTMENT_MULTIPLIER: float = 1.5  # How much to adjust sizes based on flow
    SIGNAL_DECAY_FACTOR: float = 0.95  # How quickly signals decay over time
    
    # Flow-Based Position Management
    FLOW_POSITION_MULTIPLIER: float = 2.0  # Increase position sizing when flow aligns
    ADVERSE_FLOW_REDUCTION: float = 0.5  # Reduce sizing when flow is adverse
    REBALANCE_FLOW_THRESHOLD: float = 0.8  # Flow strength needed for aggressive rebalancing
    
    def __post_init__(self):
        """Set default values that depend on other config values"""
        if self.TRADE_SIZE_PERCENTILES is None:
            self.TRADE_SIZE_PERCENTILES = [25, 50, 75, 90, 95]