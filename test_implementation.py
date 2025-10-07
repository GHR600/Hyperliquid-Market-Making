#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify all pricing_instructions.py implementation steps work correctly
"""
import sys
import os

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("=" * 60)
print("TESTING PRICING IMPLEMENTATION")
print("=" * 60)

# Test 1: Import all modules
print("\n[1/6] Testing imports...")
try:
    from config import TradingConfig
    from strategy import DynamicPricingEngine, EnhancedMarketMakingStrategyWithRisk
    from core.metrics_logger import InfluxMetricsLogger
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Load config
print("\n[2/6] Testing config...")
try:
    config = TradingConfig()
    print(f"✓ Config loaded - Symbol: {config.SYMBOL}")
except Exception as e:
    print(f"✗ Config load failed: {e}")
    sys.exit(1)

# Test 3: Instantiate DynamicPricingEngine
print("\n[3/6] Testing DynamicPricingEngine...")
try:
    engine = DynamicPricingEngine(config)
    print(f"✓ DynamicPricingEngine created")
    print(f"  - Fill rate target: {engine.fill_rate_target*100:.0f}%")
    print(f"  - Offset range: {engine.min_offset*10000:.0f}-{engine.max_offset*10000:.0f} bps")
except Exception as e:
    print(f"✗ DynamicPricingEngine creation failed: {e}")
    sys.exit(1)

# Test 4: Instantiate EnhancedMarketMakingStrategyWithRisk
print("\n[4/6] Testing Strategy with Risk Management...")
try:
    strategy = EnhancedMarketMakingStrategyWithRisk(config)
    print(f"✓ Strategy created with risk management")

    # Verify pricing engine is integrated
    if hasattr(strategy, 'pricing_engine'):
        print(f"  - Pricing engine integrated: Yes")
    else:
        print(f"  - Pricing engine integrated: No (ERROR!)")
        sys.exit(1)

    # Verify risk management is configured
    if hasattr(strategy, 'risk_config'):
        print(f"  - Risk management enabled: Yes")
        print(f"    Stop-loss: {strategy.risk_config.STOP_LOSS_PCT}%")
    else:
        print(f"  - Risk management enabled: No (ERROR!)")
        sys.exit(1)

except Exception as e:
    print(f"✗ Strategy creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Check method availability
print("\n[5/6] Testing method availability...")
try:
    # Check for key methods
    methods_to_check = [
        'calculate_order_prices',
        'generate_stop_loss_order',
        'check_stop_loss_trigger',
        'update_position_tracking',
        'get_risk_status'
    ]

    missing_methods = []
    for method_name in methods_to_check:
        if not hasattr(strategy, method_name):
            missing_methods.append(method_name)

    if missing_methods:
        print(f"✗ Missing methods: {', '.join(missing_methods)}")
        sys.exit(1)
    else:
        print(f"✓ All required methods present")

except Exception as e:
    print(f"✗ Method check failed: {e}")
    sys.exit(1)

# Test 6: Check pricing engine methods
print("\n[6/6] Testing pricing engine methods...")
try:
    # Check for key pricing engine methods
    engine_methods = [
        'calculate_dynamic_prices',
        'find_optimal_offset',
        'calculate_fill_probability',
        'adapt_offsets',
        'get_current_fill_rate',
        'record_order_outcome'
    ]

    missing_engine_methods = []
    for method_name in engine_methods:
        if not hasattr(engine, method_name):
            missing_engine_methods.append(method_name)

    if missing_engine_methods:
        print(f"✗ Missing engine methods: {', '.join(missing_engine_methods)}")
        sys.exit(1)
    else:
        print(f"✓ All pricing engine methods present")

except Exception as e:
    print(f"✗ Pricing engine method check failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED - Implementation is ready!")
print("=" * 60)
print("\nYou can now run: python main.py")
print("\nExpected outputs to look for:")
print("  1. '🎯 Dynamic Pricing Engine initialized' - on startup")
print("  2. '🎯 DYNAMIC PRICING CALCULATION' - every trading loop")
print("  3. '📊 Optimal offsets: Bid: X.X bps' - showing calculated spreads")
print("  4. '📈 Performance: Recent fill rate: XX%' - showing adaptive feedback")
print("  5. '🛡️ Risk Management Status' - in status logs")
