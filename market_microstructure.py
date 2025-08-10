import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from collections import deque
from config import TradingConfig

@dataclass
class OrderbookSnapshot:
    timestamp: float
    bids: List[List[float]]  # [[price, size], ...]
    asks: List[List[float]]  # [[price, size], ...]
    mid_price: float
    spread: float
    spread_pct: float
    bid_depth: float  # Total volume in top N levels
    ask_depth: float
    
@dataclass
class TradeEvent:
    timestamp: float
    price: float
    size: float
    side: str  # "B" for buy (at ask), "A" for sell (at bid)
    is_aggressive_buy: bool
    is_aggressive_sell: bool

@dataclass
class MarketSignals:
    # Order flow signals
    volume_imbalance: float  # -1 to +1, positive = more buying pressure
    depth_pressure: float   # -1 to +1, positive = asks being depleted
    large_order_flow: float # -1 to +1, direction of large orders
    
    # Orderbook dynamics
    order_velocity: float   # Rate of order changes
    spread_volatility: float # Recent spread instability
    support_resistance: Dict[float, float]  # price -> stickiness score
    
    # Trade flow
    net_aggressive_buying: float  # -1 to +1, net direction of aggressive trades
    vwap_deviation: float   # Current price vs VWAP
    momentum_score: float   # -1 to +1, recent price momentum
    trade_velocity: float   # Recent trade frequency
    accumulation_score: float  # -1 to +1, distribution vs accumulation
    
    # Combined signals
    flow_confidence: float  # 0 to 1, how confident we are in flow direction
    adverse_selection_risk: float  # 0 to 1, risk of being picked off
    overall_momentum: float # -1 to +1, combined momentum signal
    
    # Metadata
    timestamp: float
    sample_size: int  # Number of data points used

class MarketMicrostructure:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self.orderbook_history = deque(maxlen=config.ORDERBOOK_HISTORY_SIZE)
        self.trade_history = deque(maxlen=config.TRADE_HISTORY_SIZE)
        
        # Current state
        self.current_signals = MarketSignals(
            volume_imbalance=0.0, depth_pressure=0.0, large_order_flow=0.0,
            order_velocity=0.0, spread_volatility=0.0, support_resistance={},
            net_aggressive_buying=0.0, vwap_deviation=0.0, momentum_score=0.0,
            trade_velocity=0.0, accumulation_score=0.0, flow_confidence=0.0,
            adverse_selection_risk=0.0, overall_momentum=0.0,
            timestamp=0.0, sample_size=0
        )
        
        # Analysis state
        self.last_update_time = 0.0
        self.trade_size_stats = {'mean': 0.0, 'std': 0.0, 'percentiles': {}}
        
        print(f"📊 Initialized MarketMicrostructure for {config.SYMBOL}")
        print(f"   - Orderbook history: {config.ORDERBOOK_HISTORY_SIZE} snapshots")
        print(f"   - Trade history: {config.TRADE_HISTORY_SIZE} trades")
        print(f"   - Update interval: {config.MICROSTRUCTURE_UPDATE_INTERVAL}s")
    
    def add_orderbook_snapshot(self, orderbook: Dict):
        """Add new orderbook data and trigger analysis if needed"""
        print(f"📋 Processing new orderbook snapshot...")
        
        if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):
            print("⚠️  Invalid orderbook data received")
            return
        
        # Create snapshot
        snapshot = self._create_orderbook_snapshot(orderbook)
        self.orderbook_history.append(snapshot)
        
        print(f"   - Mid price: ${snapshot.mid_price:.5f}")
        print(f"   - Spread: {snapshot.spread_pct:.3f}%")
        print(f"   - Bid depth: {snapshot.bid_depth:.2f}, Ask depth: {snapshot.ask_depth:.2f}")
        print(f"   - Orderbook history size: {len(self.orderbook_history)}")
        
        self._maybe_update_analysis()
    
    def add_trade_events(self, trades: List[Dict]):
        """Add new trade data"""
        if not trades:
            return
            
        print(f"💹 Processing {len(trades)} new trades...")
        
        new_events = []
        for trade in trades:
            event = self._create_trade_event(trade)
            if event:
                self.trade_history.append(event)
                new_events.append(event)
        
        if new_events:
            print(f"   - Added {len(new_events)} trade events")
            print(f"   - Latest trade: ${new_events[-1].price:.5f} size={new_events[-1].size:.2f} side={new_events[-1].side}")
            print(f"   - Trade history size: {len(self.trade_history)}")
            
            # Update trade statistics
            self._update_trade_statistics()
            self._maybe_update_analysis()
    
    def _create_orderbook_snapshot(self, orderbook: Dict) -> OrderbookSnapshot:
        """Convert raw orderbook to structured snapshot"""
        bids = orderbook['bids']
        asks = orderbook['asks']
        
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        spread = best_ask - best_bid if best_bid and best_ask else 0
        spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0
        
        # Calculate depth in top N levels
        bid_depth = sum(bid[1] for bid in bids[:self.config.IMBALANCE_DEPTH_LEVELS])
        ask_depth = sum(ask[1] for ask in asks[:self.config.IMBALANCE_DEPTH_LEVELS])
        
        return OrderbookSnapshot(
            timestamp=orderbook.get('timestamp', datetime.now().timestamp()),
            bids=bids,
            asks=asks,
            mid_price=mid_price,
            spread=spread,
            spread_pct=spread_pct,
            bid_depth=bid_depth,
            ask_depth=ask_depth
        )
    
    def _create_trade_event(self, trade: Dict) -> Optional[TradeEvent]:
        """Convert raw trade to structured event"""
        try:
            side = trade.get('side', '')
            is_aggressive_buy = side == 'B'  # Trade at ask (buyer aggressor)
            is_aggressive_sell = side == 'A'  # Trade at bid (seller aggressor)
            
            return TradeEvent(
                timestamp=float(trade.get('timestamp', 0)),
                price=float(trade.get('price', 0)),
                size=float(trade.get('size', 0)),
                side=side,
                is_aggressive_buy=is_aggressive_buy,
                is_aggressive_sell=is_aggressive_sell
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to parse trade: {trade}, error: {e}")
            return None
    
    def _maybe_update_analysis(self):
        """Update analysis if enough time has passed"""
        current_time = datetime.now().timestamp()
        
        if current_time - self.last_update_time >= self.config.MICROSTRUCTURE_UPDATE_INTERVAL:
            print(f"🔄 Updating microstructure analysis...")
            self._update_all_signals()
            self.last_update_time = current_time
    
    def _update_all_signals(self):
        """Comprehensive signal update"""
        print("   📈 Calculating order flow signals...")
        self._calculate_order_flow_signals()
        
        print("   📊 Analyzing orderbook dynamics...")
        self._calculate_orderbook_dynamics()
        
        print("   💱 Processing trade flow analysis...")
        self._calculate_trade_flow_signals()
        
        print("   🎯 Generating combined signals...")
        self._calculate_combined_signals()
        
        self.current_signals.timestamp = datetime.now().timestamp()
        self.current_signals.sample_size = len(self.trade_history)
        
        print(f"   ✅ Analysis complete - Flow confidence: {self.current_signals.flow_confidence:.3f}")
    
    def _calculate_order_flow_signals(self):
        """Calculate order flow imbalance, large orders, depth pressure"""
        if len(self.orderbook_history) < 2:
            return
        
        current_snapshot = self.orderbook_history[-1]
        
        # Volume imbalance ratio
        total_bid_vol = current_snapshot.bid_depth
        total_ask_vol = current_snapshot.ask_depth
        
        if total_bid_vol + total_ask_vol > 0:
            imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)
            self.current_signals.volume_imbalance = imbalance
            print(f"      Volume imbalance: {imbalance:.3f} (bid depth: {total_bid_vol:.1f}, ask depth: {total_ask_vol:.1f})")
        
        # Depth pressure (comparing recent snapshots)
        if len(self.orderbook_history) >= 5:
            recent_snapshots = list(self.orderbook_history)[-5:]
            bid_depth_change = (recent_snapshots[-1].bid_depth - recent_snapshots[0].bid_depth) / recent_snapshots[0].bid_depth
            ask_depth_change = (recent_snapshots[-1].ask_depth - recent_snapshots[0].ask_depth) / recent_snapshots[0].ask_depth
            
            depth_pressure = ask_depth_change - bid_depth_change  # Positive = asks depleting faster
            self.current_signals.depth_pressure = max(-1.0, min(1.0, depth_pressure))
            print(f"      Depth pressure: {depth_pressure:.3f}")
        
        # Large order detection (simplified - would need order-by-order tracking for full implementation)
        self._detect_large_orders()
    
    def _detect_large_orders(self):
        """Detect large orders in recent trades"""
        if not self.trade_history or not self.trade_size_stats.get('mean'):
            return
        
        recent_trades = list(self.trade_history)[-10:]  # Last 10 trades
        large_order_signal = 0.0
        
        for trade in recent_trades:
            if trade.size > self.trade_size_stats['mean'] * self.config.LARGE_ORDER_THRESHOLD:
                weight = min(trade.size / (self.trade_size_stats['mean'] * self.config.LARGE_ORDER_THRESHOLD), 3.0)
                direction = 1.0 if trade.is_aggressive_buy else -1.0
                large_order_signal += direction * weight
        
        # Normalize
        self.current_signals.large_order_flow = max(-1.0, min(1.0, large_order_signal / 10.0))
        
        if abs(self.current_signals.large_order_flow) > 0.3:
            print(f"      🚨 Large order flow detected: {self.current_signals.large_order_flow:.3f}")
    
    def _calculate_orderbook_dynamics(self):
        """Analyze orderbook change velocity and spread dynamics"""
        if len(self.orderbook_history) < self.config.ORDER_VELOCITY_WINDOW:
            return
        
        recent_snapshots = list(self.orderbook_history)[-self.config.ORDER_VELOCITY_WINDOW:]
        
        # Order velocity (simplified - measuring depth changes as proxy)
        depth_changes = []
        for i in range(1, len(recent_snapshots)):
            prev = recent_snapshots[i-1]
            curr = recent_snapshots[i]
            
            bid_change = abs(curr.bid_depth - prev.bid_depth) / max(prev.bid_depth, 0.001)
            ask_change = abs(curr.ask_depth - prev.ask_depth) / max(prev.ask_depth, 0.001)
            depth_changes.append(bid_change + ask_change)
        
        if depth_changes:
            self.current_signals.order_velocity = np.mean(depth_changes)
            print(f"      Order velocity: {self.current_signals.order_velocity:.4f}")
        
        # Spread volatility
        spreads = [s.spread_pct for s in recent_snapshots[-self.config.SPREAD_VOLATILITY_WINDOW:]]
        if len(spreads) > 1:
            self.current_signals.spread_volatility = np.std(spreads)
            print(f"      Spread volatility: {self.current_signals.spread_volatility:.4f}%")
        
        # Level stickiness (simplified implementation)
        self._calculate_level_stickiness()
    
    def _calculate_level_stickiness(self):
        """Identify sticky price levels (support/resistance)"""
        if len(self.orderbook_history) < self.config.LEVEL_STICKINESS_WINDOW:
            return
        
        recent_snapshots = list(self.orderbook_history)[-self.config.LEVEL_STICKINESS_WINDOW:]
        price_touches = {}
        
        # Count how often price levels appear in top of book
        for snapshot in recent_snapshots:
            if snapshot.bids:
                best_bid = round(snapshot.bids[0][0], 2)  # Round to avoid floating point issues
                price_touches[best_bid] = price_touches.get(best_bid, 0) + 1
            
            if snapshot.asks:
                best_ask = round(snapshot.asks[0][0], 2)
                price_touches[best_ask] = price_touches.get(best_ask, 0) + 1
        
        # Calculate stickiness scores
        self.current_signals.support_resistance = {}
        for price, touches in price_touches.items():
            stickiness = touches / len(recent_snapshots)
            if stickiness >= self.config.LEVEL_STICKINESS_THRESHOLD:
                self.current_signals.support_resistance[price] = stickiness
        
        if self.current_signals.support_resistance:
            print(f"      🎯 Found {len(self.current_signals.support_resistance)} sticky levels")
    
    def _calculate_trade_flow_signals(self):
        """Analyze trade flow patterns"""
        if len(self.trade_history) < 10:
            return
        
        recent_trades = list(self.trade_history)[-self.config.MOMENTUM_WINDOW:]
        
        # Net aggressive buying
        buy_volume = sum(t.size for t in recent_trades if t.is_aggressive_buy)
        sell_volume = sum(t.size for t in recent_trades if t.is_aggressive_sell)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            self.current_signals.net_aggressive_buying = (buy_volume - sell_volume) / total_volume
            print(f"      Net aggressive buying: {self.current_signals.net_aggressive_buying:.3f} (buy: {buy_volume:.1f}, sell: {sell_volume:.1f})")
        
        # VWAP deviation
        self._calculate_vwap_deviation()
        
        # Price momentum
        if len(recent_trades) >= 5:
            first_price = recent_trades[0].price
            last_price = recent_trades[-1].price
            momentum = (last_price - first_price) / first_price
            self.current_signals.momentum_score = max(-1.0, min(1.0, momentum * 100))  # Scale for readability
            print(f"      Price momentum: {self.current_signals.momentum_score:.3f}")
        
        # Trade velocity
        self._calculate_trade_velocity()
        
        # Accumulation/distribution
        self._calculate_accumulation_score()
    
    def _calculate_vwap_deviation(self):
        """Calculate current price deviation from VWAP"""
        if len(self.trade_history) < self.config.VWAP_WINDOW:
            return
        
        recent_trades = list(self.trade_history)[-self.config.VWAP_WINDOW:]
        
        total_value = sum(t.price * t.size for t in recent_trades)
        total_volume = sum(t.size for t in recent_trades)
        
        if total_volume > 0:
            vwap = total_value / total_volume
            current_price = recent_trades[-1].price
            deviation = (current_price - vwap) / vwap
            self.current_signals.vwap_deviation = deviation
            print(f"      VWAP deviation: {deviation:.4f} (current: ${current_price:.5f}, VWAP: ${vwap:.5f})")
    
    def _calculate_trade_velocity(self):
        """Calculate recent trade frequency"""
        if len(self.trade_history) < self.config.TRADE_VELOCITY_WINDOW:
            return
        
        recent_trades = list(self.trade_history)[-self.config.TRADE_VELOCITY_WINDOW:]
        
        if len(recent_trades) >= 2:
            time_span = recent_trades[-1].timestamp - recent_trades[0].timestamp
            if time_span > 0:
                trades_per_second = len(recent_trades) / time_span
                self.current_signals.trade_velocity = trades_per_second
                print(f"      Trade velocity: {trades_per_second:.2f} trades/sec")
    
    def _calculate_accumulation_score(self):
        """Detect accumulation vs distribution patterns"""
        if len(self.trade_history) < self.config.ACCUMULATION_WINDOW:
            return
        
        recent_trades = list(self.trade_history)[-self.config.ACCUMULATION_WINDOW:]
        
        # Simple accumulation indicator: consistent buying of increasing sizes
        buy_trades = [t for t in recent_trades if t.is_aggressive_buy]
        sell_trades = [t for t in recent_trades if t.is_aggressive_sell]
        
        buy_momentum = len(buy_trades) / len(recent_trades) if recent_trades else 0
        sell_momentum = len(sell_trades) / len(recent_trades) if recent_trades else 0
        
        # Weight by volume
        buy_volume = sum(t.size for t in buy_trades)
        sell_volume = sum(t.size for t in sell_trades)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            volume_weighted_score = (buy_volume - sell_volume) / total_volume
            frequency_score = buy_momentum - sell_momentum
            
            # Combine both signals
            self.current_signals.accumulation_score = (volume_weighted_score + frequency_score) / 2
            print(f"      Accumulation score: {self.current_signals.accumulation_score:.3f}")
    
    def _calculate_combined_signals(self):
        """Generate high-level combined signals"""
        signals = self.current_signals
        
        # Flow confidence - how aligned are the different signals?
        flow_signals = [
            signals.net_aggressive_buying,
            signals.volume_imbalance,
            signals.large_order_flow,
            signals.accumulation_score
        ]
        
        # Calculate signal alignment
        mean_signal = np.mean(flow_signals)
        signal_std = np.std(flow_signals)
        
        # High confidence when signals agree (low std) and are strong (high mean)
        confidence = (1.0 - min(signal_std / 0.5, 1.0)) * min(abs(mean_signal) / 0.5, 1.0)
        signals.flow_confidence = confidence
        
        # Adverse selection risk - high when we're against the flow
        adverse_risk = 0.0
        if abs(signals.net_aggressive_buying) > 0.5:
            # Risk is high if orderbook pressure opposes trade flow
            if (signals.net_aggressive_buying > 0 and signals.volume_imbalance < -0.3) or \
               (signals.net_aggressive_buying < 0 and signals.volume_imbalance > 0.3):
                adverse_risk = 0.8
        
        signals.adverse_selection_risk = adverse_risk
        
        # Overall momentum - combine price and flow momentum
        momentum_signals = [signals.momentum_score, signals.net_aggressive_buying, signals.accumulation_score]
        signals.overall_momentum = np.mean(momentum_signals)
        
        print(f"      📊 Combined signals: confidence={confidence:.3f}, adverse_risk={adverse_risk:.3f}, momentum={signals.overall_momentum:.3f}")
    
    def _update_trade_statistics(self):
        """Update running statistics on trade sizes"""
        if len(self.trade_history) < 10:
            return
        
        sizes = [t.size for t in self.trade_history]
        
        self.trade_size_stats['mean'] = np.mean(sizes)
        self.trade_size_stats['std'] = np.std(sizes)
        
        # Calculate percentiles
        percentiles = {}
        for p in self.config.TRADE_SIZE_PERCENTILES:
            percentiles[p] = np.percentile(sizes, p)
        self.trade_size_stats['percentiles'] = percentiles
    
    def get_current_signals(self) -> MarketSignals:
        """Get the latest market signals"""
        return self.current_signals
    
    def get_signal_summary(self) -> Dict:
        """Get a summary of current signals for logging"""
        s = self.current_signals
        return {
            'flow_confidence': f"{s.flow_confidence:.3f}",
            'net_buying': f"{s.net_aggressive_buying:.3f}",
            'volume_imbalance': f"{s.volume_imbalance:.3f}",
            'momentum': f"{s.overall_momentum:.3f}",
            'adverse_risk': f"{s.adverse_selection_risk:.3f}",
            'samples': s.sample_size
        }