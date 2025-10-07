import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class TradingConfig:
    # Exchange settings - SDK handles authentication automatically
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    # Account data - Master wallet address for balance/position queries
    MASTER_WALLET_ADDRESS: str = os.getenv("MASTER_WALLET_ADDRESS", "")
    account_address: str = os.getenv("ACCOUNT_ADDRESS", os.getenv("MASTER_WALLET_ADDRESS", ""))
    TESTNET: bool = os.getenv("TESTNET", "False").lower() == "true"
    
    # Trading parameters
    SYMBOL: str = "ETH"  # Hyperliquid uses coin symbols like "BTC", "ETH"
    BASE_SPREAD: float = 0.001  # 0.1% spread
    
    # Symbol-specific parameters (will be auto-fetched)
    SIZE_DECIMALS: int = 2  # Will be updated from API
    PRICE_DECIMALS: int = 2
    MAX_LEVERAGE: float = 8000.0  # Will be updated from API
    
    # Position sizing (choose ONE approach)
    USE_PERCENTAGE_SIZING: bool = True  # Set to False for fixed sizing
    
    # Percentage-based sizing (when USE_PERCENTAGE_SIZING = True)
    ORDER_SIZE_PCT: float = 300.0  # 300% of account value per order
    MAX_POSITION_PCT: float = 8000.0  # Will be set to max leverage from API

    # Risk management
    MAX_ORDERS_PER_SIDE: int = 3
    REBALANCE_THRESHOLD: float = 0.01  # 1%
    MIN_ORDER_SIZE: float = 0.00000001  # Minimum order size
    MIN_ACCOUNT_VALUE: float = 1.0  # Minimum account value to trade
    
    # =================== LEARNING PHASE ===================
    
    # Learning phase settings
    LEARNING_PHASE_DURATION: float = 0.0  # 5 minutes in seconds (adjust as needed)
    ENABLE_LEARNING_PHASE: bool = True      # Set to False to skip learning phase
    
    # Learning phase behavior
    LEARNING_PHASE_UPDATE_INTERVAL: float = 0.01  # Faster updates during learning
    LEARNING_PHASE_LOG_INTERVAL: float = 30.0    # Log progress every 30 seconds
    
    # Minimum data requirements before going live
    MIN_ORDERBOOK_SNAPSHOTS: int = 150   # Minimum orderbook updates needed
    MIN_TRADE_EVENTS: int = 200          # Minimum trades observed
    
    # What to collect during learning
    COLLECT_SPREAD_STATISTICS: bool = True
    COLLECT_VOLUME_STATISTICS: bool = True
    COLLECT_PRICE_MOVEMENT_STATS: bool = True
    
    # =================== FASTER ORDER MANAGEMENT ===================
    
    # Timing - Make these much faster
    UPDATE_INTERVAL: float = 0.01  # Reduced from 5.0 to 0.01 seconds
    ORDER_REFRESH_INTERVAL: float = 0.5  # New: How often to check/refresh orders
    QUICK_CANCEL_THRESHOLD: float = 0.02  # 2% - Cancel orders faster when price moves
    
    # Order Management Strategy
    ENABLE_AGGRESSIVE_REFRESH: bool = True  # Enable fast order refresh
    MAX_ORDER_AGE_SECONDS: float = 15.0  # Cancel orders after 15 seconds regardless
    PRICE_MOVEMENT_CANCEL_THRESHOLD: float = 0.001  # 0.1% price movement triggers cancel

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
    ORDERBOOK_HISTORY_SIZE: int = 300  # Number of orderbook snapshots to keep
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
    VWAP_WINDOW: int = 450  # Number of trades for VWAP calculation
    MOMENTUM_WINDOW: int = 450  # Number of trades for momentum calculation
    ACCUMULATION_WINDOW: int = 450  # Trades to analyze for accumulation/distribution
    TRADE_VELOCITY_WINDOW: int = 450  # Trades to measure velocity
    
    # Signal Generation Thresholds
    STRONG_MOMENTUM_THRESHOLD: float = 0.6  # Threshold for "strong" momentum signal
    FLOW_CONFIDENCE_THRESHOLD: float = 0.6  # Min confidence for acting on flow signals
    ADVERSE_SELECTION_THRESHOLD: float = 0.5  # Threshold for adverse selection risk
    
    # Dynamic Strategy Adjustments
    SPREAD_ADJUSTMENT_MULTIPLIER: float = 1.0  # How much to adjust spreads based on signals
    SIZE_ADJUSTMENT_MULTIPLIER: float = 1.5  # How much to adjust sizes based on flow
    SIGNAL_DECAY_FACTOR: float = 0.7  # How quickly signals decay over time
    
    # Flow-Based Position Management
    FLOW_POSITION_MULTIPLIER: float = 2.0  # Increase position sizing when flow aligns
    ADVERSE_FLOW_REDUCTION: float = 0.5  # Reduce sizing when flow is adverse
    REBALANCE_FLOW_THRESHOLD: float = 0.8  # Flow strength needed for aggressive rebalancing
    
    # =================== RISK MANAGEMENT ===================
    
    # Stop-loss settings
    ENABLE_STOP_LOSS: bool = True
    STOP_LOSS_PCT: float = 2.0  # 2% stop loss from entry
    TRAILING_STOP_LOSS: bool = True
    TRAILING_STOP_DISTANCE: float = 1.0  # 1% trailing distance
    
    # Profit-taking settings  
    ENABLE_PROFIT_TAKING: bool = True
    PROFIT_TARGET_PCT: float = 1.5  # 1.5% profit target
    PARTIAL_PROFIT_LEVELS: List[float] = None  # Will be set to [0.5, 1.0, 1.5]
    PARTIAL_PROFIT_SIZE_PCT: float = 25.0  # Take 25% profit at each level
    
    # Position skewing for profit
    ENABLE_PROFIT_SKEW: bool = True
    MAX_PROFIT_SKEW: float = 0.5  # Max 0.5% additional skew
    PROFIT_SKEW_SCALING: float = 0.6  # How aggressively to skew
    
    # Emergency controls
    MAX_DAILY_LOSS_PCT: float = 35.0  # Stop trading if daily loss > 5%
    MAX_POSITION_LOSS_PCT: float = 13.0  # Force close if position loss > 3%
    ENABLE_EMERGENCY_STOPS: bool = True
    
    # Risk monitoring
    RISK_CHECK_INTERVAL: float = 0.5  # Check risk every 500ms
    LOG_RISK_STATUS: bool = True

    # =================== FUNDING RATE MONITORING ===================

    # Funding rate alerts
    ENABLE_FUNDING_ALERTS: bool = True  # Enable funding rate monitoring
    HIGH_FUNDING_THRESHOLD: float = 0.0001  # 0.01% - Alert when abs(funding) exceeds this

    # Funding rate thresholds for strategy adjustments
    EXTREME_FUNDING_THRESHOLD: float = 0.0005  # 0.05% - Very high funding
    FUNDING_CHECK_INTERVAL: float = 60.0  # Check funding every 60 seconds

    # =================== INTELLIGENT ORDER PLACEMENT ===================

    # Join existing liquidity levels
    JOIN_EXISTING_LEVELS: bool = True  # Try to join existing orders instead of creating new levels
    MIN_JOIN_SIZE_MULTIPLIER: float = 0.01  # Minimum size to join (1% of fair value)
    MAX_JOIN_DISTANCE_PCT: float = 0.003  # Maximum distance from fair value to join (0.3%)

    def __post_init__(self):
        """Set default values that depend on other config values"""
        if self.TRADE_SIZE_PERCENTILES is None:
            self.TRADE_SIZE_PERCENTILES = [25, 50, 75, 90, 95]
        
        # Fix for missing PARTIAL_PROFIT_LEVELS
        if not hasattr(self, 'PARTIAL_PROFIT_LEVELS') or self.PARTIAL_PROFIT_LEVELS is None:
            self.PARTIAL_PROFIT_LEVELS = [0.5, 1.0, 1.5]