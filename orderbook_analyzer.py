# orderbook_analyzer.py
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from collections import deque
import time
from config import TradingConfig

@dataclass
class OrderbookLevel:
    price: float
    size: float
    cumulative_size: float
    distance_from_mid: float

@dataclass
class OrderbookImbalance:
    bid_volume: float
    ask_volume: float
    imbalance_ratio: float  # -1 to +1, positive = more bids
    depth_ratio: float      # ratio of bid depth to ask depth
    weighted_mid: float     # volume-weighted mid price

@dataclass
class OrderbookGaps:
    bid_gaps: List[Tuple[float, float]]  # (price, gap_size)
    ask_gaps: List[Tuple[float, float]]
    largest_bid_gap: Tuple[float, float]
    largest_ask_gap: Tuple[float, float]

@dataclass
class LiquidityProfile:
    total_bid_liquidity: float
    total_ask_liquidity: float
    bid_depth_at_distances: Dict[float, float]  # distance_pct -> cumulative_volume
    ask_depth_at_distances: Dict[float, float]
    liquidity_concentration: float  # 0-1, higher = more concentrated at top

@dataclass
class MarketCondition:
    spread_pct: float
    spread_volatility: float
    book_stability: float      # 0-1, higher = more stable
    trade_frequency: float     # trades per second
    condition_type: str        # 'CALM', 'TRENDING', 'VOLATILE', 'ILLIQUID'
    confidence: float          # 0-1, confidence in classification

@dataclass
class AdverseSelectionRisk:
    spread_percentile: float   # current spread vs historical
    fill_rate_imbalance: float # if we're getting filled more on one side
    price_impact_risk: float   # 0-1, risk of immediate adverse price move
    informed_trader_signals: float  # 0-1, signs of informed trading
    overall_risk: float        # 0-1, combined risk score

class OrderbookAnalyzer:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Historical data for analysis
        self.spread_history = deque(maxlen=1000)
        self.imbalance_history = deque(maxlen=500)
        self.fill_history = deque(maxlen=200)  # Track our fills
        self.price_history = deque(maxlen=500)
        
        # Market condition baselines (set during learning phase)
        self.baseline_spread = None
        self.baseline_imbalance_std = None
        self.baseline_volatility = None
        
        print(f"📊 Orderbook Analyzer initialized")
    
    def update_baselines_from_learning(self, learning_stats: Dict):
        """Update baselines from learning phase data - FIXED VERSION"""
        print("📚 Updating analysis baselines from learning phase...")
        
        try:
            if learning_stats.get('spreads'):
                spreads = np.array(learning_stats['spreads'])
                self.baseline_spread = {
                    'mean': float(np.mean(spreads)),
                    'std': float(np.std(spreads)),
                    'percentiles': {
                        '25': float(np.percentile(spreads, 25)),
                        '50': float(np.percentile(spreads, 50)),
                        '75': float(np.percentile(spreads, 75)),
                        '90': float(np.percentile(spreads, 90)),
                        '95': float(np.percentile(spreads, 95))
                    }
                }
                print(f"   📈 Baseline spread: {self.baseline_spread['mean']:.4f}% ± {self.baseline_spread['std']:.4f}%")
            
            if learning_stats.get('imbalances'):
                # Handle imbalances which might be a list of dicts
                imbalances_list = learning_stats['imbalances']
                if imbalances_list and len(imbalances_list) > 0:
                    # Extract just the imbalance values
                    if isinstance(imbalances_list[0], dict):
                        imbalance_values = [item['imbalance'] for item in imbalances_list if 'imbalance' in item]
                    else:
                        imbalance_values = imbalances_list
                    
                    if imbalance_values:
                        imbalances = np.array(imbalance_values)
                        self.baseline_imbalance_std = float(np.std(imbalances))
                        print(f"   ⚖️  Baseline imbalance volatility: {self.baseline_imbalance_std:.4f}")
            
            if learning_stats.get('mid_prices') and len(learning_stats['mid_prices']) > 1:
                prices = np.array(learning_stats['mid_prices'])
                price_changes = np.diff(prices) / prices[:-1]
                self.baseline_volatility = float(np.std(price_changes))
                print(f"   📊 Baseline price volatility: {self.baseline_volatility:.6f}")
                
        except Exception as e:
            print(f"❌ Error updating baselines: {e}")
            import traceback
            traceback.print_exc()
            self.logger.error(f"Error updating baselines: {e}")
    
    def analyze_orderbook(self, orderbook: Dict) -> Tuple[OrderbookImbalance, OrderbookGaps, LiquidityProfile, MarketCondition]:
        """Comprehensive orderbook analysis"""
        
        # Extract basic data
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        mid_price = orderbook.get('mid_price', 0)
        spread_pct = orderbook.get('spread_pct', 0)
        
        if not bids or not asks or mid_price == 0:
            return self._empty_analysis()
        
        # 1. Analyze imbalance
        imbalance = self._analyze_imbalance(bids, asks, mid_price)
        
        # 2. Find gaps in the orderbook
        gaps = self._find_orderbook_gaps(bids, asks, mid_price)
        
        # 3. Analyze liquidity profile
        liquidity = self._analyze_liquidity_profile(bids, asks, mid_price)
        
        # 4. Classify market condition
        condition = self._classify_market_condition(spread_pct, imbalance, liquidity)
        
        # Update historical data
        self.spread_history.append(spread_pct)
        self.imbalance_history.append(imbalance.imbalance_ratio)
        self.price_history.append(mid_price)
        
        return imbalance, gaps, liquidity, condition
    
    def _analyze_imbalance(self, bids: List[List[float]], asks: List[List[float]], mid_price: float) -> OrderbookImbalance:
        """Analyze orderbook volume imbalance"""
        
        # Calculate imbalance at different depths
        depth_levels = [3, 5, 10, 20]  # number of levels to analyze
        imbalances = {}
        
        for depth in depth_levels:
            bid_vol = sum(bid[1] for bid in bids[:depth])
            ask_vol = sum(ask[1] for ask in asks[:depth])
            
            if bid_vol + ask_vol > 0:
                imbalances[depth] = (bid_vol - ask_vol) / (bid_vol + ask_vol)
            else:
                imbalances[depth] = 0.0
        
        # Use 5-level imbalance as primary
        primary_imbalance = imbalances.get(5, 0.0)
        
        # Calculate volume-weighted mid price
        if len(bids) > 0 and len(asks) > 0:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            bid_vol = sum(bid[1] for bid in bids[:5])
            ask_vol = sum(ask[1] for ask in asks[:5])
            
            if bid_vol + ask_vol > 0:
                weighted_mid = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)
            else:
                weighted_mid = mid_price
        else:
            weighted_mid = mid_price
        
        return OrderbookImbalance(
            bid_volume=sum(bid[1] for bid in bids[:10]),
            ask_volume=sum(ask[1] for ask in asks[:10]),
            imbalance_ratio=primary_imbalance,
            depth_ratio=imbalances.get(10, 0.0),
            weighted_mid=weighted_mid
        )
    
    def _find_orderbook_gaps(self, bids: List[List[float]], asks: List[List[float]], mid_price: float) -> OrderbookGaps:
        """Find gaps in orderbook that represent good order placement opportunities"""
        
        bid_gaps = []
        ask_gaps = []
        
        # Analyze bid side gaps
        for i in range(len(bids) - 1):
            current_price = bids[i][0]
            next_price = bids[i + 1][0]
            gap_size = current_price - next_price
            
            # Only consider significant gaps (> 0.1% of mid price)
            if gap_size > mid_price * 0.001:
                bid_gaps.append((current_price - gap_size/2, gap_size))
        
        # Analyze ask side gaps
        for i in range(len(asks) - 1):
            current_price = asks[i][0]
            next_price = asks[i + 1][0]
            gap_size = next_price - current_price
            
            # Only consider significant gaps
            if gap_size > mid_price * 0.001:
                ask_gaps.append((current_price + gap_size/2, gap_size))
        
        # Find largest gaps
        largest_bid_gap = max(bid_gaps, key=lambda x: x[1]) if bid_gaps else (0, 0)
        largest_ask_gap = max(ask_gaps, key=lambda x: x[1]) if ask_gaps else (0, 0)
        
        return OrderbookGaps(
            bid_gaps=bid_gaps,
            ask_gaps=ask_gaps,
            largest_bid_gap=largest_bid_gap,
            largest_ask_gap=largest_ask_gap
        )
    
    def _analyze_liquidity_profile(self, bids: List[List[float]], asks: List[List[float]], mid_price: float) -> LiquidityProfile:
        """Analyze liquidity distribution in the orderbook"""
        
        distance_thresholds = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]  # 0.1%, 0.2%, 0.5%, 1%, 2%, 5%
        
        bid_depth_at_distances = {}
        ask_depth_at_distances = {}
        
        # Calculate cumulative volume at different distances
        for threshold in distance_thresholds:
            price_threshold_bid = mid_price * (1 - threshold)
            price_threshold_ask = mid_price * (1 + threshold)
            
            bid_volume = sum(bid[1] for bid in bids if bid[0] >= price_threshold_bid)
            ask_volume = sum(ask[1] for ask in asks if ask[0] <= price_threshold_ask)
            
            bid_depth_at_distances[threshold] = bid_volume
            ask_depth_at_distances[threshold] = ask_volume
        
        # Calculate liquidity concentration (how much is in top 3 levels vs total)
        total_bid_vol = sum(bid[1] for bid in bids)
        total_ask_vol = sum(ask[1] for ask in asks)
        top3_bid_vol = sum(bid[1] for bid in bids[:3])
        top3_ask_vol = sum(ask[1] for ask in asks[:3])
        
        if total_bid_vol > 0 and total_ask_vol > 0:
            concentration = (top3_bid_vol / total_bid_vol + top3_ask_vol / total_ask_vol) / 2
        else:
            concentration = 0.0
        
        return LiquidityProfile(
            total_bid_liquidity=total_bid_vol,
            total_ask_liquidity=total_ask_vol,
            bid_depth_at_distances=bid_depth_at_distances,
            ask_depth_at_distances=ask_depth_at_distances,
            liquidity_concentration=concentration
        )
    
    def _classify_market_condition(self, spread_pct: float, imbalance: OrderbookImbalance, liquidity: LiquidityProfile) -> MarketCondition:
        """Classify current market condition"""
        
        # Calculate spread volatility
        spread_volatility = 0.0
        if len(self.spread_history) > 10:
            recent_spreads = list(self.spread_history)[-20:]
            spread_volatility = np.std(recent_spreads)
        
        # Calculate book stability (low volatility in imbalance = stable)
        book_stability = 1.0
        if len(self.imbalance_history) > 10:
            recent_imbalances = list(self.imbalance_history)[-20:]
            imbalance_volatility = np.std(recent_imbalances)
            if self.baseline_imbalance_std and self.baseline_imbalance_std > 0:
                stability_ratio = imbalance_volatility / self.baseline_imbalance_std
                book_stability = max(0.0, min(1.0, 2.0 - stability_ratio))
        
        # Calculate trade frequency (placeholder - would need trade timestamps)
        trade_frequency = 1.0  # Default value
        
        # Classify condition
        condition_type = "UNKNOWN"
        confidence = 0.5
        
        if self.baseline_spread:
            spread_percentile = self._calculate_percentile(spread_pct, self.baseline_spread)
            
            # CALM: tight spreads, stable book, balanced
            if (spread_percentile < 50 and 
                book_stability > 0.7 and 
                abs(imbalance.imbalance_ratio) < 0.3):
                condition_type = "CALM"
                confidence = 0.8
            
            # TRENDING: imbalanced book, moderate spreads
            elif (abs(imbalance.imbalance_ratio) > 0.5 and 
                  spread_percentile < 75 and 
                  book_stability > 0.5):
                condition_type = "TRENDING" 
                confidence = 0.7
            
            # VOLATILE: wide spreads, unstable book
            elif (spread_percentile > 80 or 
                  book_stability < 0.4):
                condition_type = "VOLATILE"
                confidence = 0.8
            
            # ILLIQUID: very wide spreads, thin book
            elif (spread_percentile > 95 or 
                  liquidity.total_bid_liquidity + liquidity.total_ask_liquidity < 10):
                condition_type = "ILLIQUID"
                confidence = 0.9
            
            else:
                condition_type = "NORMAL"
                confidence = 0.6
        
        return MarketCondition(
            spread_pct=spread_pct,
            spread_volatility=spread_volatility,
            book_stability=book_stability,
            trade_frequency=trade_frequency,
            condition_type=condition_type,
            confidence=confidence
        )
    
    def calculate_adverse_selection_risk(self, orderbook: Dict, recent_fills: List[Dict] = None) -> AdverseSelectionRisk:
        """Calculate risk of adverse selection"""
        
        spread_pct = orderbook.get('spread_pct', 0)
        
        # 1. Spread percentile risk
        spread_percentile = 50.0  # Default
        if self.baseline_spread:
            spread_percentile = self._calculate_percentile(spread_pct, self.baseline_spread)
        
        # Tight spreads (low percentile) = higher adverse selection risk
        spread_risk = max(0.0, (50 - spread_percentile) / 50.0)
        
        # 2. Fill rate imbalance
        fill_imbalance = 0.0
        if recent_fills and len(recent_fills) > 5:
            buy_fills = sum(1 for fill in recent_fills if fill.get('side') == 'buy')
            sell_fills = len(recent_fills) - buy_fills
            if len(recent_fills) > 0:
                fill_imbalance = abs(buy_fills - sell_fills) / len(recent_fills)
        
        # 3. Price impact risk (rapid price changes)
        price_impact_risk = 0.0
        if len(self.price_history) > 5:
            recent_prices = list(self.price_history)[-5:]
            if len(recent_prices) > 1:
                price_changes = np.diff(recent_prices) / recent_prices[:-1]
                recent_volatility = np.std(price_changes)
                if self.baseline_volatility and self.baseline_volatility > 0:
                    price_impact_risk = min(1.0, recent_volatility / self.baseline_volatility / 2.0)
        
        # 4. Informed trader signals (placeholder)
        informed_signals = 0.0
        
        # Combine risks
        overall_risk = (spread_risk * 0.4 + 
                       fill_imbalance * 0.3 + 
                       price_impact_risk * 0.3)
        
        return AdverseSelectionRisk(
            spread_percentile=spread_percentile,
            fill_rate_imbalance=fill_imbalance,
            price_impact_risk=price_impact_risk,
            informed_trader_signals=informed_signals,
            overall_risk=overall_risk
        )
    
    def should_place_orders(self, market_condition: MarketCondition, adverse_risk: AdverseSelectionRisk) -> bool:
        """Determine if conditions are favorable for order placement"""
        
        # Don't trade in illiquid or highly volatile conditions
        if market_condition.condition_type in ['ILLIQUID', 'VOLATILE']:
            print(f"❌ Unfavorable market condition: {market_condition.condition_type}")
            return False
        
        # Don't trade with high adverse selection risk
        if adverse_risk.overall_risk > 0.8:
            print(f"❌ High adverse selection risk: {adverse_risk.overall_risk:.3f}")
            return False
        
        # Don't trade if spread is abnormally tight (informed trader warning)
        if adverse_risk.spread_percentile < 10:
            print(f"❌ Abnormally tight spread (percentile: {adverse_risk.spread_percentile:.1f})")
            return False
        
        print(f"✅ Conditions favorable: {market_condition.condition_type}, risk: {adverse_risk.overall_risk:.3f}")
        return True
    
    def calculate_smart_fair_price(self, orderbook: Dict, imbalance: OrderbookImbalance) -> float:
        """Calculate fair price using advanced orderbook analysis"""
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 0.0
        
        # Start with volume-weighted mid price
        fair_price = imbalance.weighted_mid
        
        # Adjust for persistent imbalance
        if abs(imbalance.imbalance_ratio) > 0.3:
            # If there's strong bid pressure, fair price should be higher
            adjustment = imbalance.imbalance_ratio * orderbook.get('spread', 0) * 0.3
            fair_price += adjustment
            print(f"   📊 Imbalance adjustment: {adjustment:.5f} (imbalance: {imbalance.imbalance_ratio:.3f})")
        
        return fair_price
    
    def find_optimal_order_prices(self, orderbook: Dict, gaps: OrderbookGaps, fair_price: float) -> Tuple[float, float]:
        """Find optimal bid/ask prices using gap analysis"""
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        tick_size = orderbook.get('tick_size', 0.5)
        
        if not bids or not asks:
            return fair_price * 0.999, fair_price * 1.001
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        
        # Default to slightly inside the spread
        target_bid = best_bid + tick_size
        target_ask = best_ask - tick_size
        
        # Use gaps if they're significant and close to fair price
        if gaps.largest_bid_gap[1] > tick_size * 3:  # Gap is significant
            gap_price = gaps.largest_bid_gap[0]
            if abs(gap_price - fair_price) / fair_price < 0.005:  # Within 0.5% of fair
                target_bid = gap_price
                print(f"   🎯 Using bid gap at ${gap_price:.5f}")
        
        if gaps.largest_ask_gap[1] > tick_size * 3:
            gap_price = gaps.largest_ask_gap[0]
            if abs(gap_price - fair_price) / fair_price < 0.005:
                target_ask = gap_price
                print(f"   🎯 Using ask gap at ${gap_price:.5f}")
        
        # Ensure prices don't cross the spread
        target_bid = min(target_bid, best_ask - tick_size)
        target_ask = max(target_ask, best_bid + tick_size)
        
        return target_bid, target_ask
    
    def _calculate_percentile(self, value: float, baseline: Dict) -> float:
        """Calculate percentile of value within baseline distribution"""
        percentiles = baseline.get('percentiles', {})
        
        if value <= percentiles.get('25', 0):
            return 25.0
        elif value <= percentiles.get('50', 0):
            return 37.5
        elif value <= percentiles.get('75', 0):
            return 62.5
        elif value <= percentiles.get('90', 0):
            return 82.5
        elif value <= percentiles.get('95', 0):
            return 92.5
        else:
            return 97.5
    
    def _empty_analysis(self):
        """Return empty analysis objects"""
        return (
            OrderbookImbalance(0, 0, 0, 0, 0),
            OrderbookGaps([], [], (0, 0), (0, 0)),
            LiquidityProfile(0, 0, {}, {}, 0),
            MarketCondition(0, 0, 0, 0, "UNKNOWN", 0)
        )
    
    def get_analysis_summary(self, imbalance: OrderbookImbalance, condition: MarketCondition, adverse_risk: AdverseSelectionRisk) -> str:
        """Get human-readable analysis summary"""
        return (f"Condition: {condition.condition_type} | "
                f"Imbalance: {imbalance.imbalance_ratio:.3f} | "
                f"Stability: {condition.book_stability:.2f} | "
                f"Risk: {adverse_risk.overall_risk:.3f}")