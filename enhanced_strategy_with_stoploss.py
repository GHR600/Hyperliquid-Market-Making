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
from position_tracker import Position, Order
from market_microstructure import MarketSignals
from orderbook_analyzer import OrderbookAnalyzer, OrderbookImbalance, OrderbookGaps, LiquidityProfile, MarketCondition, AdverseSelectionRisk

from enhanced_strategy import EnhancedMarketMakingStrategy

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
        """Calculate additional spread skew based on profit"""
        if (not self.risk_config.ENABLE_PROFIT_SKEW or 
            not position or 
            not self.position_entry_price or 
            position.size == 0):
            return 0.0
        
        # Calculate current profit/loss percentage
        if position.size > 0:  # Long position
            profit_pct = (current_price - self.position_entry_price) / self.position_entry_price
        else:  # Short position
            profit_pct = (self.position_entry_price - current_price) / self.position_entry_price
        
        # Only apply skew if profitable
        if profit_pct <= 0:
            return 0.0
        
        # Calculate skew (positive = skew towards selling profitable position)
        max_skew = self.risk_config.MAX_PROFIT_SKEW / 100  # Convert to decimal
        scaling = self.risk_config.SKEW_SCALING_FACTOR
        
        # Scale profit to skew amount
        skew = min(profit_pct * scaling, max_skew)
        
        # Apply skew direction based on position
        if position.size > 0:  # Long position - skew towards selling
            return skew
        else:  # Short position - skew towards buying back
            return -skew
    
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
        """Enhanced order prices with profit skewing"""
        
        # Update position tracking
        self.update_position_tracking(position, fair_price)
        
        # Get base prices from parent class
        bid_price, ask_price = super().calculate_order_prices(fair_price, orderbook, position, signals)
        
        # Apply profit skew
        profit_skew = self.calculate_profit_skew(position, fair_price)
        
        if profit_skew != 0:
            # Positive skew = encourage selling (widen bid, tighten ask)
            # Negative skew = encourage buying (tighten bid, widen ask)
            spread = ask_price - bid_price
            skew_adjustment = spread * profit_skew
            
            bid_price -= skew_adjustment
            ask_price -= skew_adjustment
            
            print(f"💰 Applied profit skew: {profit_skew*100:.3f}% (${skew_adjustment:.5f})")
            print(f"   Adjusted prices: bid=${bid_price:.5f}, ask=${ask_price:.5f}")
        
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
    
