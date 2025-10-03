# enhanced_strategy.py - Updated strategy.py with orderbook-based decision making

import logging
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
from typing import Dict, List, Tuple, Optional
from config import TradingConfig
from position_tracker import Position, Order
from market_microstructure import MarketSignals
from orderbook_analyzer import OrderbookAnalyzer, OrderbookImbalance, OrderbookGaps, LiquidityProfile, MarketCondition, AdverseSelectionRisk

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
    
    def add_fill(self, fill_data: Dict):
        """Track our fills for adverse selection analysis"""
        self.recent_fills.append({
            'timestamp': fill_data.get('timestamp', 0),
            'side': fill_data.get('side', ''),
            'price': fill_data.get('price', 0),
            'size': fill_data.get('size', 0)
        })
        
        # Keep only recent fills (last 50)
        if len(self.recent_fills) > 50:
            self.recent_fills = self.recent_fills[-50:]
    
    def calculate_fair_price(self, orderbook: Dict) -> Optional[float]:
        """Calculate sophisticated fair price using orderbook analysis"""
        print("💰 Calculating enhanced fair price...")
        
        # Get comprehensive orderbook analysis
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        
        if imbalance.weighted_mid == 0:
            print("⚠️  Cannot calculate fair price - invalid orderbook")
            return None
        
        # Use orderbook-informed fair price
        fair_price = self.orderbook_analyzer.calculate_smart_fair_price(orderbook, imbalance)
        
        # Log analysis
        analysis_summary = self.orderbook_analyzer.get_analysis_summary(imbalance, condition, 
                                                                        self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills))
        print(f"   📊 Market analysis: {analysis_summary}")
        print(f"   💰 Enhanced fair price: ${fair_price:.5f} (vs simple mid: ${orderbook.get('mid_price', 0):.5f})")
        
        return fair_price
    
    def should_place_orders(self, position: Optional[Position], orderbook: Dict, signals: Optional[MarketSignals] = None) -> bool:
        """Enhanced order placement decision using orderbook analysis"""
        print("🤔 Enhanced evaluation for order placement...")
        
        # Get orderbook analysis
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)
        
        # Use orderbook analyzer's decision
        if not self.orderbook_analyzer.should_place_orders(condition, adverse_risk):
            return False
        
        # Additional position-based checks
        if position and abs(position.size) >= self.config.MAX_POSITION_PCT:
            print(f"❌ Position too large: {position.size} (max: {self.config.MAX_POSITION_PCT})")
            return False
        
        # Check microstructure signals if available
        if signals and signals.adverse_selection_risk > self.config.ADVERSE_SELECTION_THRESHOLD:
            print(f"❌ High microstructure adverse risk: {signals.adverse_selection_risk:.3f}")
            return False
        
        print("✅ Enhanced analysis confirms favorable conditions")
        return True
    
    def calculate_dynamic_spreads(self, orderbook: Dict, condition: MarketCondition, 
                                 adverse_risk: AdverseSelectionRisk, position: Optional[Position] = None) -> Tuple[float, float]:
        """Calculate dynamic spreads based on market conditions"""
        print("📈 Calculating dynamic spreads...")
        
        base_spread = self.config.BASE_SPREAD
        spread_multiplier = 1.0
        
        # Adjust for market condition
        if condition.condition_type == "CALM":
            spread_multiplier *= 0.8  # Tighter spreads in calm markets
            print(f"   😌 Calm market - tightening spreads by 20%")
        elif condition.condition_type == "TRENDING":
            spread_multiplier *= 1.1  # Slightly wider in trending
            print(f"   📈 Trending market - widening spreads by 10%")
        elif condition.condition_type == "VOLATILE":
            spread_multiplier *= 1.5  # Much wider in volatile
            print(f"   🌪️  Volatile market - widening spreads by 50%")
        elif condition.condition_type == "NORMAL":
            spread_multiplier *= 1.0  # Keep base spread
            print(f"   📊 Normal market - using base spreads")
        
        # Adjust for adverse selection risk
        if adverse_risk.overall_risk > 0.6:
            risk_multiplier = 1.0 + adverse_risk.overall_risk
            spread_multiplier *= risk_multiplier
            print(f"   ⚠️  High adverse risk - additional {(risk_multiplier-1)*100:.0f}% spread widening")
        
        # Adjust for book stability
        if condition.book_stability < 0.5:
            stability_multiplier = 2.0 - condition.book_stability
            spread_multiplier *= stability_multiplier
            print(f"   📊 Unstable book - additional {(stability_multiplier-1)*100:.0f}% spread widening")
        
        # Position-based skew
        position_skew = 0.0
        if position and position.size != 0:
            position_ratio = position.size / self.config.MAX_POSITION_PCT
            position_skew = position_ratio * base_spread * 0.3
            print(f"   🎯 Position skew: {position_skew*100:.2f}% (position: {position.size:.4f})")
        
        # Calculate final spreads
        adjusted_spread = base_spread * spread_multiplier
        bid_spread = adjusted_spread / 2 + position_skew
        ask_spread = adjusted_spread / 2 - position_skew
        
        print(f"   📊 Final spreads: bid={bid_spread*100:.3f}%, ask={ask_spread*100:.3f}% (base: {base_spread*100:.3f}%)")
        
        return bid_spread, ask_spread
    
    def calculate_order_prices(self, fair_price: float, orderbook: Dict, position: Optional[Position], 
                              signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Calculate order prices using orderbook analysis and gaps"""
        print("📈 Calculating enhanced order prices...")
        
        # Get orderbook analysis
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)
        
        # Calculate dynamic spreads
        bid_spread, ask_spread = self.calculate_dynamic_spreads(orderbook, condition, adverse_risk, position)
        
        # Calculate base prices
        base_bid_price = fair_price * (1 - bid_spread)
        base_ask_price = fair_price * (1 + ask_spread)
        
        # Use gap analysis for optimal placement
        optimal_bid, optimal_ask = self.orderbook_analyzer.find_optimal_order_prices(orderbook, gaps, fair_price)
        
        # Choose between base calculation and gap-based placement
        tick_size = orderbook.get('tick_size', 0.5)
        
        # Use gap placement if it's not too far from our calculated price
        final_bid = base_bid_price
        final_ask = base_ask_price
        
        if abs(optimal_bid - base_bid_price) / fair_price < 0.002:  # Within 0.2%
            final_bid = optimal_bid
            print(f"   🎯 Using gap-based bid placement")
        
        if abs(optimal_ask - base_ask_price) / fair_price < 0.002:
            final_ask = optimal_ask
            print(f"   🎯 Using gap-based ask placement")
        
        # Round to tick size
        final_bid = self._round_price_to_tick(final_bid, tick_size)
        final_ask = self._round_price_to_tick(final_ask, tick_size)
        
        print(f"   💵 Final prices: bid=${final_bid:.5f}, ask=${final_ask:.5f}")
        print(f"   📏 Effective spread: {((final_ask - final_bid) / fair_price * 100):.3f}%")
        
        return final_bid, final_ask
    
    def calculate_dynamic_order_sizes(self, position: Optional[Position], current_price: float, 
                                    account_value: float, condition: MarketCondition, 
                                    adverse_risk: AdverseSelectionRisk, signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Calculate order sizes based on market conditions"""
        print("📊 Calculating dynamic order sizes...")
        
        # Start with base size calculation
        if self.config.USE_PERCENTAGE_SIZING:
            if account_value <= self.config.MIN_ACCOUNT_VALUE:
                print(f"❌ Account value too low: ${account_value:.2f}")
                return 0.0, 0.0
            
            dollar_amount = account_value * self.config.ORDER_SIZE_PCT / 100
            base_size = dollar_amount / current_price
            print(f"   💰 Base size: {base_size:.4f} (${dollar_amount:.2f})")
        else:
            base_size = getattr(self.config, 'ORDER_SIZE', 1.0)
            print(f"   📏 Fixed base size: {base_size:.4f}")
        
        # Apply condition-based adjustments
        size_multiplier = 1.0
        
        if condition.condition_type == "CALM":
            size_multiplier *= 1.2  # Larger sizes in calm markets
            print(f"   😌 Calm market - increasing size by 20%")
        elif condition.condition_type == "TRENDING":
            size_multiplier *= 0.9  # Smaller sizes in trending markets
            print(f"   📈 Trending market - reducing size by 10%")
        elif condition.condition_type == "VOLATILE":
            size_multiplier *= 0.6  # Much smaller in volatile markets
            print(f"   🌪️  Volatile market - reducing size by 40%")
        
        # Adjust for adverse selection risk
        if adverse_risk.overall_risk > 0.5:
            risk_reduction = 1.0 - (adverse_risk.overall_risk - 0.5)
            size_multiplier *= risk_reduction
            print(f"   ⚠️  High adverse risk - reducing size by {(1-risk_reduction)*100:.0f}%")
        
        # Adjust for book stability
        if condition.book_stability < 0.6:
            stability_factor = condition.book_stability / 0.6
            size_multiplier *= stability_factor
            print(f"   📊 Unstable book - reducing size by {(1-stability_factor)*100:.0f}%")
        
        # Apply microstructure signals
        if signals:
            if signals.flow_confidence > 0.7 and abs(signals.overall_momentum) < 0.3:
                size_multiplier *= 1.3  # Favorable ranging conditions
                print(f"   🧠 Favorable microstructure - increasing size by 30%")
            elif signals.adverse_selection_risk > 0.7:
                size_multiplier *= 0.7
                print(f"   🧠 Microstructure adverse risk - reducing size by 30%")
        
        # Calculate final sizes
        adjusted_size = base_size * size_multiplier
        adjusted_size = max(adjusted_size, self.config.MIN_ORDER_SIZE)
        
        # Position limits
        current_position = position.size if position else 0.0
        max_position = self.config.MAX_POSITION_PCT
        
        max_buy = max_position - current_position
        max_sell = current_position + max_position
        
        # Final size calculation
        bid_size = min(adjusted_size, max_buy) if max_buy > self.config.MIN_ORDER_SIZE else 0
        ask_size = min(adjusted_size, max_sell) if max_sell > self.config.MIN_ORDER_SIZE else 0
        
        # Round to size decimals
        bid_size = self._round_size_to_decimals(bid_size)
        ask_size = self._round_size_to_decimals(ask_size)
        
        # Final minimum size check
        if bid_size < self.config.MIN_ORDER_SIZE:
            bid_size = 0.0
        if ask_size < self.config.MIN_ORDER_SIZE:
            ask_size = 0.0
        
        print(f"   📋 Final sizes: bid={bid_size:.{self.config.SIZE_DECIMALS}f}, ask={ask_size:.{self.config.SIZE_DECIMALS}f}")
        print(f"   📊 Size multiplier applied: {size_multiplier:.2f}")
        
        return bid_size, ask_size
    
    def generate_orders(self, orderbook: Dict, position: Optional[Position], account_value: float, 
                       signals: Optional[MarketSignals] = None) -> List[Dict]:
        """Generate orders using enhanced orderbook analysis"""
        print("🎯 Generating enhanced orders...")
        orders = []
        
        try:
            # Get comprehensive orderbook analysis
            imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
            adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)
            
            # Check if we should place orders
            if not self.should_place_orders(position, orderbook, signals):
                print("❌ Enhanced analysis: conditions not favorable - no orders generated")
                return orders
            
            # Calculate fair price
            fair_price = self.calculate_fair_price(orderbook)
            if not fair_price:
                print("❌ Cannot determine enhanced fair price - no orders generated")
                return orders
            
            # Calculate order prices using orderbook analysis
            bid_price, ask_price = self.calculate_order_prices(fair_price, orderbook, position, signals)
            
            # Calculate dynamic order sizes
            bid_size, ask_size = self.calculate_dynamic_order_sizes(
                position, fair_price, account_value, condition, adverse_risk, signals
            )
            
            print(f"📊 Enhanced order parameters:")
            print(f"   💵 Prices: bid=${bid_price:.5f}, ask=${ask_price:.5f}")
            print(f"   📏 Sizes: bid={bid_size:.{self.config.SIZE_DECIMALS}f}, ask={ask_size:.{self.config.SIZE_DECIMALS}f}")
            print(f"   🎯 Condition: {condition.condition_type}, Risk: {adverse_risk.overall_risk:.3f}")
            
            # Create orders in Hyperliquid format
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
                print(f"   ✅ Generated enhanced BID: {bid_size:.{self.config.SIZE_DECIMALS}f} @ ${bid_price:.5f}")
            else:
                print(f"   ❌ Skipping BID: size too small or conditions unfavorable")
            
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
                print(f"   ✅ Generated enhanced ASK: {ask_size:.{self.config.SIZE_DECIMALS}f} @ ${ask_price:.5f}")
            else:
                print(f"   ❌ Skipping ASK: size too small or conditions unfavorable")
            
            print(f"📦 Generated {len(orders)} enhanced orders")
            return orders
            
        except Exception as e:
            print(f"❌ Error in enhanced order generation: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def should_cancel_orders(self, orders: List[Order], fair_price: float, 
                           signals: Optional[MarketSignals] = None) -> List[str]:
        """Enhanced order cancellation logic"""
        print("🔍 Enhanced order cancellation evaluation...")
        to_cancel = []
        
        # Get current market analysis for cancellation decisions
        # Note: This would need orderbook passed in, for now use traditional logic with enhancements
        
        # More aggressive cancellation based on adverse selection
        dynamic_threshold = self.config.REBALANCE_THRESHOLD
        
        # Tighten threshold if we have high adverse selection risk
        if len(self.recent_fills) > 10:
            recent_buy_fills = sum(1 for fill in self.recent_fills[-10:] if fill.get('side') == 'buy')
            fill_imbalance = abs(recent_buy_fills - 5) / 5  # Deviation from 50/50
            
            if fill_imbalance > 0.6:  # Very imbalanced fills
                dynamic_threshold *= 0.5  # Much tighter cancellation
                print(f"   ⚠️  High fill imbalance detected - using tight threshold: {dynamic_threshold:.4f}")
        
        # Enhanced microstructure-based cancellation
        if signals:
            if signals.adverse_selection_risk > 0.7:
                dynamic_threshold *= 0.6  # Tighter when adverse risk is high
                print(f"   🧠 High microstructure risk - tightening threshold to {dynamic_threshold:.4f}")
            
            if signals.flow_confidence > 0.8 and abs(signals.overall_momentum) > 0.6:
                dynamic_threshold *= 0.7  # Tighter during strong directional flow
                print(f"   🌊 Strong directional flow - tightening threshold to {dynamic_threshold:.4f}")
        
        # Traditional price-based cancellation with dynamic threshold
        for order in orders:
            should_cancel = False
            reason = ""
            
            if order.side == 'buy' and order.price < fair_price * (1 - dynamic_threshold):
                should_cancel = True
                reason = f"bid too far below enhanced fair price"
            elif order.side == 'sell' and order.price > fair_price * (1 + dynamic_threshold):
                should_cancel = True
                reason = f"ask too far above enhanced fair price"
            
            # Enhanced microstructure cancellation
            if signals and not should_cancel:
                if signals.flow_confidence > 0.7:
                    if order.side == 'buy' and signals.overall_momentum < -0.5:
                        should_cancel = True
                        reason = "strong sell momentum detected"
                    elif order.side == 'sell' and signals.overall_momentum > 0.5:
                        should_cancel = True
                        reason = "strong buy momentum detected"
            
            if should_cancel:
                to_cancel.append(order.order_id)
                print(f"   ❌ Enhanced cancellation: {order.order_id} - {reason}")
        
        if not to_cancel:
            print("   ✅ No orders need enhanced cancellation")
        else:
            print(f"📝 Enhanced analysis marked {len(to_cancel)} orders for cancellation")
        
        return to_cancel
    
    def _round_price_to_tick(self, price: float, tick_size: float) -> float:
        """Round price to tick size"""
        if price <= 0 or tick_size <= 0:
            return price
        
        rounded = round(price / tick_size) * tick_size
        return round(rounded, self.config.PRICE_DECIMALS)
    
    def _round_size_to_decimals(self, size: float) -> float:
        """Round size to appropriate decimals"""
        if size <= 0:
            return 0.0
        
        return round(size, self.config.SIZE_DECIMALS)
    
    def get_strategy_status(self, orderbook: Dict) -> Dict:
        """Get current strategy status for logging/monitoring"""
        try:
            imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
            adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)
            
            return {
                'condition_type': condition.condition_type,
                'condition_confidence': condition.confidence,
                'book_stability': condition.book_stability,
                'imbalance_ratio': imbalance.imbalance_ratio,
                'adverse_risk': adverse_risk.overall_risk,
                'spread_percentile': adverse_risk.spread_percentile,
                'recent_fills': len(self.recent_fills),
                'largest_bid_gap': gaps.largest_bid_gap[1] if gaps.largest_bid_gap else 0,
                'largest_ask_gap': gaps.largest_ask_gap[1] if gaps.largest_ask_gap else 0,
                'liquidity_concentration': liquidity.liquidity_concentration
            }
        except Exception as e:
            print(f"⚠️  Error getting strategy status: {e}")
            return {'error': str(e)}


# For backward compatibility, create an alias
MarketMakingStrategy = EnhancedMarketMakingStrategy