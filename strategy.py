
import logging
from typing import Dict, List, Tuple, Optional
from config import TradingConfig
from position_tracker import Position, Order

class MarketMakingStrategy:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_fair_price(self, orderbook: Dict) -> Optional[float]:
        """Calculate fair price from orderbook"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return None
            
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        # Simple mid-price calculation
        fair_price = round(((best_bid + best_ask) / 2), 5)
        return fair_price
    
    def should_place_orders(self, position: Optional[Position], orderbook: Dict) -> bool:
        """Determine if we should place new orders"""
        if not orderbook.get('bids') or not orderbook.get('asks'):
            return False
            
        # Check spread is reasonable
        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        spread = (best_ask - best_bid) / best_bid
        
        if spread > self.config.BASE_SPREAD * 5:  # Don't trade in very wide markets
            self.logger.warning(f"Spread too wide: {spread:.4f}")
            return False
            
        # Don't trade if position is too large
        if position and abs(position.size) >= self.config.MAX_POSITION_PCT:
            self.logger.warning(f"Position too large: {position.size}")
            return False
            
        return True
    
    def calculate_order_prices(self, fair_price: float, position: Optional[Position]) -> Tuple[float, float]:
        """Calculate bid and ask prices for orders"""
        base_spread = self.config.BASE_SPREAD
        
        # Adjust spread based on position (inventory risk)
        position_skew = 0.0
        if position and position.size != 0:
            # Skew prices away from our position to encourage rebalancing
            position_ratio = position.size / self.config.MAX_POSITION_PCT
            position_skew = position_ratio * base_spread * 0.5
        
        # Calculate bid and ask prices
        bid_price = round(fair_price * (1 - base_spread / 2 - position_skew), 5)
        ask_price = round(fair_price * (1 + base_spread / 2 - position_skew), 5)
        
        return bid_price, ask_price
    
    def calculate_order_sizes(self, position: Optional[Position], current_price: float, account_value: float) -> Tuple[float, float]:
        """Calculate order sizes for bid and ask (supports both fixed and percentage sizing)"""
        
        # Determine base size and max position based on configuration
        if self.config.USE_PERCENTAGE_SIZING:
            if account_value <= self.config.MIN_ACCOUNT_VALUE:
                self.logger.warning(f"Account value too low: ${account_value:.2f}")
                return 0.0, 0.0
            
            # Calculate sizes based on percentage of account value
            dollar_amount = account_value * self.config.ORDER_SIZE_PCT
            base_size = dollar_amount / current_price
            
            max_position_dollar = account_value * self.config.MAX_POSITION_PCT
            max_position = max_position_dollar / current_price
            
            self.logger.debug(f"Percentage sizing: {self.config.ORDER_SIZE_PCT*100:.1f}% = ${dollar_amount:.2f} = {base_size:.4f} {self.config.SYMBOL}")
        else:
            # Use fixed sizing
            base_size = self.config.ORDER_SIZE
            max_position = self.config.MAX_POSITION_PCT
        
        # Apply minimum size constraint
        base_size = max(base_size, self.config.MIN_ORDER_SIZE)
        
        # Reduce size if we're approaching position limits
        current_position = position.size if position else 0.0
        
        # Calculate how much we can buy/sell without exceeding limits
        max_buy = max_position - current_position
        max_sell = current_position + max_position

        bid_size = round(min(base_size, max_buy) if max_buy > self.config.MIN_ORDER_SIZE else 0, 2)
        ask_size = round(min(base_size, max_sell) if max_sell > self.config.MIN_ORDER_SIZE else 0, 2)

        print(bid_size, ask_size)

        return bid_size, ask_size
    
    def generate_orders(self, orderbook: Dict, position: Optional[Position], account_value: float) -> List[Dict]:
        """Generate Hyperliquid-compatible order specifications"""
        orders = []
        
        if not self.should_place_orders(position, orderbook):
            return orders
            
        fair_price = self.calculate_fair_price(orderbook)
        if not fair_price:
            return orders
            
        bid_price, ask_price = self.calculate_order_prices(fair_price, position)
        bid_size, ask_size = self.calculate_order_sizes(position, fair_price, account_value)
        
        # Create bid order (Hyperliquid format)
        if bid_size > 0:
            orders.append({
                'coin': self.config.SYMBOL,
                'is_buy': True,
                'sz': bid_size,
                'limit_px': bid_price,
                'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                'reduce_only': False
            })
        
        # Create ask order (Hyperliquid format)
        if ask_size > 0:
            orders.append({
                'coin': self.config.SYMBOL,
                'is_buy': False,
                'sz': ask_size,
                'limit_px': ask_price,
                'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                'reduce_only': False
            })
        
        return orders
    
    def should_cancel_orders(self, orders: List[Order], fair_price: float) -> List[str]:
        """Determine which orders should be cancelled"""
        to_cancel = []
        
        for order in orders:
            # Cancel if price has moved too far from fair price
            if order.side == 'buy' and order.price < fair_price * (1 - self.config.REBALANCE_THRESHOLD):
                to_cancel.append(order.order_id)
            elif order.side == 'sell' and order.price > fair_price * (1 + self.config.REBALANCE_THRESHOLD):
                to_cancel.append(order.order_id)
                
        return to_cancel