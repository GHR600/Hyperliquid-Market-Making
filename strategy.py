# enhanced_strategy_with_stoploss.py - Add to your enhanced_strategy.py

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import time
import logging
import numpy as np
from collections import deque
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

class DynamicPricingEngine:
    """
    Sophisticated dynamic bid/ask calculation using:
    - Fill rate feedback loops
    - Probabilistic fill modeling
    - Queue position analysis
    - Microstructure-informed pricing
    - Adaptive spread adjustment
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Fill rate tracking
        self.recent_orders = deque(maxlen=50)  # Last 50 orders
        self.fill_rate_target = 0.40  # Target 40% fill rate
        self.fill_rate_window = 20  # Calculate over last 20 orders

        # Spread adaptation
        self.current_bid_offset = 0.0005  # Start at 5 bps
        self.current_ask_offset = 0.0005
        self.min_offset = 0.0002  # 2 bps minimum (0.02%)
        self.max_offset = 0.0030  # 30 bps maximum (0.30%)
        self.adaptation_step = 0.0001  # Adjust by 1 bp at a time

        # Performance tracking
        self.orders_placed = 0
        self.orders_filled = 0
        self.adverse_fills = 0  # Fills that moved against us immediately
        self.good_fills = 0  # Fills that were profitable

        # Last calculation metadata
        self.last_calculation = {
            'bid_ev': 0.0,
            'ask_ev': 0.0,
            'bid_fill_prob': 0.0,
            'ask_fill_prob': 0.0,
            'market_pressure': 0.0
        }

        print("🎯 Dynamic Pricing Engine initialized")
        print(f"   Target fill rate: {self.fill_rate_target*100:.0f}%")
        print(f"   Offset range: {self.min_offset*10000:.0f}-{self.max_offset*10000:.0f} bps")

    def record_order_outcome(self, filled: bool, side: str, price: float, market_moved_against: bool = False):
        """Record order outcome for adaptive learning"""
        self.orders_placed += 1

        outcome = {
            'timestamp': time.time(),
            'filled': filled,
            'side': side,
            'price': price,
            'adverse': market_moved_against if filled else False
        }
        self.recent_orders.append(outcome)

        if filled:
            self.orders_filled += 1
            if market_moved_against:
                self.adverse_fills += 1
            else:
                self.good_fills += 1

    def get_current_fill_rate(self) -> float:
        """Calculate recent fill rate"""
        if len(self.recent_orders) < 5:
            return 0.5  # Assume 50% until we have data

        recent = list(self.recent_orders)[-self.fill_rate_window:]
        filled_count = sum(1 for r in recent if r['filled'])
        return filled_count / len(recent) if recent else 0.5

    def get_adverse_selection_rate(self) -> float:
        """Calculate rate of adverse fills"""
        if self.orders_filled < 5:
            return 0.0

        return self.adverse_fills / self.orders_filled

    def adapt_offsets(self):
        """Adapt bid/ask offsets based on performance"""
        current_fill_rate = self.get_current_fill_rate()
        adverse_rate = self.get_adverse_selection_rate()

        # Feedback loop: adjust offsets to hit target fill rate
        if current_fill_rate > self.fill_rate_target + 0.10:  # Filling too often
            # Widen spreads (move away from fair price)
            self.current_bid_offset = min(self.max_offset, self.current_bid_offset + self.adaptation_step)
            self.current_ask_offset = min(self.max_offset, self.current_ask_offset + self.adaptation_step)
            print(f"   📏 Widening spreads: fill rate {current_fill_rate:.1%} > target {self.fill_rate_target:.1%}")

        elif current_fill_rate < self.fill_rate_target - 0.10:  # Not filling enough
            # Tighten spreads (move toward fair price)
            self.current_bid_offset = max(self.min_offset, self.current_bid_offset - self.adaptation_step)
            self.current_ask_offset = max(self.min_offset, self.current_ask_offset - self.adaptation_step)
            print(f"   📏 Tightening spreads: fill rate {current_fill_rate:.1%} < target {self.fill_rate_target:.1%}")

        # Additional adjustment for adverse selection
        if adverse_rate > 0.30:  # More than 30% adverse fills
            # Widen spreads regardless of fill rate
            self.current_bid_offset = min(self.max_offset, self.current_bid_offset + self.adaptation_step * 2)
            self.current_ask_offset = min(self.max_offset, self.current_ask_offset + self.adaptation_step * 2)
            print(f"   ⚠️  High adverse selection: {adverse_rate:.1%} - widening spreads")

    def calculate_fill_probability(self, offset_pct: float, side: str, orderbook: Dict,
                                   liquidity, condition) -> float:
        """
        Estimate probability of getting filled at a given offset from fair price
        """

        fair_price = orderbook.get('mid_price', 0)
        if fair_price == 0:
            return 0.0

        # Calculate where our order would be
        if side == 'bid':
            our_price = fair_price * (1 - offset_pct)
            best_price = orderbook.get('best_bid', 0)
            levels = orderbook.get('bids', [])
        else:
            our_price = fair_price * (1 + offset_pct)
            best_price = orderbook.get('best_ask', 0)
            levels = orderbook.get('asks', [])

        if not levels or best_price == 0:
            return 0.0

        # Base probability from distance to best
        if side == 'bid':
            distance_from_best = (best_price - our_price) / best_price
        else:
            distance_from_best = (our_price - best_price) / best_price

        # Closer to best = higher fill probability
        base_prob = 0.80 * np.exp(-distance_from_best * 100)

        # Adjust for queue position
        existing_liquidity_at_level = 0
        for level in levels:
            if abs(level[0] - our_price) < 0.01:
                existing_liquidity_at_level = level[1]
                break

        if existing_liquidity_at_level > 0:
            base_prob *= 0.5  # 50% reduction if behind others

        # Adjust for market volatility
        if condition.condition_type == "VOLATILE":
            base_prob *= 1.5
        elif condition.condition_type == "CALM":
            base_prob *= 0.7

        # Adjust for liquidity depth
        total_liquidity = liquidity.total_bid_liquidity + liquidity.total_ask_liquidity
        if total_liquidity < 100:
            base_prob *= 1.3
        elif total_liquidity > 1000:
            base_prob *= 0.8

        return min(1.0, max(0.0, base_prob))

    def calculate_spread_capture(self, offset_pct: float, fair_price: float) -> float:
        """Calculate how much spread we capture at this offset"""
        return fair_price * offset_pct

    def calculate_adverse_selection_cost(self, offset_pct: float, adverse_risk,
                                         signals, side: str) -> float:
        """Estimate cost of adverse selection at this offset"""

        base_cost = adverse_risk.overall_risk * 10

        # Flow-based adjustment
        if signals and hasattr(signals, 'net_aggressive_buying'):
            flow = signals.net_aggressive_buying

            if side == 'bid' and flow < -0.3:
                base_cost *= 2.0
            elif side == 'ask' and flow > 0.3:
                base_cost *= 2.0

        # Tight spreads = higher adverse selection
        if offset_pct < 0.0003:
            base_cost *= 2.0

        return base_cost

    def calculate_expected_value(self, offset_pct: float, side: str, fair_price: float,
                                orderbook: Dict, liquidity, condition, adverse_risk, signals) -> float:
        """Calculate expected value of quoting at this offset"""

        fill_prob = self.calculate_fill_probability(offset_pct, side, orderbook, liquidity, condition)
        spread_capture = self.calculate_spread_capture(offset_pct, fair_price)
        adverse_cost = self.calculate_adverse_selection_cost(offset_pct, adverse_risk, signals, side)

        ev = fill_prob * (spread_capture - adverse_cost)

        return ev

    def find_optimal_offset(self, side: str, fair_price: float, orderbook: Dict,
                           liquidity, condition, adverse_risk, signals) -> Tuple[float, Dict]:
        """Find optimal offset by maximizing expected value"""

        # Test offsets from 2 bps to 30 bps
        test_offsets = np.linspace(self.min_offset, self.max_offset, 15)

        best_ev = -999999
        best_offset = self.current_bid_offset if side == 'bid' else self.current_ask_offset

        for offset in test_offsets:
            ev = self.calculate_expected_value(
                offset, side, fair_price, orderbook, liquidity, condition, adverse_risk, signals
            )

            if ev > best_ev:
                best_ev = ev
                best_offset = offset

        fill_prob = self.calculate_fill_probability(best_offset, side, orderbook, liquidity, condition)

        metadata = {
            'best_offset': best_offset,
            'best_ev': best_ev,
            'fill_probability': fill_prob
        }

        return best_offset, metadata

    def calculate_dynamic_prices(self, fair_price: float, orderbook: Dict,
                                imbalance, gaps, liquidity, condition,
                                adverse_risk, signals, position) -> Tuple[float, float, Dict]:
        """Main method: Calculate optimal bid/ask prices dynamically"""

        print(f"\n🎯 DYNAMIC PRICING CALCULATION")
        print(f"   Fair Price: ${fair_price:.2f}")

        # Adapt offsets based on recent performance
        if self.orders_placed > 10:
            self.adapt_offsets()

        # Find optimal offsets using EV maximization
        bid_offset, bid_meta = self.find_optimal_offset(
            'bid', fair_price, orderbook, liquidity, condition, adverse_risk, signals
        )

        ask_offset, ask_meta = self.find_optimal_offset(
            'ask', fair_price, orderbook, liquidity, condition, adverse_risk, signals
        )

        # Calculate raw prices
        bid_price = fair_price * (1 - bid_offset)
        ask_price = fair_price * (1 + ask_offset)

        print(f"   📊 Optimal offsets:")
        print(f"      Bid: {bid_offset*10000:.1f} bps → ${bid_price:.2f} (Fill prob: {bid_meta['fill_probability']:.1%})")
        print(f"      Ask: {ask_offset*10000:.1f} bps → ${ask_price:.2f} (Fill prob: {ask_meta['fill_probability']:.1%})")

        # Flow-based asymmetric adjustment
        if signals and hasattr(signals, 'net_aggressive_buying'):
            flow = signals.net_aggressive_buying

            if abs(flow) > 0.3:
                if flow > 0.3:  # Strong buying
                    ask_adjustment = 1.0 + (flow * 0.5)
                    bid_adjustment = 1.0 - (flow * 0.3)
                else:  # Strong selling
                    bid_adjustment = 1.0 - (flow * 0.5)
                    ask_adjustment = 1.0 + (flow * 0.3)

                bid_price = fair_price * (1 - bid_offset * bid_adjustment)
                ask_price = fair_price * (1 + ask_offset * ask_adjustment)

                print(f"   🌊 Flow adjustment: {flow:+.2f}")

        # Inventory skewing
        if position and position.size != 0:
            max_position = self.config.MAX_POSITION_PCT
            inventory_ratio = position.size / max_position
            inventory_ratio = max(-1.0, min(1.0, inventory_ratio))
            sign = 1.0 if inventory_ratio > 0 else -1.0
            exponential_skew = sign * (abs(inventory_ratio) ** 2)
            MAX_SKEW_PCT = 0.025
            inventory_skew = exponential_skew * MAX_SKEW_PCT

            if abs(inventory_skew) > 0.01:
                spread = ask_price - bid_price
                skew_adjustment = spread * inventory_skew

                bid_price += skew_adjustment
                ask_price += skew_adjustment

                print(f"   📊 Inventory skew: {inventory_skew*100:.2f}%")

        # Round to tick size
        tick_size = orderbook.get('tick_size', 0.5)
        bid_price = round(bid_price / tick_size) * tick_size
        ask_price = round(ask_price / tick_size) * tick_size

        # Round to price decimals
        bid_price = round(bid_price, self.config.PRICE_DECIMALS)
        ask_price = round(ask_price, self.config.PRICE_DECIMALS)

        # Compile metadata
        metadata = {
            'bid_offset_bps': bid_offset * 10000,
            'ask_offset_bps': ask_offset * 10000,
            'bid_ev': bid_meta['best_ev'],
            'ask_ev': ask_meta['best_ev'],
            'bid_fill_prob': bid_meta['fill_probability'],
            'ask_fill_prob': ask_meta['fill_probability'],
            'current_fill_rate': self.get_current_fill_rate(),
            'adverse_rate': self.get_adverse_selection_rate()
        }

        spread = ask_price - bid_price
        spread_pct = (spread / fair_price) * 100

        print(f"   ✅ FINAL PRICES:")
        print(f"      Bid: ${bid_price:.2f}")
        print(f"      Ask: ${ask_price:.2f}")
        print(f"      Spread: ${spread:.2f} ({spread_pct:.3f}%)")
        print(f"   📈 Performance:")
        print(f"      Recent fill rate: {metadata['current_fill_rate']:.1%}")
        print(f"      Adverse selection: {metadata['adverse_rate']:.1%}")

        return bid_price, ask_price, metadata

# Base Enhanced Strategy Class (consolidated from enhanced_strategy.py)
class EnhancedMarketMakingStrategy:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize orderbook analyzer
        self.orderbook_analyzer = OrderbookAnalyzer(config)

        # Track our fills for adverse selection analysis
        self.recent_fills = []

        # Flow adjustment tracking (for logging)
        self.last_flow_imbalance = 0.0
        self.last_flow_adjustment = 0.0

        print(f"🎯 Enhanced MarketMaking Strategy initialized")
        print(f"   - Base spread: {config.BASE_SPREAD * 100:.2f}%")
        print(f"   - Order size: {'percentage-based' if config.USE_PERCENTAGE_SIZING else 'fixed'}")
        print(f"   - Max orders per side: {config.MAX_ORDERS_PER_SIDE}")
        print(f"   - Orderbook-based decision making: ENABLED")
        print(f"   - Flow-adjusted pricing: ENABLED")

    def update_baselines_from_learning(self, learning_stats: Dict):
        """Update strategy baselines from learning phase"""
        print("🎓 Strategy: Updating baselines from learning phase...")
        self.orderbook_analyzer.update_baselines_from_learning(learning_stats)

    def calculate_microprice(self, orderbook: Dict) -> Optional[float]:
        """Calculate microprice - a more sophisticated fair price estimate

        Microprice weights prices by the OPPOSITE side's size:
        - Thin ask side (low liquidity) -> price closer to ask
        - Thin bid side (low liquidity) -> price closer to bid

        Formula: (best_bid * ask_size + best_ask * bid_size) / (bid_size + ask_size)

        This is superior to simple mid because it accounts for liquidity imbalance
        and provides better price discovery.
        """
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if not bids or not asks:
                return None

            # Extract best bid/ask and their sizes
            best_bid = bids[0][0]
            bid_size = bids[0][1]
            best_ask = asks[0][0]
            ask_size = asks[0][1]

            # Check for zero sizes
            if bid_size <= 0 or ask_size <= 0:
                # Fallback to simple mid
                return (best_bid + best_ask) / 2

            # Calculate microprice: weights by opposite side's size
            # Thin ask -> higher weight to ask price (expect upward pressure)
            # Thin bid -> higher weight to bid price (expect downward pressure)
            microprice = (best_bid * ask_size + best_ask * bid_size) / (bid_size + ask_size)

            return microprice

        except Exception as e:
            self.logger.error(f"Error calculating microprice: {e}")
            # Fallback to simple mid
            if orderbook.get('mid_price'):
                return orderbook.get('mid_price')
            return None

    def calculate_flow_adjusted_price(self, orderbook: Dict, recent_trades: List[Dict] = None) -> Tuple[Optional[float], float, float]:
        """Calculate flow-adjusted price using order flow pressure

        Analyzes recent aggressive trades (market orders) to adjust fair price:
        - Heavy buying pressure -> adjust price UP
        - Heavy selling pressure -> adjust price DOWN

        Args:
            orderbook: Current orderbook data
            recent_trades: List of recent trades with 'side' and 'size' fields

        Returns:
            Tuple of (adjusted_price, flow_imbalance, flow_adjustment_dollars)
            - adjusted_price: Microprice adjusted for order flow
            - flow_imbalance: -1 to +1 (negative = selling, positive = buying)
            - flow_adjustment_dollars: Dollar adjustment applied
        """
        # Start with microprice
        microprice = self.calculate_microprice(orderbook)
        if microprice is None:
            return None, 0.0, 0.0

        # If no trades available, return unadjusted microprice
        if not recent_trades or len(recent_trades) == 0:
            return microprice, 0.0, 0.0

        try:
            # Get last 20 trades (or all if less than 20)
            last_trades = recent_trades[-20:]

            # Sum aggressive buy and sell volumes
            buy_volume = 0.0
            sell_volume = 0.0

            for trade in last_trades:
                size = trade.get('size', 0)
                side = trade.get('side', '')

                if side == 'B':  # Aggressive buy (market buy)
                    buy_volume += size
                elif side == 'A':  # Aggressive sell (market sell)
                    sell_volume += size

            total_volume = buy_volume + sell_volume

            # Calculate flow imbalance (-1 to +1)
            if total_volume > 0:
                flow_imbalance = (buy_volume - sell_volume) / total_volume
            else:
                flow_imbalance = 0.0

            # Calculate spread for adjustment scaling
            best_bid = orderbook.get('best_bid', 0)
            best_ask = orderbook.get('best_ask', 0)
            spread = best_ask - best_bid if best_ask > best_bid else 0.0

            # Adjust microprice based on flow
            # flow_imbalance * spread * 0.3 means:
            # - Max adjustment is 30% of spread
            # - Positive flow (buying) -> push price up
            # - Negative flow (selling) -> push price down
            flow_adjustment = flow_imbalance * spread * 0.3

            adjusted_price = microprice + flow_adjustment

            return adjusted_price, flow_imbalance, flow_adjustment

        except Exception as e:
            self.logger.error(f"Error calculating flow adjusted price: {e}")
            return microprice, 0.0, 0.0

    def calculate_depth_pressure_price(self, orderbook: Dict) -> Tuple[Optional[float], float]:
        """Calculate price adjustment based on bid/ask depth imbalance

        Deep bid side → upward pressure → higher price
        Deep ask side → downward pressure → lower price

        Args:
            orderbook: Current orderbook data

        Returns:
            Tuple of (pressure_adjusted_price, depth_pressure)
            - pressure_adjusted_price: Microprice adjusted for depth
            - depth_pressure: -1 to +1 (negative = ask heavy, positive = bid heavy)
        """
        microprice = self.calculate_microprice(orderbook)
        if microprice is None:
            return None, 0.0

        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if not bids or not asks:
                return microprice, 0.0

            # Sum volume in top 10 levels
            bid_volume = sum(bid[1] for bid in bids[:10] if len(bid) >= 2)
            ask_volume = sum(ask[1] for ask in asks[:10] if len(ask) >= 2)

            total_volume = bid_volume + ask_volume

            if total_volume <= 0:
                return microprice, 0.0

            # Calculate depth pressure (-1 to +1)
            # Positive = more bid depth (upward pressure)
            # Negative = more ask depth (downward pressure)
            depth_pressure = (bid_volume - ask_volume) / total_volume

            # Adjust microprice based on depth pressure
            # 0.002 = max 0.2% adjustment at extreme pressure
            pressure_adjustment = depth_pressure * 0.002
            pressure_price = microprice * (1 + pressure_adjustment)

            return pressure_price, depth_pressure

        except Exception as e:
            self.logger.error(f"Error calculating depth pressure price: {e}")
            return microprice, 0.0

    def calculate_multi_factor_fair_value(self, orderbook: Dict, recent_trades: List[Dict] = None) -> Tuple[Optional[float], Dict]:
        """Calculate sophisticated multi-factor fair value

        Combines three pricing models with optimal weights:
        1. Microprice (50% weight) - liquidity-weighted best bid/ask
        2. Flow-adjusted price (30% weight) - incorporates order flow toxicity
        3. Depth-pressure price (20% weight) - accounts for orderbook depth imbalance

        Args:
            orderbook: Current orderbook data
            recent_trades: Optional list of recent trades

        Returns:
            Tuple of (fair_value, components_dict)
            - fair_value: Weighted combination of all factors
            - components_dict: Dictionary with all component values for logging
        """
        components = {
            'microprice': None,
            'flow_price': None,
            'flow_imbalance': 0.0,
            'flow_adjustment': 0.0,
            'pressure_price': None,
            'depth_pressure': 0.0,
            'simple_mid': orderbook.get('mid_price', 0)
        }

        try:
            # Component 1: Microprice (50% weight)
            microprice = self.calculate_microprice(orderbook)
            if microprice is None:
                return None, components

            components['microprice'] = microprice

            # Component 2: Flow-adjusted price (30% weight)
            flow_price, flow_imbalance, flow_adjustment = self.calculate_flow_adjusted_price(
                orderbook, recent_trades
            )
            components['flow_price'] = flow_price if flow_price else microprice
            components['flow_imbalance'] = flow_imbalance
            components['flow_adjustment'] = flow_adjustment

            # Component 3: Depth-pressure price (20% weight)
            pressure_price, depth_pressure = self.calculate_depth_pressure_price(orderbook)
            components['pressure_price'] = pressure_price if pressure_price else microprice
            components['depth_pressure'] = depth_pressure

            # Combine with optimal weights
            # 50% microprice (base truth)
            # 30% flow (short-term directional signal)
            # 20% depth (structural imbalance)
            fair_value = (
                0.5 * components['microprice'] +
                0.3 * components['flow_price'] +
                0.2 * components['pressure_price']
            )

            return fair_value, components

        except Exception as e:
            self.logger.error(f"Error calculating multi-factor fair value: {e}")
            return microprice if microprice else None, components

    def calculate_fair_price(self, orderbook: Dict, recent_trades: List[Dict] = None) -> Optional[float]:
        """Calculate sophisticated multi-factor fair price

        Uses advanced multi-factor model combining:
        1. Microprice (50% weight) - liquidity-weighted best bid/ask
        2. Flow-adjusted price (30% weight) - order flow toxicity
        3. Depth-pressure price (20% weight) - orderbook depth imbalance

        Falls back to microprice if signals are missing.

        Args:
            orderbook: Current orderbook data
            recent_trades: Optional list of recent trades for flow analysis

        Returns:
            Fair price estimate, or None if unable to calculate
        """
        # Use multi-factor model for most sophisticated pricing
        fair_value, components = self.calculate_multi_factor_fair_value(orderbook, recent_trades)

        if fair_value is None:
            # Fallback to microprice if multi-factor fails
            return self.calculate_microprice(orderbook)

        # Store flow data for status logging
        self.last_flow_imbalance = components['flow_imbalance']
        self.last_flow_adjustment = components['flow_adjustment']

        # Detailed logging of all components
        simple_mid = components['simple_mid']
        microprice = components['microprice']
        flow_price = components['flow_price']
        pressure_price = components['pressure_price']
        flow_imbalance = components['flow_imbalance']
        flow_adjustment = components['flow_adjustment']
        depth_pressure = components['depth_pressure']

        # Log when there are meaningful differences or signals
        should_log = False
        if simple_mid > 0 and microprice:
            diff_pct = abs(microprice - simple_mid) / simple_mid * 100
            if diff_pct > 0.001:
                should_log = True
        if abs(flow_adjustment) > 0.001 or abs(depth_pressure) > 0.05:
            should_log = True

        if should_log and simple_mid > 0:
            print(f"💎 Multi-Factor Fair Value Calculation:")
            print(f"   Simple Mid:     ${simple_mid:.5f}")

            # Component 1: Microprice (50% weight)
            if microprice:
                mid_diff_pct = (microprice - simple_mid) / simple_mid * 100
                print(f"   Microprice:     ${microprice:.5f} ({mid_diff_pct:+.4f}%) [50% weight]")

            # Component 2: Flow price (30% weight)
            if flow_price and abs(flow_imbalance) > 0.01:
                flow_direction = "↑ BUY" if flow_imbalance > 0 else "↓ SELL"
                print(f"   Flow Price:     ${flow_price:.5f} [30% weight]")
                print(f"     Flow Imbal:   {flow_imbalance:+.3f} ({flow_direction} pressure)")
                if abs(flow_adjustment) > 0.001:
                    print(f"     Flow Adj:     ${flow_adjustment:+.5f}")

            # Component 3: Depth pressure (20% weight)
            if pressure_price and abs(depth_pressure) > 0.01:
                pressure_direction = "↑ BID heavy" if depth_pressure > 0 else "↓ ASK heavy"
                print(f"   Pressure Price: ${pressure_price:.5f} [20% weight]")
                print(f"     Depth Ratio:  {depth_pressure:+.3f} ({pressure_direction})")

            # Final weighted result
            diff_from_mid = fair_value - simple_mid
            diff_from_mid_pct = (diff_from_mid / simple_mid) * 100
            print(f"   ───────────────────────────────")
            print(f"   Final Fair:     ${fair_value:.5f} ({diff_from_mid_pct:+.4f}% from mid)")

        return fair_value

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

    def should_cancel_orders(self, current_orders: List, fair_price: float, signals: Optional[MarketSignals] = None) -> List:
        """Determine which orders should be cancelled based on price deviation from fair value

        Args:
            current_orders: List of currently open orders
            fair_price: Current calculated fair price
            signals: Optional market signals

        Returns:
            List of orders that should be cancelled
        """
        orders_to_cancel = []

        if not current_orders or not fair_price:
            return orders_to_cancel

        # Cancel threshold: orders that are more than 0.5% away from fair price
        cancel_threshold_pct = getattr(self.config, 'ORDER_CANCEL_THRESHOLD_PCT', 0.5) / 100

        for order in current_orders:
            try:
                order_price = order.get('limit_px', 0)
                if order_price == 0:
                    continue

                # Calculate distance from fair price
                price_deviation = abs(order_price - fair_price) / fair_price

                # Cancel if too far from fair price
                if price_deviation > cancel_threshold_pct:
                    orders_to_cancel.append(order)

            except Exception as e:
                self.logger.error(f"Error evaluating order for cancellation: {e}")
                continue

        return orders_to_cancel

    def find_optimal_quote_levels(self, orderbook: Dict, fair_value: float, side: str) -> Optional[float]:
        """Find optimal price level to join existing liquidity

        Analyzes existing orderbook levels to determine if we should join an existing
        level rather than creating a new one. This improves fill probability and
        reduces market impact.

        Args:
            orderbook: Current orderbook data
            fair_value: Current fair value estimate
            side: 'bid' or 'ask'

        Returns:
            Optimal price to quote, or None if no good level found
        """
        if not self.config.JOIN_EXISTING_LEVELS:
            return None

        try:
            # Get the appropriate side of the book
            if side == 'bid':
                levels = orderbook.get('bids', [])
            elif side == 'ask':
                levels = orderbook.get('asks', [])
            else:
                return None

            if not levels or len(levels) == 0:
                return None

            # Configuration parameters
            min_join_size = fair_value * self.config.MIN_JOIN_SIZE_MULTIPLIER
            max_distance_pct = self.config.MAX_JOIN_DISTANCE_PCT

            # Look at top 5 levels
            for i, level in enumerate(levels[:5]):
                if len(level) < 2:
                    continue

                price = level[0]
                size = level[1]

                # Calculate distance from fair value
                distance_pct = abs(price - fair_value) / fair_value

                # Check if this level is "good to join"
                is_close_enough = distance_pct < max_distance_pct
                is_large_enough = size > min_join_size

                if is_close_enough and is_large_enough:
                    # Found a good level to join
                    return price

            # No good level found
            return None

        except Exception as e:
            self.logger.error(f"Error finding optimal quote level: {e}")
            return None

    def calculate_order_prices(self, fair_price: float, orderbook: Dict, position: Optional[Position],
                              signals: Optional[MarketSignals] = None) -> Tuple[float, float]:
        """Calculate order prices with dynamic spread widening based on adverse selection risk"""
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)

        # Start with base spread
        base_spread = self.config.BASE_SPREAD
        risk_multiplier = 1.0
        widening_reasons = []

        # Dynamic spread widening based on risk factors

        # 1. High adverse selection risk
        if hasattr(adverse_risk, 'overall_risk') and adverse_risk.overall_risk > 0.6:
            risk_multiplier *= 1.4
            widening_reasons.append(f"High adverse risk ({adverse_risk.overall_risk:.2f})")

        # 2. Abnormally tight spread (likely toxic flow)
        if hasattr(adverse_risk, 'spread_percentile') and adverse_risk.spread_percentile < 20:
            risk_multiplier *= 1.3
            widening_reasons.append(f"Tight spread percentile ({adverse_risk.spread_percentile:.0f})")

        # 3. Volatile market conditions
        if condition.condition_type == "VOLATILE":
            risk_multiplier *= 1.5
            widening_reasons.append("Volatile market")
        elif condition.condition_type == "CALM":
            risk_multiplier *= 0.8
            widening_reasons.append("Calm market (tighter)")

        # 4. Very tight current spread (< 0.05% = 5 bps)
        current_spread_pct = orderbook.get('spread_pct', 0)
        if current_spread_pct < 0.05 and current_spread_pct > 0:
            risk_multiplier *= 1.2
            widening_reasons.append(f"Very tight market ({current_spread_pct:.3f}%)")

        # Apply the risk multiplier to base spread
        adjusted_spread = base_spread * risk_multiplier
        bid_spread = adjusted_spread / 2
        ask_spread = adjusted_spread / 2

        # Log spread adjustments when significant
        if risk_multiplier > 1.1 or risk_multiplier < 0.9:
            print(f"📏 Dynamic Spread Adjustment:")
            print(f"   Base Spread: {base_spread*100:.2f}%")
            print(f"   Risk Multiplier: {risk_multiplier:.2f}x")
            print(f"   Final Spread: {adjusted_spread*100:.2f}%")
            if widening_reasons:
                print(f"   Reasons: {', '.join(widening_reasons)}")

        # Calculate base bid/ask prices from fair value and spread
        calculated_bid = fair_price * (1 - bid_spread)
        calculated_ask = fair_price * (1 + ask_spread)

        # Try to find existing levels to join (intelligent order placement)
        join_bid = self.find_optimal_quote_levels(orderbook, fair_price, 'bid')
        join_ask = self.find_optimal_quote_levels(orderbook, fair_price, 'ask')

        # Decide whether to join or create new levels
        # Join if the existing level is within 0.2% of our calculated price
        max_join_deviation = 0.002  # 0.2%

        # Bid side logic
        if join_bid is not None:
            bid_deviation = abs(join_bid - calculated_bid) / calculated_bid
            if bid_deviation <= max_join_deviation:
                bid_price = join_bid
                # Log joining
                if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                    bids = orderbook.get('bids', [])
                    join_size = next((b[1] for b in bids if b[0] == join_bid), 0)
                    print(f"📍 Joining existing bid at ${join_bid:.5f} (size: {join_size:.4f})")
            else:
                bid_price = calculated_bid
                if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                    print(f"📍 Creating new bid level at ${calculated_bid:.5f}")
        else:
            bid_price = calculated_bid
            if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                print(f"📍 Creating new bid level at ${calculated_bid:.5f}")

        # Ask side logic
        if join_ask is not None:
            ask_deviation = abs(join_ask - calculated_ask) / calculated_ask
            if ask_deviation <= max_join_deviation:
                ask_price = join_ask
                # Log joining
                if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                    asks = orderbook.get('asks', [])
                    join_size = next((a[1] for a in asks if a[0] == join_ask), 0)
                    print(f"📍 Joining existing ask at ${join_ask:.5f} (size: {join_size:.4f})")
            else:
                ask_price = calculated_ask
                if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                    print(f"📍 Creating new ask level at ${calculated_ask:.5f}")
        else:
            ask_price = calculated_ask
            if hasattr(self.config, 'LOG_LEVEL') and self.config.LOG_LEVEL == "DEBUG":
                print(f"📍 Creating new ask level at ${calculated_ask:.5f}")

        # Round to tick size
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

        # Initialize dynamic pricing engine
        self.pricing_engine = DynamicPricingEngine(config)
        print("🎯 Dynamic pricing engine integrated with risk management")

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
        """Generate stop-loss order - FIXED VERSION"""
        if not self.check_stop_loss_trigger(position, current_price):
            return None

        print(f"🛑 STOP-LOSS TRIGGERED!")
        print(f"   Position: {position.size:.4f}")
        print(f"   Current price: ${current_price:.5f}")
        print(f"   Stop-loss price: ${self.stop_loss_price:.5f}")

        # Calculate stop execution price with slippage buffer
        if position.size > 0:  # Long position - sell at market
            # Use market order to ensure execution
            order = {
                'coin': str(self.config.SYMBOL),
                'is_buy': False,  # Sell to close long
                'sz': float(abs(position.size)),
                'limit_px': float(current_price * 0.98),  # 2% slippage buffer
                'order_type': {'limit': {'tif': 'Ioc'}},  # Immediate or cancel
                'reduce_only': True
            }
        else:  # Short position - buy at market
            order = {
                'coin': str(self.config.SYMBOL),
                'is_buy': True,  # Buy to close short
                'sz': float(abs(position.size)),
                'limit_px': float(current_price * 1.02),  # 2% slippage buffer
                'order_type': {'limit': {'tif': 'Ioc'}},
                'reduce_only': True
            }

        print(f"🛑 Stop-loss order: {'BUY' if order['is_buy'] else 'SELL'} {order['sz']:.4f} @ ${order['limit_px']:.5f}")

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
        """Calculate order prices using sophisticated dynamic pricing engine"""

        # Update position tracking
        self.update_position_tracking(position, fair_price)

        # Get comprehensive orderbook analysis
        imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
        adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)

        # Use dynamic pricing engine
        bid_price, ask_price, metadata = self.pricing_engine.calculate_dynamic_prices(
            fair_price, orderbook, imbalance, gaps, liquidity, condition, adverse_risk, signals, position
        )

        # Store metadata for dashboard
        if not hasattr(self, '_pricing_metadata'):
            self._pricing_metadata = {}
        self._pricing_metadata = metadata

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

    def get_strategy_status(self, orderbook: Dict) -> Dict:
        """Get current strategy status for logging"""
        try:
            # Analyze current market condition
            imbalance, gaps, liquidity, condition = self.orderbook_analyzer.analyze_orderbook(orderbook)
            adverse_risk = self.orderbook_analyzer.calculate_adverse_selection_risk(orderbook, self.recent_fills)

            return {
                'condition_type': condition.condition_type,
                'condition_confidence': condition.confidence,
                'adverse_risk': adverse_risk.overall_risk,
                'spread_percentile': adverse_risk.spread_percentile,
                'book_stability': condition.book_stability,
                'imbalance_ratio': imbalance.imbalance_ratio
            }
        except Exception as e:
            self.logger.error(f"Error getting strategy status: {e}")
            return {
                'condition_type': 'UNKNOWN',
                'condition_confidence': 0.0,
                'adverse_risk': 0.0,
                'spread_percentile': 0.0,
                'book_stability': 0.0,
                'imbalance_ratio': 0.0
            }

