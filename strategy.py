# enhanced_strategy_with_stoploss.py - Add to your enhanced_strategy.py

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
from config import TradingConfig
from core.position_tracker import Position, Order
from analysis.market_microstructure import MarketSignals
from analysis.orderbook_analyzer import OrderbookAnalyzer, OrderbookImbalance, OrderbookGaps, LiquidityProfile, MarketCondition, AdverseSelectionRisk

# Import base strategy classes inline to avoid circular dependency
import logging
from typing import Dict, List, Tuple, Optional

# Base Enhanced Strategy Class (consolidated from enhanced_strategy.py)
class EnhancedMarketMakingStrategy:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize orderbook analyzer
        self.orderbook_analyzer = OrderbookAnalyzer(config)

        # Track our fills for adverse selection analysis
        self.recent_fills = []

        print(f"🎯 Enhanced MarketMaking Strategy initialized")
        print(f"   - Base spread: {config.BASE_SPREAD * 100:.2f}%")
        print(f"   - Order size: {'percentage-based' if config.USE_PERCENTAGE_SIZING else 'fixed'}")
        print(f"   - Max orders per side: {config.MAX_ORDERS_PER_SIDE}")
        print(f"   - Orderbook-based decision making: ENABLED")

    def update_baselines_from_learning(self, learning_stats: Dict):
        """Update strategy baselines from learning phase"""
        print("🎓 Strategy: Updating baselines from learning phase...")
        self.orderbook_analyzer.update_baselines_from_learning(learning_stats)

    def calculate_fair_price(self, orderbook: Dict) -> Optional[float]:
        """Calculate sophisticated fair price using orderbook analysis"""
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        if imbalance.weighted_mid == 0:
            return None
        return self.orderbook_analyzer.calculate_smart_fair_price(orderbook, imbalance)

    def should_place_orders(self, position: Optional[Position], orderbook: Dict, signals: Optional[MarketSignals] = None) -> bool:
        """Enhanced order placement decision using orderbook analysis"""
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)

        if not self.orderbook_analyzer.should_place_orders(condition, adverse_risk):
            return False

        if position and abs(position.size) >= self.config.MAX_POSITION_PCT:
            return False

        if signals and signals.adverse_selection_risk > self.config.ADVERSE_SELECTION_THRESHOLD:
            return False

        return True

    def calculate_order_prices(self, fair_price: float, orderbook: Dict, position: Optional[Position],
                              signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Calculate order prices using orderbook analysis"""
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)

        base_spread = self.config.BASE_SPREAD
        spread_multiplier = 1.0

        if condition.condition_type == "CALM":
            spread_multiplier *= 0.8
        elif condition.condition_type == "VOLATILE":
            spread_multiplier *= 1.5

        adjusted_spread = base_spread * spread_multiplier
        bid_spread = adjusted_spread / 2
        ask_spread = adjusted_spread / 2

        bid_price = fair_price * (1 - bid_spread)
        ask_price = fair_price * (1 + ask_spread)

        tick_size = orderbook.get('tick_size', 0.5)
        bid_price = round(bid_price / tick_size) * tick_size
        ask_price = round(ask_price / tick_size) * tick_size

        return round(bid_price, self.config.PRICE_DECIMALS), round(ask_price, self.config.PRICE_DECIMALS)

    def generate_orders(self, orderbook: Dict, position: Optional[Position], account_value: float,
                       signals: Optional[MarketSignals] = None) -> List[Dict]:
        """Generate orders using enhanced orderbook analysis"""
        orders = []

        if not self.should_place_orders(position, orderbook, signals):
            return orders

        fair_price = self.calculate_fair_price(orderbook)
        if not fair_price:
            return orders

        bid_price, ask_price = self.calculate_order_prices(fair_price, orderbook, position, signals)

        # Simple size calculation
        if self.config.USE_PERCENTAGE_SIZING:
            dollar_amount = account_value * self.config.ORDER_SIZE_PCT / 100
            size = dollar_amount / fair_price
        else:
            size = getattr(self.config, 'ORDER_SIZE', 1.0)

        size = max(size, self.config.MIN_ORDER_SIZE)
        size = round(size, self.config.SIZE_DECIMALS)

        if size >= self.config.MIN_ORDER_SIZE:
            orders.append({
                'coin': self.config.SYMBOL,
                'is_buy': True,
                'sz': size,
                'limit_px': bid_price,
                'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                'reduce_only': False
            })
            orders.append({
                'coin': self.config.SYMBOL,
                'is_buy': False,
                'sz': size,
                'limit_px': ask_price,
                'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                'reduce_only': False
            })

        return orders

@dataclass
class RiskManagementConfig:
    # Stop-loss settings
    ENABLE_STOP_LOSS: bool = True
    STOP_LOSS_PCT: float = 2.0  # 2% stop loss
    TRAILING_STOP_LOSS: bool = True
    TRAILING_STOP_DISTANCE: float = 1.0  # 1% trailing distance
    
    # Profit-taking settings
    ENABLE_PROFIT_TAKING: bool = True
    PROFIT_TARGET_PCT: float = 1.5  # 1.5% profit target
    PARTIAL_PROFIT_LEVELS: List[float] = None  # [0.5, 1.0, 1.5] # Take profits at these %
    
    # Position skewing for profit
    ENABLE_PROFIT_SKEW: bool = True
    MAX_PROFIT_SKEW: float = 0.5  # Max 0.5% additional skew for profitable positions
    SKEW_SCALING_FACTOR: float = 0.3  # How aggressively to skew
    
    def __post_init__(self):
        if self.PARTIAL_PROFIT_LEVELS is None:
            self.PARTIAL_PROFIT_LEVELS = [0.5, 1.0, 1.5]

class EnhancedMarketMakingStrategyWithRisk(EnhancedMarketMakingStrategy):
    def __init__(self, config: TradingConfig):
        super().__init__(config)
        
        # ADD THESE LINES for risk management:
        self.position_entry_price = None
        self.position_entry_time = None
        self.highest_profit_price = None
        self.lowest_loss_price = None
        self.stop_loss_price = None
        self.profit_target_price = None
        self.profit_levels_hit = set()
        
        # Simple risk config
        class SimpleRiskConfig:
            ENABLE_STOP_LOSS = True
            STOP_LOSS_PCT = 2.0
            TRAILING_STOP_LOSS = True
            TRAILING_STOP_DISTANCE = 1.0
            ENABLE_PROFIT_TAKING = True
            PROFIT_TARGET_PCT = 1.5
            PARTIAL_PROFIT_LEVELS = [0.5, 1.0, 1.5]
            ENABLE_PROFIT_SKEW = True
            MAX_PROFIT_SKEW = 0.5
            SKEW_SCALING_FACTOR = 0.3
        
        self.risk_config = SimpleRiskConfig()
        
        print(f"🛡️  Risk Management enabled:")
        print(f"   - Stop-loss: {self.risk_config.STOP_LOSS_PCT}%")
        print(f"   - Profit target: {self.risk_config.PROFIT_TARGET_PCT}%")
    
    def update_position_tracking(self, position, current_price: float):
        """Update position tracking"""
        if not position or position.size == 0:
            self.position_entry_price = None
            self.stop_loss_price = None
            self.profit_target_price = None
            if hasattr(self, 'profit_levels_hit'):
                self.profit_levels_hit.clear()
            return
        
        if self.position_entry_price is None:
            self.position_entry_price = getattr(position, 'entry_price', current_price)
            
            if position.size > 0:  # Long
                self.stop_loss_price = self.position_entry_price * (1 - self.risk_config.STOP_LOSS_PCT / 100)
                self.profit_target_price = self.position_entry_price * (1 + self.risk_config.PROFIT_TARGET_PCT / 100)
            else:  # Short
                self.stop_loss_price = self.position_entry_price * (1 + self.risk_config.STOP_LOSS_PCT / 100)
                self.profit_target_price = self.position_entry_price * (1 - self.risk_config.PROFIT_TARGET_PCT / 100)

    
    def _update_trailing_stops(self, position: Position, current_price: float):
        """Update trailing stop-loss levels"""
        if position.size > 0:  # Long position
            # Track highest price for trailing stop
            if self.highest_profit_price is None or current_price > self.highest_profit_price:
                self.highest_profit_price = current_price
                
                # Update trailing stop-loss
                new_stop = self.highest_profit_price * (1 - self.risk_config.TRAILING_STOP_DISTANCE / 100)
                if new_stop > self.stop_loss_price:
                    self.stop_loss_price = new_stop
                    print(f"📈 Trailing stop updated: ${self.stop_loss_price:.5f}")
        
        else:  # Short position
            # Track lowest price for trailing stop
            if self.lowest_loss_price is None or current_price < self.lowest_loss_price:
                self.lowest_loss_price = current_price
                
                # Update trailing stop-loss
                new_stop = self.lowest_loss_price * (1 + self.risk_config.TRAILING_STOP_DISTANCE / 100)
                if new_stop < self.stop_loss_price:
                    self.stop_loss_price = new_stop
                    print(f"📉 Trailing stop updated: ${self.stop_loss_price:.5f}")
    
    def check_stop_loss_trigger(self, position, current_price: float) -> bool:
        """Check if stop-loss should be triggered"""
        if (not position or not hasattr(self, 'stop_loss_price') or 
            not self.stop_loss_price or not self.risk_config.ENABLE_STOP_LOSS):
            return False
        
        if position.size > 0:  # Long position
            return current_price <= self.stop_loss_price
        else:  # Short position
            return current_price >= self.stop_loss_price
    
    def check_profit_taking_trigger(self, position, current_price: float):
        """Check profit taking trigger"""
        if (not position or not hasattr(self, 'position_entry_price') or 
            not self.position_entry_price or not self.risk_config.ENABLE_PROFIT_TAKING):
            return None
        
        profit_pct = abs(current_price - self.position_entry_price) / self.position_entry_price * 100
        
        # Check profit levels
        if hasattr(self, 'profit_levels_hit'):
            for level in self.risk_config.PARTIAL_PROFIT_LEVELS:
                if level not in self.profit_levels_hit and profit_pct >= level:
                    self.profit_levels_hit.add(level)
                    return abs(position.size) * 0.25  # 25% profit taking
        
        if profit_pct >= self.risk_config.PROFIT_TARGET_PCT:
            return abs(position.size)  # Full close
        
        return None
    
    def calculate_profit_skew(self, position: Optional[Position], current_price: float) -> float:
        """Calculate exponential inventory skew that gets aggressive as position approaches limits

        This replaces the old profit-based skew with position-based inventory management.
        Returns skew as a decimal (e.g., 0.02 = 2% of spread)

        The skew pushes prices AWAY from adding to position when near limits:
        - Long position: increases ask price, decreases bid price (encourages selling)
        - Short position: decreases ask price, increases bid price (encourages buying back)
        """
        if not position or position.size == 0:
            return 0.0

        # Calculate inventory ratio (-1.0 to +1.0)
        max_position = self.config.MAX_POSITION_PCT
        inventory_ratio = position.size / max_position

        # Clamp to [-1, 1] for safety
        inventory_ratio = max(-1.0, min(1.0, inventory_ratio))

        # Apply EXPONENTIAL scaling: skew = sign(ratio) * (abs(ratio) ** 2)
        # This makes the skew grow exponentially as position size increases
        # Examples:
        #   50% of max (0.5 ratio) -> 0.25 squared effect (moderate)
        #   80% of max (0.8 ratio) -> 0.64 squared effect (aggressive)
        #   90% of max (0.9 ratio) -> 0.81 squared effect (very aggressive)
        sign = 1.0 if inventory_ratio > 0 else -1.0
        exponential_skew = sign * (abs(inventory_ratio) ** 2)

        # Maximum skew as percentage (2-3% of spread)
        MAX_SKEW_PCT = 0.025  # 2.5% maximum skew

        # Scale the exponential skew to our maximum
        skew = exponential_skew * MAX_SKEW_PCT

        # Positive skew = long position = push prices to encourage selling
        # Negative skew = short position = push prices to encourage buying
        return skew
    
    def generate_stop_loss_order(self, position, current_price: float):
        """Generate stop-loss order with valid price formatting"""
        if not self.check_stop_loss_trigger(position, current_price):
            return None
        
        print(f"🛑 DEBUG: Stop-loss price calculation:")
        print(f"   Current price: ${current_price:.5f}")
        print(f"   Position size: {position.size}")
        
        # Get orderbook to check valid price ranges
        # For now, use a more conservative price adjustment
        if position.size > 0:  # Long position - sell to close
            # For LINK, use a reasonable tick size (usually $0.001 or $0.0001)
            # Make the stop-loss more conservative - 1% below current price
            stop_price = current_price * 0.99  # 1% below instead of 0.1%
            print(f"   Long position: selling at ${stop_price:.5f} (1% below)")
        else:  # Short position - buy to close
            stop_price = current_price * 1.01  # 1% above instead of 0.1%
            print(f"   Short position: buying at ${stop_price:.5f} (1% above)")
        
        # Round to appropriate tick size for LINK
        # LINK typically uses $0.001 tick size
        tick_size = 0.001
        stop_price = round(stop_price / tick_size) * tick_size
        
        print(f"   Rounded to tick size: ${stop_price:.3f}")
        
        # Ensure size is properly formatted
        size = abs(position.size)
        size = round(size, self.config.SIZE_DECIMALS)
        
        print(f"   Order size: {size:.{self.config.SIZE_DECIMALS}f}")
        
        order = {
            'coin': str(self.config.SYMBOL),
            'is_buy': bool(position.size < 0),
            'sz': float(size),
            'limit_px': float(stop_price),
            'order_type': {'limit': {'tif': 'Gtc'}}
            # Remove reduce_only for now to test
        }
        
        print(f"🛑 Generated FIXED stop-loss order:")
        print(f"   {'BUY' if order['is_buy'] else 'SELL'} {order['sz']:.{self.config.SIZE_DECIMALS}f} {order['coin']} @ ${order['limit_px']:.3f}")
        
        return order

        

    def generate_profit_taking_order(self, position, current_price: float):
        """Generate profit taking order"""
        close_size = self.check_profit_taking_trigger(position, current_price)
        if not close_size:
            return None
        
        if position.size > 0:  # Long - sell higher
            price = current_price * 1.0005
        else:  # Short - buy lower
            price = current_price * 0.9995
        
        return {
            'coin': self.config.SYMBOL,
            'is_buy': position.size < 0,
            'sz': close_size,
            'limit_px': price,
            'order_type': {'limit': {'tif': 'Gtc'}},
            'reduce_only': True
        }
    
    def calculate_order_prices(self, fair_price: float, orderbook: Dict, position: Optional[Position],
                              signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Enhanced order prices with exponential inventory skewing"""

        # Update position tracking
        self.update_position_tracking(position, fair_price)

        # Get base prices from parent class
        bid_price, ask_price = super().calculate_order_prices(fair_price, orderbook, position, signals)

        # Calculate base spread before skewing
        base_spread = ask_price - bid_price

        # Apply exponential inventory skew
        inventory_skew = self.calculate_profit_skew(position, fair_price)

        if inventory_skew != 0 and position:
            # Calculate inventory ratio for logging
            max_position = self.config.MAX_POSITION_PCT
            inventory_ratio = position.size / max_position
            inventory_pct = inventory_ratio * 100

            # Apply skew: shift BOTH prices in the direction that discourages adding to position
            # Positive skew (long position): shift both prices UP to discourage buying, encourage selling
            # Negative skew (short position): shift both prices DOWN to discourage selling, encourage buying
            skew_adjustment = base_spread * inventory_skew

            # Shift both bid and ask by the skew amount
            bid_price += skew_adjustment
            ask_price += skew_adjustment

            # Calculate effective skew as percentage of spread
            skew_pct = abs(inventory_skew) * 100

            # Log inventory management details
            position_type = "LONG" if position.size > 0 else "SHORT"
            print(f"📊 Inventory Skew Applied [{position_type}]:")
            print(f"   Position: {position.size:.4f} / {max_position:.4f} ({inventory_pct:.1f}%)")
            print(f"   Inventory Ratio: {inventory_ratio:.3f}")
            print(f"   Exponential Skew: {skew_pct:.2f}% of spread")
            print(f"   Skew Adjustment: ${skew_adjustment:.5f}")
            print(f"   Direction: {'↑ Shift UP (discourage buys)' if inventory_skew > 0 else '↓ Shift DOWN (discourage sells)'}")
            print(f"   Final: bid=${bid_price:.5f}, ask=${ask_price:.5f}")

        return bid_price, ask_price
    
    def generate_enhanced_orders_with_risk(self, orderbook, position, account_value, signals=None):
        """Generate orders with risk management"""
        # Update position tracking first
        current_price = orderbook.get('mid_price', 0)
        self.update_position_tracking(position, current_price)
        
        # Check for stop loss
        if position and self.check_stop_loss_trigger(position, current_price):
            stop_order = self.generate_stop_loss_order(position, current_price)
            if stop_order:
                return [stop_order]
        
        # Check for profit taking
        orders = []
        if position and self.check_profit_taking_trigger(position, current_price):
            profit_order = self.generate_profit_taking_order(position, current_price)
            if profit_order:
                orders.append(profit_order)
        
        # Add normal orders
        normal_orders = self.generate_orders(orderbook, position, account_value, signals)
        orders.extend(normal_orders)
        
        return orders
    
    def get_risk_status(self, position, current_price: float):
        """Get risk status"""
        if not position or position.size == 0:
            return {'status': 'FLAT', 'no_position': True}
        
        return {
            'position_size': position.size,
            'entry_price': getattr(self, 'position_entry_price', 0) or 0,
            'current_price': current_price,
            'unrealized_pnl': position.calculate_unrealized_pnl(current_price),
            'stop_loss_price': getattr(self, 'stop_loss_price', 0) or 0,
            'profit_target_price': getattr(self, 'profit_target_price', 0) or 0,
            'stop_loss_distance': 0.0,
            'profit_target_distance': 0.0,
            'profit_levels_hit': list(getattr(self, 'profit_levels_hit', set()))
        }
    
