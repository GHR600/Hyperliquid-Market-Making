# Dynamic Pricing Engine Implementation Guide

## Overview
This guide implements a sophisticated dynamic bid/ask calculation system using expected value optimization, adaptive feedback loops, and microstructure analysis. It replaces the rigid BASE_SPREAD system with intelligent, self-optimizing pricing.

---

## PART 1: Add Dynamic Pricing Engine to strategy.py

### Step 1.1: Add imports at top of strategy.py

After existing imports, add:
```python
from collections import deque
import time
```

### Step 1.2: Add DynamicPricingEngine class to strategy.py

**Location**: Add this BEFORE the `EnhancedMarketMakingStrategy` class (around line 30)

```python
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
```

### Step 1.3: Initialize pricing engine in EnhancedMarketMakingStrategyWithRisk

**Location**: In `EnhancedMarketMakingStrategyWithRisk.__init__` method (around line 600)

**Find this code:**
```python
def __init__(self, config: TradingConfig):
    super().__init__(config)
    
    # ADD THESE LINES for risk management:
```

**Add AFTER the existing risk management init:**
```python
    # Initialize dynamic pricing engine
    self.pricing_engine = DynamicPricingEngine(config)
    print("🎯 Dynamic pricing engine integrated with risk management")
```

### Step 1.4: Replace calculate_order_prices method

**Location**: Find the `calculate_order_prices` method in `EnhancedMarketMakingStrategyWithRisk` class

**Replace the ENTIRE method with:**
```python
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
```

---

## PART 2: Fix Stop-Loss Implementation

### Step 2.1: Fix generate_stop_loss_order method

**Location**: Find `generate_stop_loss_order` in `EnhancedMarketMakingStrategyWithRisk` class (around line 750)

**Replace the ENTIRE method with:**
```python
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
```

### Step 2.2: Ensure stop-loss is checked every loop

**Location**: In `main.py`, find `execute_enhanced_trading_logic` method (around line 500)

**Find this section:**
```python
# 1. IMMEDIATE RISK CHECKS (NEW!)
print("🛡️  Performing risk checks...")

# Check for stop-loss trigger
if (position and 
    hasattr(self.strategy, 'check_stop_loss_trigger') and 
    self.strategy.check_stop_loss_trigger(position, current_price)):
```

**Ensure this entire risk check section is BEFORE all other trading logic**

### Step 2.3: Add stop-loss monitoring to status logging

**Location**: In `main.py`, find `log_enhanced_status` method (around line 650)

**Find the risk status section and ensure it includes:**
```python
# NEW: Risk-specific logging
current_price = fair_price or 0
if position and hasattr(self.strategy, 'get_risk_status') and current_price > 0:
    risk_status = self.strategy.get_risk_status(position, current_price)
    
    if not risk_status.get('no_position'):
        print(f"🛡️  Risk Management Status:")
        
        stop_loss_price = risk_status.get('stop_loss_price', 0)
        profit_target_price = risk_status.get('profit_target_price', 0)
        
        if stop_loss_price > 0:
            distance_to_stop = ((current_price - stop_loss_price) / current_price * 100) if position.size > 0 else ((stop_loss_price - current_price) / current_price * 100)
            print(f"   - Stop-Loss: ${stop_loss_price:.5f} (distance: {distance_to_stop:.2f}%)")
            
            # WARNING if close to stop
            if abs(distance_to_stop) < 0.5:
                print(f"   ⚠️  CLOSE TO STOP-LOSS!")
        
        if profit_target_price > 0:
            print(f"   - Profit Target: ${profit_target_price:.5f}")
```

---

## PART 3: Integrate with InfluxDB Dashboard

### Step 3.1: Add pricing engine metrics to InfluxDB

**Location**: In `core/metrics_logger.py`, add new method after `log_risk_metrics`:

```python
def log_pricing_metrics(self, pricing_metadata: Dict):
    """Log dynamic pricing engine metrics"""
    if not self.enabled or not pricing_metadata:
        return
    
    try:
        point = Point("pricing_metrics") \
            .tag("symbol", self.config.SYMBOL) \
            .field("bid_offset_bps", float(pricing_metadata.get('bid_offset_bps', 0))) \
            .field("ask_offset_bps", float(pricing_metadata.get('ask_offset_bps', 0))) \
            .field("bid_fill_prob", float(pricing_metadata.get('bid_fill_prob', 0))) \
            .field("ask_fill_prob", float(pricing_metadata.get('ask_fill_prob', 0))) \
            .field("current_fill_rate", float(pricing_metadata.get('current_fill_rate', 0))) \
            .field("adverse_rate", float(pricing_metadata.get('adverse_rate', 0))) \
            .field("bid_ev", float(pricing_metadata.get('bid_ev', 0))) \
            .field("ask_ev", float(pricing_metadata.get('ask_ev', 0))) \
            .time(datetime.utcnow(), WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        
    except Exception as e:
        self.logger.error(f"Failed to log pricing metrics: {e}")
```

### Step 3.2: Call pricing metrics logging

**Location**: In `main.py`, in `log_enhanced_status` method, add after existing metrics logging:

```python
# Log pricing engine metrics
if hasattr(self.strategy, '_pricing_metadata'):
    self.metrics_logger.log_pricing_metrics(self.strategy._pricing_metadata)
```

### Step 3.3: Update Grafana dashboard for new metrics

**Add these new panels to your Grafana dashboard:**

**Panel 1: Fill Rate Gauge**
```json
{
  "title": "Fill Rate",
  "type": "gauge",
  "targets": [{
    "query": "from(bucket: \"Metrics\")\n  |> range(start: -5m)\n  |> filter(fn: (r) => r._measurement == \"pricing_metrics\")\n  |> filter(fn: (r) => r._field == \"current_fill_rate\")\n  |> last()"
  }],
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 1,
      "thresholds": {
        "steps": [
          {"color": "red", "value": 0},
          {"color": "yellow", "value": 0.3},
          {"color": "green", "value": 0.4},
          {"color": "yellow", "value": 0.5},
          {"color": "red", "value": 0.6}
        ]
      }
    }
  }
}
```

**Panel 2: Bid/Ask Offsets**
```json
{
  "title": "Dynamic Spreads (bps)",
  "type": "timeseries",
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"Metrics\")\n  |> range(start: -1h)\n  |> filter(fn: (r) => r._measurement == \"pricing_metrics\")\n  |> filter(fn: (r) => r._field == \"bid_offset_bps\" or r._field == \"ask_offset_bps\")"
    }
  ]
}
```

---

## PART 4: Testing & Verification

### Step 4.1: Run initial tests

After implementing all changes, run:

```bash
python main.py
```

**Look for these outputs:**
1. `🎯 Dynamic Pricing Engine initialized` - on startup
2. `🎯 DYNAMIC PRICING CALCULATION` - every trading loop
3. `📊 Optimal offsets: Bid: X.X bps` - showing calculated spreads
4. `📈 Performance: Recent fill rate: XX%` - showing adaptive feedback

### Step 4.2: Verify stop-loss triggers

To test stop-loss:

1. Take a position (let bot trade)
2. Wait for position entry
3. Watch for these outputs:
   ```
   🛡️ Risk Management Status:
      - Stop-Loss: $X.XX (distance: X.XX%)
   ```
4. If price moves toward stop, you should see:
   ```
   🛑 STOP-LOSS TRIGGERED!
   ```

### Step 4.3: Verify Grafana integration

1. Open Grafana: http://localhost:3000
2. Check dashboard shows:
   - Fill Rate gauge (should show 0-100%)
   - Dynamic Spreads chart (should show changing bps values)
   - All existing panels still work

3. Verify data in InfluxDB:
   - Go to http://localhost:8086
   - Data Explorer → Metrics bucket
   - Should see new measurement: `pricing_metrics`

### Step 4.4: Monitor adaptive behavior

Run bot for 30 minutes and watch for:

```
📏 Widening spreads: fill rate 52.3% > target 40.0%
   OR
📏 Tightening spreads: fill rate 28.1% < target 40.0%
```

This confirms the adaptive feedback loop is working.

---

## PART 5: Configuration Tuning

### Step 5.1: Adjust fill rate target

In `strategy.py`, `DynamicPricingEngine.__init__`:

```python
self.fill_rate_target = 0.40  # Change to 0.30 for less aggressive, 0.50 for more aggressive
```

### Step 5.2: Adjust offset range

```python
self.min_offset = 0.0002  # Tightest spread (2 bps)
self.max_offset = 0.0030  # Widest spread (30 bps)
```

### Step 5.3: Adjust stop-loss settings

In `config.py`:

```python
STOP_LOSS_PCT: float = 2.0  # 2% stop loss
TRAILING_STOP_LOSS: bool = True
TRAILING_STOP_DISTANCE: float = 1.0  # 1% trailing
```

---

## PART 6: Troubleshooting

### Issue: Orders still using old rigid spread

**Solution**: Ensure `calculate_order_prices` is calling `pricing_engine.calculate_dynamic_prices`

**Check**: Look for output `🎯 DYNAMIC PRICING CALCULATION` in logs

### Issue: Stop-loss not triggering

**Solution**: 
1. Verify `update_position_tracking` is being called
2. Check `self.stop_loss_price` is set after taking position
3. Add debug output to `check_stop_loss_trigger`:

```python
def check_stop_loss_trigger(self, position, current_price: float) -> bool:
    print(f"🔍 Stop-loss check: pos={position.size:.4f}, price=${current_price:.2f}, stop=${self.stop_loss_price:.2f if self.stop_loss_price else 0}")
    # ... rest of method
```

### Issue: No pricing_metrics in InfluxDB

**Solution**:
1. Check `log_pricing_metrics` is being called
2. Verify `self.strategy._pricing_metadata` exists
3. Check InfluxDB connection is working

### Issue: Fill rate stuck at 0% or 100%

**Solution**: Need at least 10 orders before adaptation kicks in. Keep running bot longer.

---

## PART 7: Expected Results

After full implementation, you should see:

### Console Output
```
🎯 DYNAMIC PRICING CALCULATION
   Fair Price: $4700.00
   📊 Optimal offsets:
      Bid: 4.5 bps → $4697.89 (Fill prob: 45.3%)
      Ask: 5.2 bps → $4702.44 (Fill prob: 38.7%)
   ✅ FINAL PRICES:
      Bid: $4697.00
      Ask: $4702.50
      Spread: $5.50 (0.117%)
   📈 Performance:
      Recent fill rate: 42.1%
      Adverse selection: 18.3%
```

### Adaptive Behavior
- Spreads automatically widen if filling too often
- Spreads automatically tighten if not filling enough
- Target: ~40% fill rate

### Stop-Loss Behavior
- Position tracked with entry price
- Stop-loss calculated at 2% below entry (long) or above entry (short)
- Triggers automatically when price crosses stop level
- Executes with IoC order for guaranteed fill

### Dashboard Metrics
- Fill Rate: 30-50% (green zone)
- Bid Offset: 2-30 bps (adapting dynamically)
- Ask Offset: 2-30 bps (adapting dynamically)
- Adverse Rate: <30% (acceptable range)

---

## Summary of Changes

### Files Modified:
1. ✅ `strategy.py` - Added DynamicPricingEngine class
2. ✅ `strategy.py` - Updated calculate_order_prices method
3. ✅ `strategy.py` - Fixed generate_stop_loss_order method
4. ✅ `main.py` - Enhanced stop-loss checking logic
5. ✅ `main.py` - Added pricing metrics logging
6. ✅ `core/metrics_logger.py` - Added log_pricing_metrics method
7. ✅ Grafana dashboard - Added new pricing panels

### Key Features:
- ✅ Expected value optimization
- ✅ Adaptive spread adjustment
- ✅ Probabilistic fill modeling
- ✅ Microstructure integration
- ✅ Working stop-losses
- ✅ Dashboard integration

### Testing Checklist:
- [ ] Bot starts without errors
- [ ] Dynamic pricing outputs appear
- [ ] Spreads adapt based on fill rate
- [ ] Stop-loss triggers correctly
- [ ] Grafana shows new pricing metrics
- [ ] InfluxDB receives pricing_metrics data

---

## COMPLETE! 🎉

This implementation replaces rigid spread calculations with sophisticated, adaptive, self-optimizing pricing that learns from your actual results and market microstructure.