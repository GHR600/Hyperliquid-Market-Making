import logging
from typing import Dict, List, Tuple, Optional
from config import TradingConfig
from position_tracker import Position, Order
from market_microstructure import MarketSignals

class MarketMakingStrategy:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        print(f"🎯 Initialized MarketMakingStrategy")
        print(f"   - Base spread: {config.BASE_SPREAD * 100:.2f}%")
        print(f"   - Order size: {'percentage-based' if config.USE_PERCENTAGE_SIZING else 'fixed'}")
        print(f"   - Max orders per side: {config.MAX_ORDERS_PER_SIDE}")
        
    def calculate_fair_price(self, orderbook: Dict) -> Optional[float]:
        """Calculate fair price from orderbook"""
        print("💰 Calculating fair price...")
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            print("⚠️  Cannot calculate fair price - missing bids or asks")
            return None
            
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        # Simple mid-price calculation
        fair_price = round(((best_bid + best_ask) / 2), 5)
        
        print(f"   📊 Fair price: ${fair_price:.5f} (bid: ${best_bid:.5f}, ask: ${best_ask:.5f})")
        return fair_price
    
    def should_place_orders(self, position: Optional[Position], orderbook: Dict, signals: Optional[MarketSignals] = None) -> bool:
        """Determine if we should place new orders"""
        print("🤔 Evaluating whether to place orders...")
        
        if not orderbook.get('bids') or not orderbook.get('asks'):
            print("❌ No orderbook data - skipping order placement")
            return False
            
        # Check spread is reasonable
        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        spread = (best_ask - best_bid) / best_bid
        
        if spread > self.config.BASE_SPREAD * 15:  # Don't trade in very wide markets
            print(f"❌ Spread too wide: {spread:.4f} (>{self.config.BASE_SPREAD * 15:.4f}) - skipping")
            self.logger.warning(f"Spread too wide: {spread:.4f}")
            return False
            
        # Don't trade if position is too large
        if position and abs(position.size) >= self.config.MAX_POSITION_PCT:
            print(f"❌ Position too large: {position.size} (max: {self.config.MAX_POSITION_PCT}) - skipping")
            self.logger.warning(f"Position too large: {position.size}")
            return False
        
        # Check microstructure signals for adverse conditions
        if signals and signals.adverse_selection_risk > self.config.ADVERSE_SELECTION_THRESHOLD:
            print(f"❌ High adverse selection risk: {signals.adverse_selection_risk:.3f} - skipping")
            return False
            
        print("✅ Conditions favorable for order placement")
        return True
    
    def calculate_order_prices(self, fair_price: float, position: Optional[Position], signals: Optional[MarketSignals] = None, tick_size: float = 0.5) -> Tuple[float, float]:
        """Calculate bid and ask prices for orders with microstructure adjustments"""
        print("📈 Calculating order prices...")
        
        base_spread = self.config.BASE_SPREAD
        print(f"   Base spread: {base_spread * 100:.3f}%")
        
        # Adjust spread based on microstructure signals
        spread_multiplier = 1.0
        
        if signals:
            # Widen spreads during high volatility or uncertain conditions
            if signals.spread_volatility > 0.1:  # High spread volatility
                spread_multiplier *= 1.2
                print(f"   📊 High spread volatility detected - widening spreads by 20%")
            
            # Adjust based on flow confidence
            if signals.flow_confidence < 0.3:  # Low confidence
                spread_multiplier *= 1.3
                print(f"   🤷 Low flow confidence - widening spreads by 30%")
            elif signals.flow_confidence > 0.8:  # High confidence
                spread_multiplier *= 0.9
                print(f"   💪 High flow confidence - tightening spreads by 10%")
            
            # Adjust for order flow imbalance
            if abs(signals.volume_imbalance) > 0.5:
                if signals.volume_imbalance > 0:  # More bid volume
                    print(f"   📊 Strong bid pressure detected - adjusting ask spread")
                else:  # More ask volume
                    print(f"   📊 Strong ask pressure detected - adjusting bid spread")
        
        adjusted_spread = base_spread * spread_multiplier
        print(f"   Adjusted spread: {adjusted_spread * 100:.3f}% (multiplier: {spread_multiplier:.2f})")
        
        # Adjust spread based on position (inventory risk)
        position_skew = 0.0
        if position and position.size != 0:
            # Skew prices away from our position to encourage rebalancing
            position_ratio = position.size / self.config.MAX_POSITION_PCT
            position_skew = position_ratio * adjusted_spread * 0.5
            print(f"   🎯 Position skew: {position_skew * 100:.3f}% (position: {position.size:.4f})")
        
        # Apply flow-based skewing
        flow_skew = 0.0
        if signals and hasattr(self.config, 'FLOW_CONFIDENCE_THRESHOLD') and signals.flow_confidence > self.config.FLOW_CONFIDENCE_THRESHOLD:
            flow_direction = signals.overall_momentum
            if hasattr(self.config, 'SPREAD_ADJUSTMENT_MULTIPLIER'):
                flow_skew = flow_direction * adjusted_spread * self.config.SPREAD_ADJUSTMENT_MULTIPLIER
    
        total_skew = position_skew + flow_skew
        
        # Calculate bid and ask prices
        raw_bid_price = fair_price * (1 - adjusted_spread / 2 - total_skew)
        raw_ask_price = fair_price * (1 + adjusted_spread / 2 - total_skew)
        
        # Round to appropriate decimals
        bid_price = self._round_price_to_decimals(raw_bid_price, tick_size)
        ask_price = self._round_price_to_decimals(raw_ask_price, tick_size)
            
        print(f"   💵 Final prices: bid=${bid_price:.5f}, ask=${ask_price:.5f}")
        print(f"   📏 Effective spread: {((ask_price - bid_price) / fair_price * 100):.3f}%")

        return bid_price, ask_price
 
        
    def _round_size_to_decimals(self, size: float) -> float:
        """Round size down to the appropriate number of decimals for the symbol"""
        if size <= 0:
            return 0.0
        
        # Round down using floor division approach
        rounded_size = round(size, self.config.SIZE_DECIMALS)
        
        print(f"      📏 Size rounding: {size:.6f} -> {rounded_size:.{self.config.SIZE_DECIMALS}f} ({self.config.SIZE_DECIMALS} decimals)")
        return rounded_size
    
    def _round_price_to_decimals(self, price: float, tick_size: float = 0.5) -> float:
        """Round price to valid tick increments for the symbol"""
        if price <= 0:
            return 0.0

        # Round to nearest tick
        rounded_price = round(price / tick_size) * tick_size
        
        # Ensure we don't exceed the decimal precision rules
        max_decimals = self.config.PRICE_DECIMALS
        final_price = round(rounded_price, max_decimals)
        
        print(f"      💰 Price rounding: {price:.5f} -> tick_rounded: {rounded_price:.5f} -> final: {final_price:.{max_decimals}f}")
        return final_price
    
    def calculate_order_sizes(self, position: Optional[Position], current_price: float, account_value: float, signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Calculate order sizes with microstructure-based adjustments"""
        print("📊 Calculating order sizes...")
        
        try:
            # Determine base size and max position based on configuration
            if self.config.USE_PERCENTAGE_SIZING:
                if account_value <= self.config.MIN_ACCOUNT_VALUE:
                    print(f"❌ Account value too low: ${account_value:.2f} (min: ${self.config.MIN_ACCOUNT_VALUE})")
                    self.logger.warning(f"Account value too low: ${account_value:.2f}")
                    return 0.0, 0.0
                
                # Calculate sizes based on percentage of account value
                dollar_amount = account_value * self.config.ORDER_SIZE_PCT / 100
                base_size = dollar_amount / current_price
                
                max_position_dollar = account_value * self.config.MAX_POSITION_PCT / 100
                max_position = max_position_dollar / current_price
                
                print(f"   💰 Percentage sizing: {self.config.ORDER_SIZE_PCT}% = ${dollar_amount:.2f} = {base_size:.4f} {self.config.SYMBOL}")
            else:
                # Use fixed sizing
                base_size = getattr(self.config, 'ORDER_SIZE', 1.0)  # Fallback if not defined
                max_position = self.config.MAX_POSITION_PCT
                print(f"   📏 Fixed sizing: {base_size:.4f} {self.config.SYMBOL}")
            
            # Apply microstructure-based size adjustments
            size_multiplier = 1.0
            
            if signals:
                # Increase size when flow is strongly in our favor
                if hasattr(self.config, 'FLOW_CONFIDENCE_THRESHOLD') and signals.flow_confidence > self.config.FLOW_CONFIDENCE_THRESHOLD:
                    current_position = position.size if position else 0.0
                    
                    # If flow aligns with reducing our position, increase size
                    if (current_position > 0 and signals.overall_momentum < -0.5) or \
                       (current_position < 0 and signals.overall_momentum > 0.5):
                        if hasattr(self.config, 'FLOW_POSITION_MULTIPLIER'):
                            size_multiplier = self.config.FLOW_POSITION_MULTIPLIER
                            print(f"   🎯 Flow aligns with position reduction - increasing size by {size_multiplier}x")
                        else:
                            size_multiplier = 2.0  # Default fallback
                            print(f"   🎯 Flow aligns with position reduction - using default 2x multiplier")
                    
                    # If flow supports our market making direction, moderate increase
                    elif abs(signals.overall_momentum) < 0.3:  # Sideways/ranging market
                        size_multiplier = 1.2
                        print(f"   📈 Favorable ranging conditions - increasing size by 20%")
                
                # Reduce size in adverse conditions
                if signals.adverse_selection_risk > 0.6:
                    if hasattr(self.config, 'ADVERSE_FLOW_REDUCTION'):
                        reduction_factor = self.config.ADVERSE_FLOW_REDUCTION
                    else:
                        reduction_factor = 0.5  # Default fallback
                    size_multiplier *= reduction_factor
                    print(f"   ⚠️  High adverse selection risk - reducing size by {(1-reduction_factor)*100:.0f}%")
                
                # Adjust based on trade velocity (high velocity = more risk)
                if signals.trade_velocity > 2.0:  # More than 2 trades/second
                    size_multiplier *= 0.8
                    print(f"   ⚡ High trade velocity - reducing size by 20%")
            
            adjusted_base_size = base_size * size_multiplier
            print(f"   📊 Adjusted base size: {adjusted_base_size:.4f} (multiplier: {size_multiplier:.2f})")
            
            # Apply minimum size constraint
            adjusted_base_size = max(adjusted_base_size, self.config.MIN_ORDER_SIZE)
            
            # Reduce size if we're approaching position limits
            current_position = position.size if position else 0.0
            
            # Calculate how much we can buy/sell without exceeding limits
            max_buy = max_position - current_position
            max_sell = current_position + max_position

            # Apply size rounding BEFORE final size calculation
            raw_bid_size = min(adjusted_base_size, max_buy) if max_buy > self.config.MIN_ORDER_SIZE else 0
            raw_ask_size = min(adjusted_base_size, max_sell) if max_sell > self.config.MIN_ORDER_SIZE else 0
            
            # Round sizes to appropriate decimals
            bid_size = self._round_size_to_decimals(raw_bid_size)
            ask_size = self._round_size_to_decimals(raw_ask_size)
            
            # Final check after rounding - ensure minimum size requirements
            if bid_size < self.config.MIN_ORDER_SIZE:
                bid_size = 0.0
                print(f"      ❌ Bid size too small after rounding: {bid_size}")
            
            if ask_size < self.config.MIN_ORDER_SIZE:
                ask_size = 0.0
                print(f"      ❌ Ask size too small after rounding: {ask_size}")

            print(f"   📋 Final sizes: bid={bid_size:.{self.config.SIZE_DECIMALS}f}, ask={ask_size:.{self.config.SIZE_DECIMALS}f}")
            print(f"   📊 Position limits: current={current_position:.4f}, max_buy={max_buy:.4f}, max_sell={max_sell:.4f}")

            if self.config.USE_PERCENTAGE_SIZING:
                max_position_dollar = account_value * self.config.MAX_POSITION_PCT / 100
                max_position = max_position_dollar / current_price
                
                print(f"   🔍 POSITION DEBUG:")
                print(f"       Account value: ${account_value:.2f}")
                print(f"       MAX_POSITION_PCT: {self.config.MAX_POSITION_PCT}%")
                print(f"       Max position dollar: ${max_position_dollar:.2f}")
                print(f"       Current price: ${current_price:.2f}")
                print(f"       Max position BTC: {max_position:.8f}")

            max_buy = max_position - current_position
            max_sell = current_position + max_position
            
            print(f"   🔍 DEBUG: adjusted_base_size = {adjusted_base_size:.8f}")
            print(f"   🔍 DEBUG: max_buy = {max_buy:.8f}")
            print(f"   🔍 DEBUG: max_sell = {max_sell:.8f}")
            print(f"   🔍 DEBUG: self.config.MIN_ORDER_SIZE = {self.config.MIN_ORDER_SIZE}")

            # Apply size rounding BEFORE final size calculation
            raw_bid_size = min(adjusted_base_size, max_buy) if max_buy > self.config.MIN_ORDER_SIZE else 0
            raw_ask_size = min(adjusted_base_size, max_sell) if max_sell > self.config.MIN_ORDER_SIZE else 0
            
            print(f"   🔍 DEBUG: raw_bid_size = {raw_bid_size:.8f}")
            print(f"   🔍 DEBUG: raw_ask_size = {raw_ask_size:.8f}")
            
            # Round sizes to appropriate decimals
            bid_size = self._round_size_to_decimals(raw_bid_size)
            ask_size = self._round_size_to_decimals(raw_ask_size)
            
            print(f"   🔍 DEBUG: final bid_size = {bid_size:.8f}")
            print(f"   🔍 DEBUG: final ask_size = {ask_size:.8f}")
            
            return bid_size, ask_size
            
        except Exception as e:
            print(f"❌ Error calculating order sizes: {e}")
            import traceback
            traceback.print_exc()
            # Return safe defaults
            return 0.0, 0.0
    
    def generate_orders(self, orderbook: Dict, position: Optional[Position], account_value: float, signals: Optional[MarketSignals] = None) -> List[Dict]:

        """Generate Hyperliquid-compatible order specifications with microstructure integration"""
        print("🎯 Generating orders...")
        orders = []
        
        tick_size = orderbook.get('tick_size', 0.5)  # Add this

        try:
            if not self.should_place_orders(position, orderbook, signals):
                print("❌ Conditions not favorable - no orders generated")
                return orders
                
            fair_price = self.calculate_fair_price(orderbook)
            if not fair_price:
                print("❌ Cannot determine fair price - no orders generated")
                return orders
            
            print("📈 Calculating order parameters...")
            
            # Calculate order prices - this should return a tuple
            price_result = self.calculate_order_prices(fair_price, position, signals, tick_size)
            print(f"   🔍 Price result type: {type(price_result)}, value: {price_result}")
            
            if price_result is None:
                print("❌ Price result is None - no orders generated")
                return orders
            
            if not isinstance(price_result, (tuple, list)) or len(price_result) != 2:
                print(f"❌ Invalid price result format: {price_result} - no orders generated")
                return orders
                
            bid_price, ask_price = price_result
            print(f"   ✅ Prices unpacked: bid=${bid_price:.5f}, ask=${ask_price:.5f}")
            
            # Calculate order sizes - this should return a tuple  
            size_result = self.calculate_order_sizes(position, fair_price, account_value, signals)
            print(f"   🔍 Size result type: {type(size_result)}, value: {size_result}")
            
            if size_result is None:
                print("❌ Size result is None - no orders generated")
                return orders
                
            if not isinstance(size_result, (tuple, list)) or len(size_result) != 2:
                print(f"❌ Invalid size result format: {size_result} - no orders generated")
                return orders
                
            bid_size, ask_size = size_result
            print(f"   ✅ Sizes unpacked: bid={bid_size:.4f}, ask={ask_size:.4f}")
            
            print(f"📊 Order parameters calculated successfully:")
            print(f"   💵 Prices: bid=${bid_price:.5f}, ask=${ask_price:.5f}")
            print(f"   📏 Sizes: bid={bid_size:.{self.config.SIZE_DECIMALS}f}, ask={ask_size:.{self.config.SIZE_DECIMALS}f}")
            
            # Create bid order (Hyperliquid format)
            if bid_size > 0:
                bid_order = {
                    'coin': self.config.SYMBOL,
                    'is_buy': True,
                    'sz': bid_size,
                    'limit_px': bid_price,
                    'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                    'reduce_only': False
                }
                orders.append(bid_order)
                print(f"   ✅ Generated BID order: {bid_size:.{self.config.SIZE_DECIMALS}f} @ ${bid_price:.5f}")
            else:
                print(f"   ❌ Skipping BID order: size too small ({bid_size:.{self.config.SIZE_DECIMALS}f})")
            
            # Create ask order (Hyperliquid format)
            if ask_size > 0:
                ask_order = {
                    'coin': self.config.SYMBOL,
                    'is_buy': False,
                    'sz': ask_size,
                    'limit_px': ask_price,
                    'order_type': {'limit': {'tif': self.config.TIME_IN_FORCE}},
                    'reduce_only': False
                }
                orders.append(ask_order)
                print(f"   ✅ Generated ASK order: {ask_size:.{self.config.SIZE_DECIMALS}f} @ ${ask_price:.5f}")
            else:
                print(f"   ❌ Skipping ASK order: size too small ({ask_size:.{self.config.SIZE_DECIMALS}f})")
            
            print(f"📦 Generated {len(orders)} orders total")
            return orders
            
        except Exception as e:
            print(f"❌ Error in generate_orders: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def should_cancel_orders(self, orders: List[Order], fair_price: float, signals: Optional[MarketSignals] = None) -> List[str]:
        """Determine which orders should be cancelled with microstructure considerations"""
        print("🔍 Evaluating orders for cancellation...")
        to_cancel = []
        
        # Enhanced cancellation logic with microstructure signals
        dynamic_threshold = self.config.REBALANCE_THRESHOLD
        
        if signals:
            # Be more aggressive about cancelling when conditions change rapidly
            if signals.order_velocity > 0.1:  # High order book activity
                dynamic_threshold *= 0.7  # Tighter threshold
                print(f"   ⚡ High orderbook activity - using tighter cancellation threshold: {dynamic_threshold:.4f}")
            
            # Cancel more aggressively when flow is strongly directional
            if signals.flow_confidence > 0.8 and abs(signals.overall_momentum) > 0.6:
                dynamic_threshold *= 0.8
                print(f"   🌊 Strong directional flow - using tighter cancellation threshold: {dynamic_threshold:.4f}")
        
        for order in orders:
            should_cancel = False
            reason = ""
            
            # Traditional price-based cancellation
            if order.side == 'buy' and order.price < fair_price * (1 - dynamic_threshold):
                should_cancel = True
                reason = f"bid too far below fair price ({order.price:.5f} vs {fair_price * (1 - dynamic_threshold):.5f})"
            elif order.side == 'sell' and order.price > fair_price * (1 + dynamic_threshold):
                should_cancel = True
                reason = f"ask too far above fair price ({order.price:.5f} vs {fair_price * (1 + dynamic_threshold):.5f})"
            
            # Microstructure-based cancellation
            if signals and not should_cancel:
                # Cancel if we're on the wrong side of strong flow
                if signals.flow_confidence > 0.8:
                    if order.side == 'buy' and signals.overall_momentum < -0.7:
                        should_cancel = True
                        reason = "strong sell flow detected - cancelling bid"
                    elif order.side == 'sell' and signals.overall_momentum > 0.7:
                        should_cancel = True
                        reason = "strong buy flow detected - cancelling ask"
                
                # Cancel during high adverse selection risk
                if signals.adverse_selection_risk > self.config.ADVERSE_SELECTION_THRESHOLD:
                    should_cancel = True
                    reason = f"high adverse selection risk ({signals.adverse_selection_risk:.3f})"
            
            if should_cancel:
                to_cancel.append(order.order_id)
                print(f"   ❌ Cancelling order {order.order_id}: {reason}")
        
        if not to_cancel:
            print("   ✅ No orders need cancellation")
        else:
            print(f"📝 Marked {len(to_cancel)} orders for cancellation")
        
        return to_cancel