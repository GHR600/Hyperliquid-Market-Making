from typing import Dict, List, Optional
import logging
from datetime import datetime
from config import TradingConfig

class Position:
    def __init__(self, symbol: str, size: float = 0.0, entry_price: float = 0.0):
        self.symbol = symbol
        self.size = size  # Positive for long, negative for short
        self.entry_price = entry_price
        self.unrealized_pnl = 0.0
        self.last_updated = datetime.now()
    
    def update(self, size: float, entry_price: float):
        self.size = size
        self.entry_price = entry_price
        self.last_updated = datetime.now()
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        if self.size == 0:
            return 0.0
        
        self.unrealized_pnl = (current_price - self.entry_price) * self.size
        return self.unrealized_pnl

import time
from datetime import datetime

class Order:
    def __init__(self, order_data: Dict):
        self.order_id = order_data.get('oid', '')
        self.symbol = order_data.get('coin', '')
        self.side = 'buy' if order_data.get('side') == 'B' else 'sell'
        self.size = float(order_data.get('sz', 0))
        self.price = float(order_data.get('limitPx', 0))
        self.timestamp = order_data.get('timestamp', 0)
        self.status = 'open'
        
        # Store creation time as float timestamp for easy comparison
        self.created_at = time.time()  # Always store as float
        
        # Keep datetime for compatibility if needed
        self.created_datetime = datetime.now()
    
    def get_age_seconds(self) -> float:
        """Get order age in seconds"""
        return time.time() - self.created_at
    
    def is_old(self, max_age_seconds: float) -> bool:
        """Check if order is older than max_age_seconds"""
        return self.get_age_seconds() > max_age_seconds

class PositionTracker:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, Order] = {}
        self.account_value: float = 0.0  # Track total account value
        self.logger = logging.getLogger(__name__)

    def get_account_value_fast(self) -> float:
        """Get account value with caching for performance"""
        current_time = time.time()
        
        # Return cached value if recent
        if (current_time - self._cached_account_timestamp) < self._cache_duration:
            return self._cached_account_value
        
        # Update cache
        self._cached_account_value = self.account_value
        self._cached_account_timestamp = current_time
        return self._cached_account_value
    
    def get_open_orders_fast(self, symbol: str = None) -> List[Order]:
        """Fast order lookup without API calls"""
        if symbol:
            return [order for order in self.open_orders.values() if order.symbol == symbol]
        return list(self.open_orders.values())
    
    def remove_orders_fast(self, order_ids: List[str]):
        """Fast order removal from tracking"""
        for order_id in order_ids:
            if order_id in self.open_orders:
                del self.open_orders[order_id]

    def update_from_account_state(self, account_state: Dict):
        """Update positions from Hyperliquid account state"""
        try:
            if not account_state:
                return
            
            # Calculate total account value
            self._calculate_account_value(account_state)
                
            # Update positions
            asset_positions = account_state.get('assetPositions', [])
            for pos_data in asset_positions:
                position_info = pos_data.get('position', {})
                coin = position_info.get('coin', '')
                
                if coin:
                    size = float(position_info.get('szi', 0))
                    entry_px = float(position_info.get('entryPx', 0)) if position_info.get('entryPx') else 0.0
                    
                    if coin not in self.positions:
                        self.positions[coin] = Position(coin)
                    
                    self.positions[coin].update(size, entry_px)
                    self.logger.debug(f"Updated position {coin}: size={size}, entry_px={entry_px}")
            
        except Exception as e:
            self.logger.error(f"Error updating positions from account state: {e}")
    
    def _calculate_account_value(self, account_state: Dict):
        """Calculate total account value in USD"""
        try:
            # Get margin summary for total account value
            margin_summary = account_state.get('marginSummary', {})
            account_value = float(margin_summary.get('accountValue', 0))
            
            # Alternative: sum up all balances if accountValue not available
            if account_value == 0:
                cross_margin_summary = account_state.get('crossMarginSummary', {})
                account_value = float(cross_margin_summary.get('accountValue', 0))
            
            # Fallback: calculate from cash and positions
            if account_value == 0:
                cash = 0
                # Try to get USD cash balance
                for balance in account_state.get('assetPositions', []):
                    if balance.get('position', {}).get('coin') == 'USDC':
                        cash = float(balance.get('position', {}).get('szi', 0))
                        break
                
                # Add unrealized PnL from positions
                total_unrealized = 0
                for pos_data in account_state.get('assetPositions', []):
                    unrealized = float(pos_data.get('position', {}).get('unrealizedPnl', 0))
                    total_unrealized += unrealized
                
                account_value = cash + total_unrealized
            
            self.account_value = max(account_value, 0)
            self.logger.debug(f"Updated account value: ${self.account_value:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error calculating account value: {e}")
            self.account_value = 0
    
    def get_account_value(self) -> float:
        """Get current account value"""
        return self.account_value
    
    def calculate_order_size_from_percentage(self, percentage: float, current_price: float) -> float:
        """Calculate order size based on percentage of account value"""
        if self.account_value <= 0 or current_price <= 0:
            return 0.0
        
        # Calculate size in base currency
        dollar_amount = self.account_value * percentage
        size = dollar_amount / current_price
        
        # Apply minimum size constraint
        size = max(size, self.config.MIN_ORDER_SIZE)
        
        return size
    
    def calculate_max_position_from_percentage(self, percentage: float, current_price: float) -> float:
        """Calculate max position based on percentage of account value"""
        if self.account_value <= 0 or current_price <= 0:
            return 0.0
        
        dollar_amount = self.account_value * percentage
        max_position = dollar_amount / current_price
        
        return max_position
    
    def update_from_open_orders(self, open_orders: List[Dict]):
        """Update order tracking from open orders"""
        try:
            # Clear existing orders and rebuild from current state
            self.open_orders.clear()
            
            for order_data in open_orders:
                order = Order(order_data)
                self.open_orders[order.order_id] = order
                self.logger.debug(f"Tracking order {order.order_id}: {order.side} {order.size} @ {order.price}")
                
        except Exception as e:
            self.logger.error(f"Error updating orders: {e}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol"""
        return self.positions.get(symbol)
    
    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders, optionally filtered by symbol"""
        if symbol:
            return [order for order in self.open_orders.values() if order.symbol == symbol]
        return list(self.open_orders.values())
    
    def calculate_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total unrealized PnL across all positions"""
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_pnl += position.calculate_unrealized_pnl(current_prices[symbol])
        return total_pnl