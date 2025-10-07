# main_enhanced.py - Complete integration of learning phase + orderbook analysis

import asyncio
import logging
import signal
import time
import numpy as np
from typing import Optional, Dict, List
from config import TradingConfig
from core.data_manager import DataManager
from core.position_tracker import PositionTracker, Order
from strategy import EnhancedMarketMakingStrategyWithRisk
from core.trading_client import TradingClient
from analysis.market_microstructure import MarketMicrostructure
from core.websocket_manager import DataManagerWithWebSocket
from core.metrics_logger import InfluxMetricsLogger
from utils.dynamic_config import DynamicConfig

class EnhancedHyperliquidMarketMaker:
    def __init__(self):
        print("🚀 Initializing Enhanced Hyperliquid Market Maker...")
        print("   🎓 Learning Phase + 📊 Orderbook Analysis + 🧠 Microstructure")
        
        self.config = TradingConfig()
        print(f"   📋 Configuration loaded for {self.config.SYMBOL}")
        
        base_data_manager = DataManager(self.config)
        self.data_manager = DataManagerWithWebSocket(self.config, base_data_manager)
        print("   📊 Data manager with WebSocket initialized")
        
        self.position_tracker = PositionTracker(self.config)
        print("   📈 Position tracker initialized")
        
        # Use enhanced strategy with orderbook analysis
        self.strategy = EnhancedMarketMakingStrategyWithRisk(self.config)
        print("   🎯 Enhanced strategy with orderbook analysis initialized")
        
        self.trading_client = TradingClient(self.config)
        print("   💱 Trading client initialized")
        
        self.microstructure = MarketMicrostructure(self.config)
        print("   🧠 Microstructure analyzer initialized")

        self.metrics_logger = InfluxMetricsLogger(self.config)
        print("   📊 Metrics logger initialized")

        self.dynamic_config = DynamicConfig()
        print("   🔧 Dynamic configuration system initialized")

        # Learning phase state
        self.learning_phase_active = self.config.ENABLE_LEARNING_PHASE
        self.learning_start_time = None
        self.trading_start_time = None
        self.orderbook_snapshots_collected = 0
        self.trade_events_collected = 0
        
        # Enhanced learning phase statistics
        self.learning_stats = {
            'spreads': [],
            'mid_prices': [],
            'trade_sizes': [],
            'imbalances': [],
            'book_stability_samples': [],
            'liquidity_samples': [],
            'first_snapshot_time': None,
            'last_update_time': None
        }
        
        self.running = False
        self.logger = self._setup_logging()
        print("   📝 Logging configured")
        
        if self.config.ENABLE_LEARNING_PHASE:
            print(f"   🎓 Learning phase enabled: {self.config.LEARNING_PHASE_DURATION/60:.1f} minutes")
            print("   📚 Will collect orderbook patterns, spreads, and market conditions")
        else:
            print("   ⚡ Learning phase disabled - will start trading immediately")
        print("")

    def handle_real_time_trades(self, trades: List[Dict]):
        """Handle real-time trade data from WebSocket"""
        if trades:
            if self.learning_phase_active:
                print(f"🎓 Learning: Processing {len(trades)} trades...")
                self.trade_events_collected += len(trades)
                
                # Enhanced trade analysis during learning
                for trade in trades:
                    size = trade.get('size', 0)
                    if size > 0:
                        self.learning_stats['trade_sizes'].append(size)
            else:
                print(f"💹 Trading: Processing {len(trades)} real-time trades...")
                
                # Track fills for adverse selection analysis
                for trade in trades:
                    # This would need to be filtered to only our fills in a real implementation
                    # For now, we'll track all trades as market activity
                    pass
            
            # Always feed to microstructure analyzer
            self.microstructure.add_trade_events(trades)
        
    def handle_real_time_orderbook(self, orderbook: Dict):
        """Handle real-time orderbook data from WebSocket"""
        if orderbook:
            if self.learning_phase_active:
                print(f"🎓 Learning: Processing orderbook update (mid: ${orderbook.get('mid_price', 0):.5f})")
                self._collect_enhanced_learning_data(orderbook)
            else:
                print(f"💹 Trading: Processing orderbook update (mid: ${orderbook.get('mid_price', 0):.5f})")
            
            # Always feed to microstructure analyzer
            self.microstructure.add_orderbook_snapshot(orderbook)
    
    def _collect_enhanced_learning_data(self, orderbook: Dict):
        """Collect enhanced statistics during learning phase"""
        current_time = time.time()
        
        if self.learning_stats['first_snapshot_time'] is None:
            self.learning_stats['first_snapshot_time'] = current_time
        
        self.learning_stats['last_update_time'] = current_time
        self.orderbook_snapshots_collected += 1
        
        # Enhanced data collection
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        mid_price = orderbook.get('mid_price', 0)
        spread_pct = orderbook.get('spread_pct', 0)
        
        if not bids or not asks or mid_price == 0:
            return
        
        # Collect spread data
        if self.config.COLLECT_SPREAD_STATISTICS and spread_pct > 0:
            self.learning_stats['spreads'].append(spread_pct)
        
        # Collect price data
        if self.config.COLLECT_PRICE_MOVEMENT_STATS and mid_price > 0:
            self.learning_stats['mid_prices'].append(mid_price)
        
        # Enhanced volume imbalance analysis
        if self.config.COLLECT_VOLUME_STATISTICS:
            # Multi-level imbalance analysis
            for depth in [3, 5, 10]:
                bid_vol = sum(bid[1] for bid in bids[:depth])
                ask_vol = sum(ask[1] for ask in asks[:depth])
                
                if bid_vol + ask_vol > 0:
                    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
                    self.learning_stats['imbalances'].append({
                        'depth': depth,
                        'imbalance': imbalance,
                        'timestamp': current_time
                    })
        
        # Book stability analysis
        if len(self.learning_stats['mid_prices']) > 5:
            recent_prices = self.learning_stats['mid_prices'][-5:]
            price_volatility = np.std(np.diff(recent_prices) / recent_prices[:-1])
            self.learning_stats['book_stability_samples'].append(price_volatility)
        
        # Liquidity concentration analysis
        total_bid_vol = sum(bid[1] for bid in bids[:20])
        total_ask_vol = sum(ask[1] for ask in asks[:20])
        top3_bid_vol = sum(bid[1] for bid in bids[:3])
        top3_ask_vol = sum(ask[1] for ask in asks[:3])
        
        if total_bid_vol > 0 and total_ask_vol > 0:
            concentration = (top3_bid_vol / total_bid_vol + top3_ask_vol / total_ask_vol) / 2
            self.learning_stats['liquidity_samples'].append(concentration)

    def _check_learning_phase_completion(self) -> bool:
        """Enhanced learning phase completion check"""
        if not self.learning_phase_active:
            return True
        
        current_time = time.time()
        
        # Time-based completion
        if self.learning_start_time:
            elapsed_time = current_time - self.learning_start_time
            if elapsed_time >= self.config.LEARNING_PHASE_DURATION:
                print(f"⏰ Learning phase time limit reached ({elapsed_time/60:.1f} minutes)")
                return True
        
        # Enhanced data requirements
        min_snapshots_met = self.orderbook_snapshots_collected >= self.config.MIN_ORDERBOOK_SNAPSHOTS
        min_trades_met = self.trade_events_collected >= self.config.MIN_TRADE_EVENTS
        min_spread_samples = len(self.learning_stats['spreads']) >= 30
        min_imbalance_samples = len(self.learning_stats['imbalances']) >= 50
        
        data_requirements_met = (min_snapshots_met and min_trades_met and 
                                min_spread_samples and min_imbalance_samples)
        
        if data_requirements_met:
            print(f"📊 Enhanced data requirements met:")
            print(f"   - Snapshots: {self.orderbook_snapshots_collected}")
            print(f"   - Trades: {self.trade_events_collected}")
            print(f"   - Spread samples: {len(self.learning_stats['spreads'])}")
            print(f"   - Imbalance samples: {len(self.learning_stats['imbalances'])}")
        
        return False

    def _end_learning_phase(self):
        """Enhanced learning phase completion with orderbook analysis setup"""
        self.learning_phase_active = False
        self.trading_start_time = time.time()
        
        print("\n" + "=" * 60)
        print("🎓 ENHANCED LEARNING PHASE COMPLETE - COMPREHENSIVE SUMMARY")
        print("=" * 60)
        
        learning_duration = time.time() - self.learning_start_time
        print(f"⏰ Learning duration: {learning_duration/60:.1f} minutes")
        print(f"📊 Data collected:")
        print(f"   - Orderbook snapshots: {self.orderbook_snapshots_collected}")
        print(f"   - Trade events: {self.trade_events_collected}")
        print(f"   - Spread samples: {len(self.learning_stats['spreads'])}")
        print(f"   - Imbalance samples: {len(self.learning_stats['imbalances'])}")
        print(f"   - Liquidity samples: {len(self.learning_stats['liquidity_samples'])}")
        
        # Enhanced spread analysis
        if self.learning_stats['spreads']:
            spreads = np.array(self.learning_stats['spreads'])
            print(f"📈 Enhanced spread analysis:")
            print(f"   - Average spread: {np.mean(spreads):.4f}%")
            print(f"   - Spread range: {np.min(spreads):.4f}% - {np.max(spreads):.4f}%")
            print(f"   - Spread volatility: {np.std(spreads):.4f}%")
            print(f"   - 95th percentile: {np.percentile(spreads, 95):.4f}%")
            print(f"   - 5th percentile: {np.percentile(spreads, 5):.4f}%")
        
        # Trade size analysis
        if self.learning_stats['trade_sizes']:
            sizes = np.array(self.learning_stats['trade_sizes'])
            print(f"💹 Trade size analysis:")
            print(f"   - Average trade size: {np.mean(sizes):.4f}")
            print(f"   - Median trade size: {np.median(sizes):.4f}")
            print(f"   - Large trade threshold (95th): {np.percentile(sizes, 95):.4f}")
            print(f"   - Small trade threshold (25th): {np.percentile(sizes, 25):.4f}")
        
        # Enhanced imbalance analysis
        if self.learning_stats['imbalances']:
            imbalances = [item['imbalance'] for item in self.learning_stats['imbalances']]
            imbalances_array = np.array(imbalances)
            print(f"⚖️  Enhanced imbalance analysis:")
            print(f"   - Average imbalance: {np.mean(imbalances_array):.4f}")
            print(f"   - Imbalance volatility: {np.std(imbalances_array):.4f}")
            print(f"   - Max bid pressure: {np.max(imbalances_array):.4f}")
            print(f"   - Max ask pressure: {np.min(imbalances_array):.4f}")
            print(f"   - Strong imbalance threshold: {np.percentile(np.abs(imbalances_array), 80):.4f}")
        
        # Market stability analysis
        if self.learning_stats['book_stability_samples']:
            stability = np.array(self.learning_stats['book_stability_samples'])
            print(f"📊 Market stability analysis:")
            print(f"   - Average price volatility: {np.mean(stability):.6f}")
            print(f"   - Volatility range: {np.min(stability):.6f} - {np.max(stability):.6f}")
            print(f"   - High volatility threshold: {np.percentile(stability, 80):.6f}")
        
        # Liquidity concentration
        if self.learning_stats['liquidity_samples']:
            concentration = np.array(self.learning_stats['liquidity_samples'])
            print(f"💧 Liquidity analysis:")
            print(f"   - Average concentration: {np.mean(concentration):.3f}")
            print(f"   - Concentration volatility: {np.std(concentration):.3f}")
            print(f"   - High concentration threshold: {np.percentile(concentration, 80):.3f}")
        
        # Price movement analysis
        if self.learning_stats['mid_prices'] and len(self.learning_stats['mid_prices']) > 1:
            prices = np.array(self.learning_stats['mid_prices'])
            price_changes = np.diff(prices) / prices[:-1] * 100
            print(f"💰 Price movement analysis:")
            print(f"   - Price volatility (std): {np.std(price_changes):.4f}%")
            print(f"   - Max price move: {np.max(np.abs(price_changes)):.4f}%")
            print(f"   - 95th percentile move: {np.percentile(np.abs(price_changes), 95):.4f}%")
        
        # Update strategy baselines with learning data
        print(f"\n🎯 Updating strategy baselines...")
        self.strategy.update_baselines_from_learning(self.learning_stats)
        
        # Get microstructure baseline
        signals = self.microstructure.get_current_signals()
        print(f"🧠 Microstructure baseline established:")
        print(f"   - Flow confidence: {signals.flow_confidence:.3f}")
        print(f"   - Overall momentum: {signals.overall_momentum:.3f}")
        print(f"   - Adverse selection risk: {signals.adverse_selection_risk:.3f}")
        print(f"   - Volume imbalance: {signals.volume_imbalance:.3f}")
        
        print(f"\n🚀 ENHANCED MARKET MAKER READY TO TRADE!")
        print(f"   ✅ Orderbook analysis baselines established")
        print(f"   ✅ Adverse selection thresholds calibrated") 
        print(f"   ✅ Dynamic spread calculations ready")
        print(f"   ✅ Smart order placement algorithms active")
        print("=" * 60)
        
        self.logger.info(f"Enhanced learning phase completed. Collected comprehensive market data in {learning_duration/60:.1f} minutes")

    def _log_learning_progress(self):
        """Enhanced learning progress logging"""
        if not self.learning_phase_active or not self.learning_start_time:
            return
        
        elapsed_time = time.time() - self.learning_start_time
        remaining_time = self.config.LEARNING_PHASE_DURATION - elapsed_time
        progress_pct = (elapsed_time / self.config.LEARNING_PHASE_DURATION) * 100
        
        print(f"\n🎓 ENHANCED LEARNING PROGRESS: {progress_pct:.1f}%")
        print(f"   ⏰ Elapsed: {elapsed_time/60:.1f}min | Remaining: {remaining_time/60:.1f}min")
        print(f"   📊 Data collected:")
        print(f"      - Orderbook snapshots: {self.orderbook_snapshots_collected}")
        print(f"      - Trade events: {self.trade_events_collected}")
        print(f"      - Spread samples: {len(self.learning_stats['spreads'])}")
        print(f"      - Imbalance samples: {len(self.learning_stats['imbalances'])}")
        
        # Show current market insights
        if self.learning_stats['spreads']:
            recent_spreads = self.learning_stats['spreads'][-10:]
            avg_recent_spread = np.mean(recent_spreads)
            print(f"   📈 Recent avg spread: {avg_recent_spread:.4f}%")
        
        if self.learning_stats['imbalances']:
            recent_imbalances = [item['imbalance'] for item in self.learning_stats['imbalances'][-10:]]
            avg_recent_imbalance = np.mean(recent_imbalances)
            print(f"   ⚖️  Recent avg imbalance: {avg_recent_imbalance:.3f}")
        
        # Current microstructure signals
        signals = self.microstructure.get_current_signals()
        print(f"   🧠 Current signals: confidence={signals.flow_confidence:.3f}, momentum={signals.overall_momentum:.3f}")

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize all enhanced components"""
        print("=" * 60)
        print("🔧 ENHANCED INITIALIZATION PHASE")
        print("=" * 60)
        
        self.logger.info("Initializing Enhanced Hyperliquid Market Maker...")
        
        # Validate configuration
        if not self.config.PRIVATE_KEY and self.config.ENABLE_TRADING:
            raise ValueError("Private key required for trading")
        
        print("🔍 Validating configuration...")
        if not self.config.PRIVATE_KEY:
            print("⚠️  No private key - running in read-only mode")
        if not self.config.ENABLE_TRADING:
            print("⚠️  Trading disabled - paper trading mode")
        
        print("\n🔌 Initializing data connections...")
        await self.data_manager.initialize()
        
        # Set up real-time callbacks
        print("🔗 Setting up enhanced real-time data callbacks...")
        self.data_manager.set_trade_callback(self.handle_real_time_trades)
        self.data_manager.set_orderbook_callback(self.handle_real_time_orderbook)
        
        # Display symbol-specific parameters
        symbol_info = self.data_manager.get_symbol_info()
        print(f"\n📊 Symbol Configuration:")
        print(f"   🎯 Symbol: {symbol_info['symbol']}")
        print(f"   📏 Size decimals: {symbol_info['size_decimals']}")
        print(f"   💰 Price decimals: {symbol_info['price_decimals']}")
        print(f"   ⚡ Max leverage: {symbol_info['max_leverage']}x")
        print(f"   📊 Max position: {symbol_info['max_position_pct']}x")
        
        # Initialize learning phase if enabled
        if self.config.ENABLE_LEARNING_PHASE:
            self.learning_start_time = time.time()
            print(f"\n🎓 Starting Enhanced Learning Phase ({self.config.LEARNING_PHASE_DURATION/60:.1f} minutes)")
            print("   📚 Collecting comprehensive market microstructure data")
            print("   📊 Analyzing orderbook patterns and liquidity distribution")
            print("   ⚖️  Measuring volume imbalances and spread dynamics")
            print("   🎯 Calibrating adverse selection detection")
        
        print("\n✅ Enhanced initialization complete!")
        print("=" * 60)
        self.logger.info("Enhanced initialization complete")
    
    async def cleanup(self):
        """Cleanup all components"""
        print("\n" + "=" * 60)
        print("🧹 ENHANCED CLEANUP PHASE")
        print("=" * 60)
        
        self.logger.info("Cleaning up enhanced components...")
        await self.data_manager.cleanup()
        print("✅ Enhanced cleanup complete!")
        print("=" * 60)
        self.logger.info("Enhanced cleanup complete")
    
    async def update_positions_and_orders(self):
        """Update position and order information from exchange"""
        if self.learning_phase_active:
            print("🎓 Learning: Updating account state (no trading)")
        else:
            print("\n📊 UPDATING ACCOUNT STATE")
            print("-" * 40)
        
        if not self.trading_client.user_address:
            print("⚠️  No user address - skipping account update")
            return
            
        try:
            # Use MASTER wallet address for account data
            master_address = self.config.MASTER_WALLET_ADDRESS
            
            # Fetch account state
            if not self.learning_phase_active:
                print("💰 Fetching account information...")
            account_info = await self.data_manager.get_account_info(master_address)
            if account_info:
                if not self.learning_phase_active:
                    print("✅ Account info retrieved - updating position tracker")
                self.position_tracker.update_from_account_state(account_info)
            else:
                if not self.learning_phase_active:
                    print("❌ Failed to retrieve account info")
            
            # Use specified account address for order queries
            account_address = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
            
            # Fetch open orders
            if not self.learning_phase_active:
                print("📋 Fetching open orders...")
            
            open_orders = await self.data_manager.get_open_orders(account_address)
            if open_orders is not None:
                if not self.learning_phase_active:
                    print(f"✅ Retrieved {len(open_orders)} open orders")
                self.position_tracker.update_from_open_orders(open_orders)
            else:
                if not self.learning_phase_active:
                    print("❌ Failed to retrieve open orders")
        
        except Exception as e:
            print(f"❌ Error updating positions and orders: {e}")
            self.logger.error(f"Error updating positions and orders: {e}")

    async def update_market_data(self):
        """Update market data with enhanced analysis"""
        if not self.learning_phase_active:
            print("\n📈 UPDATING ENHANCED MARKET DATA")
            print("-" * 40)
        
        try:
            # Fetch orderbook
            if not self.learning_phase_active:
                print("📊 Fetching orderbook for enhanced analysis...")
            orderbook = await self.data_manager.get_orderbook()
            if orderbook:
                if self.learning_phase_active:
                    self._collect_enhanced_learning_data(orderbook)
                else:
                    print("✅ Orderbook retrieved - performing enhanced analysis")
                self.microstructure.add_orderbook_snapshot(orderbook)
            else:
                if not self.learning_phase_active:
                    print("❌ Failed to retrieve orderbook")
                return None
            
            # Fetch recent trades
            if not self.learning_phase_active:
                print("💹 Fetching recent trades for flow analysis...")
            recent_trades = await self.data_manager.get_recent_trades()
            if recent_trades:
                if self.learning_phase_active:
                    self.trade_events_collected += len(recent_trades)
                    for trade in recent_trades:
                        size = trade.get('size', 0)
                        if size > 0:
                            self.learning_stats['trade_sizes'].append(size)
                else:
                    print(f"✅ Retrieved {len(recent_trades)} new trades - updating analysis")
                self.microstructure.add_trade_events(recent_trades)
            else:
                if not self.learning_phase_active:
                    print("📊 No new trades since last update")
            
            return orderbook
                    
        except Exception as e:
            print(f"❌ Error updating enhanced market data: {e}")
            self.logger.error(f"Error updating enhanced market data: {e}")
            return None

    async def execute_enhanced_trading_logic(self, orderbook: Dict):
        """Execute enhanced trading logic with integrated risk management"""
        if self.learning_phase_active:
            # Skip trading during learning phase
            return

        # Check dynamic configuration
        enable_trading = self.dynamic_config.get('enable_trading', True)
        if not enable_trading:
            print("⏸️  Trading DISABLED by dynamic config - skipping trading logic")
            return

        risk_multiplier = self.dynamic_config.get('risk_multiplier', 1.0)
        max_orders_per_side = self.dynamic_config.get('max_orders_per_side', self.config.MAX_ORDERS_PER_SIDE)

        print("\n🎯 EXECUTING ENHANCED TRADING LOGIC WITH RISK MANAGEMENT")
        print("-" * 60)
        print(f"🔧 Dynamic Config: trading={enable_trading}, risk_mult={risk_multiplier:.2f}, max_orders={max_orders_per_side}")

        try:
            current_price = orderbook.get('mid_price', 0)
            position = self.position_tracker.get_position(self.config.SYMBOL)
            
            # 1. IMMEDIATE RISK CHECKS (NEW!)
            print("🛡️  Performing risk checks...")
            
            # Check for stop-loss trigger
            if (position and 
                hasattr(self.strategy, 'check_stop_loss_trigger') and 
                self.strategy.check_stop_loss_trigger(position, current_price)):
                
                print("🛑 STOP-LOSS TRIGGERED - Generating emergency exit order")
                stop_order = self.strategy.generate_stop_loss_order(position, current_price)
                if stop_order:
                    # Execute stop-loss immediately
                    order_ids = await self.trading_client.place_orders([stop_order])
                    if order_ids and order_ids[0]:
                        print(f"✅ Stop-loss order placed: {order_ids[0]}")
                        # Update position tracker to reflect closure
                        self.position_tracker.positions[self.config.SYMBOL] = None
                    else:
                        print("❌ Failed to place stop-loss order!")
                    return  # Skip normal trading logic
            
            # Check for profit-taking (NEW!)
            if (position and 
                hasattr(self.strategy, 'check_profit_taking_trigger')):
                close_size = self.strategy.check_profit_taking_trigger(position, current_price)
                if close_size:
                    print("💰 PROFIT-TAKING TRIGGERED")
                    profit_order = self.strategy.generate_profit_taking_order(position, current_price)
                    if profit_order:
                        order_ids = await self.trading_client.place_orders([profit_order])
                        if order_ids and order_ids[0]:
                            print(f"✅ Profit-taking order placed: {order_ids[0]}")
                            # Reduce position size in tracker
                            if position:
                                position.size -= close_size if position.size > 0 else -close_size
                    # Continue with normal logic after profit-taking
            
            # 2. GET MARKET ANALYSIS (existing code)
            print("🧠 Retrieving microstructure signals...")
            signals = self.microstructure.get_current_signals()
            signal_summary = self.microstructure.get_signal_summary()
            print(f"📊 Microstructure signals: {signal_summary}")
            
            # Get enhanced strategy status
            strategy_status = self.strategy.get_strategy_status(orderbook)
            print(f"📈 Enhanced strategy status:")
            print(f"   - Market condition: {strategy_status.get('condition_type', 'UNKNOWN')}")
            print(f"   - Adverse risk: {strategy_status.get('adverse_risk', 0):.3f}")
            
            # 3. DISPLAY RISK STATUS (NEW!)
            if hasattr(self.strategy, 'get_risk_status'):
                risk_status = self.strategy.get_risk_status(position, current_price)
                if risk_status.get('no_position'):
                    print("📊 Risk Status: FLAT POSITION")
                else:
                    print(f"🛡️  Risk Status:")
                    
                    # Safe formatting with null checks
                    pos_size = risk_status.get('position_size', 0)
                    entry_price = risk_status.get('entry_price', 0)
                    unrealized_pnl = risk_status.get('unrealized_pnl', 0)
                    stop_loss_price = risk_status.get('stop_loss_price', 0)
                    profit_target_price = risk_status.get('profit_target_price', 0)
                    stop_distance = risk_status.get('stop_loss_distance', 0)
                    profit_levels_hit = risk_status.get('profit_levels_hit', [])
                    
                    print(f"   - Position: {pos_size:.4f}")
                    if entry_price > 0:
                        print(f"   - Entry: ${entry_price:.5f}")
                    else:
                        print(f"   - Entry: Not tracked")
                        
                    print(f"   - Unrealized PnL: ${unrealized_pnl:.2f}")
                    
                    if stop_loss_price > 0:
                        print(f"   - Stop-loss: ${stop_loss_price:.5f}")
                        print(f"   - Distance to stop: {stop_distance:.2f}%")
                    else:
                        print(f"   - Stop-loss: Not set")
                        
                    if profit_target_price > 0:
                        print(f"   - Profit target: ${profit_target_price:.5f}")
                    else:
                        print(f"   - Profit target: Not set")
                        
                    if profit_levels_hit:
                        print(f"   - Profit levels hit: {profit_levels_hit}")
            
            # 4. EXISTING TRADING LOGIC (mostly unchanged)
            current_orders = self.position_tracker.get_open_orders(self.config.SYMBOL)
            print(f"📋 Current state: {len(current_orders)} open orders")
            if position:
                print(f"📊 Position: {position.size:.4f} {self.config.SYMBOL}")
            else:
                print("📊 No position")
            
            # Calculate fair price with recent trades for flow adjustment
            recent_trades_list = list(self.microstructure.trade_history) if hasattr(self.microstructure, 'trade_history') else []
            # Convert TradeEvent objects to dicts for strategy consumption
            recent_trades_dicts = [
                {'price': t.price, 'size': t.size, 'side': 'B' if t.is_aggressive_buy else 'A', 'timestamp': t.timestamp}
                for t in recent_trades_list
            ] if recent_trades_list else []

            fair_price = self.strategy.calculate_fair_price(orderbook, recent_trades_dicts)
            if not fair_price:
                print("❌ Cannot determine fair price - skipping trading logic")
                return
            
            # Enhanced order cancellation
            if current_orders and fair_price:
                print("🔍 Enhanced order evaluation...")
                orders_to_cancel = self.strategy.should_cancel_orders(current_orders, fair_price, signals)
                
                if orders_to_cancel:
                    print(f"❌ Cancelling {len(orders_to_cancel)} orders...")
                    success = await self.trading_client.cancel_orders(orders_to_cancel)
                    if success:
                        print("✅ Orders cancelled successfully")
                        for order_id in orders_to_cancel:
                            if order_id in self.position_tracker.open_orders:
                                order = self.position_tracker.open_orders[order_id]
                                # Log cancellation event
                                self.metrics_logger.log_order_event(
                                    event_type='cancelled',
                                    side='buy' if order.side == 'B' else 'sell',
                                    price=float(order.limit_px),
                                    size=float(order.sz),
                                    order_id=order_id
                                )
                                del self.position_tracker.open_orders[order_id]
                    else:
                        print("❌ Failed to cancel some orders")
            
            # Generate new orders with risk management (UPDATED!)
            max_total_orders = max_orders_per_side * 2
            current_order_count = len(current_orders)

            print(f"📊 Order capacity: {current_order_count}/{max_total_orders}")

            if current_order_count < max_total_orders:
                print("🎯 Generating enhanced orders with risk management...")
                account_value = self.position_tracker.get_account_value()

                # Apply risk multiplier to account value for sizing
                adjusted_account_value = account_value * risk_multiplier

                # Use risk-aware order generation (NEW!)
                if hasattr(self.strategy, 'generate_enhanced_orders_with_risk'):
                    new_orders = self.strategy.generate_enhanced_orders_with_risk(
                        orderbook, position, adjusted_account_value, signals
                    )
                else:
                    # Fallback to normal order generation
                    new_orders = self.strategy.generate_orders(orderbook, position, adjusted_account_value, signals)
                
                if new_orders:
                    print(f"📦 Placing {len(new_orders)} risk-managed orders...")
                    order_ids = await self.trading_client.place_orders(new_orders)
                    
                    # Track successful orders
                    successful_orders = 0
                    for i, order_id in enumerate(order_ids):
                        if order_id and i < len(new_orders):
                            order_data = {
                                'oid': order_id,
                                'coin': new_orders[i]['coin'],
                                'side': 'B' if new_orders[i]['is_buy'] else 'A',
                                'sz': str(new_orders[i]['sz']),
                                'limitPx': str(new_orders[i].get('limit_px', 0))
                            }
                            order = Order(order_data)
                            self.position_tracker.open_orders[order_id] = order
                            successful_orders += 1
                            print(f"   ✅ Tracking risk-managed order: {order_id}")

                            # Log order event to InfluxDB
                            self.metrics_logger.log_order_event(
                                event_type='placed',
                                side='buy' if new_orders[i]['is_buy'] else 'sell',
                                price=float(new_orders[i].get('limit_px', 0)),
                                size=float(new_orders[i]['sz']),
                                order_id=order_id
                            )

                    print(f"📈 Successfully placed {successful_orders}/{len(new_orders)} risk-managed orders")
                else:
                    print("⚠️  No orders generated (risk management or unfavorable conditions)")
            else:
                print("📊 Maximum orders reached - not generating new orders")
        
        except Exception as e:
            print(f"❌ Error in enhanced trading logic with risk: {e}")
            self.logger.error(f"Error in enhanced trading logic with risk: {e}")


    async def log_enhanced_status(self, fair_price: Optional[float]):
        """Enhanced status logging with risk metrics"""
        if self.learning_phase_active:
            self._log_learning_progress()
            return

        print("\n📊 ENHANCED STATUS REPORT WITH RISK MANAGEMENT")
        print("-" * 50)

        try:
            # Account and position info
            account_value = self.position_tracker.get_account_value()
            position = self.position_tracker.get_position(self.config.SYMBOL)
            current_orders = self.position_tracker.get_open_orders(self.config.SYMBOL)

            print(f"💰 Account Value: ${account_value:.2f}")

            if position and fair_price:
                pnl = position.calculate_unrealized_pnl(fair_price)
                position_pct = (abs(position.size) * fair_price / account_value * 100) if account_value > 0 else 0
                print(f"📊 Position: {position.size:.4f} {self.config.SYMBOL} ({position_pct:.1f}% of account)")
                print(f"💹 Unrealized PnL: ${pnl:.2f}")
            else:
                print("📊 Position: No position")
                print("💹 Unrealized PnL: $0.00")

            print(f"📋 Open Orders: {len(current_orders)}")

            if fair_price:
                print(f"💰 Enhanced Fair Price: ${fair_price:.5f}")

            # Funding rate monitoring
            if self.config.ENABLE_FUNDING_ALERTS:
                funding_rate = self.data_manager.get_funding_rate()
                funding_pct = funding_rate * 100

                print(f"💸 Funding Rate: {funding_pct:.4f}%")

                # Determine if we're earning or paying
                if position and position.size != 0:
                    # Long position: pays funding if rate is positive, earns if negative
                    # Short position: earns funding if rate is positive, pays if negative
                    is_long = position.size > 0

                    if (is_long and funding_rate > 0) or (not is_long and funding_rate < 0):
                        status = "PAYING"
                        symbol = "➖"
                    elif (is_long and funding_rate < 0) or (not is_long and funding_rate > 0):
                        status = "EARNING"
                        symbol = "➕"
                    else:
                        status = "NEUTRAL"
                        symbol = "⚪"

                    # Calculate estimated 8-hour funding cost/income
                    position_notional = abs(position.size) * fair_price if fair_price else 0
                    funding_amount = position_notional * abs(funding_rate)

                    print(f"   {symbol} Position {status} funding")
                    print(f"   Estimated 8h: ${funding_amount:.4f} {'cost' if status == 'PAYING' else 'income'}")
                else:
                    print(f"   ⚪ No position - no funding impact")

                # Alert if funding rate is high
                if abs(funding_rate) > self.config.HIGH_FUNDING_THRESHOLD:
                    alert_symbol = "🔴" if abs(funding_rate) > self.config.HIGH_FUNDING_THRESHOLD * 2 else "🟡"
                    print(f"   {alert_symbol} HIGH FUNDING ALERT: {funding_pct:.4f}% (threshold: {self.config.HIGH_FUNDING_THRESHOLD*100:.4f}%)")

                    if funding_rate > 0:
                        print(f"   💡 Longs paying shorts - consider short bias")
                    else:
                        print(f"   💡 Shorts paying longs - consider long bias")
            
            # Enhanced microstructure summary
            signals = self.microstructure.get_current_signals()
            print(f"🧠 Microstructure Analysis:")
            print(f"   - Flow Confidence: {signals.flow_confidence:.3f}")
            print(f"   - Overall Momentum: {signals.overall_momentum:.3f}")
            print(f"   - Adverse Risk: {signals.adverse_selection_risk:.3f}")
            print(f"   - Volume Imbalance: {signals.volume_imbalance:.3f}")

            # Order Flow Pressure Analysis
            if hasattr(self.strategy, 'last_flow_imbalance') and hasattr(self.strategy, 'last_flow_adjustment'):
                flow_imbalance = self.strategy.last_flow_imbalance
                flow_adjustment = self.strategy.last_flow_adjustment

                if abs(flow_imbalance) > 0.01 or abs(flow_adjustment) > 0.001:
                    print(f"🌊 Order Flow Pressure:")
                    print(f"   - Flow Imbalance: {flow_imbalance:+.3f} ({flow_imbalance*100:+.1f}%)")

                    # Visual indicator
                    if flow_imbalance > 0.3:
                        flow_status = "🟢 Strong BUY pressure"
                    elif flow_imbalance > 0.1:
                        flow_status = "🟩 Moderate BUY pressure"
                    elif flow_imbalance < -0.3:
                        flow_status = "🔴 Strong SELL pressure"
                    elif flow_imbalance < -0.1:
                        flow_status = "🟥 Moderate SELL pressure"
                    else:
                        flow_status = "⚪ Neutral flow"

                    print(f"   - Flow Status: {flow_status}")
                    print(f"   - Price Adjustment: ${flow_adjustment:+.5f}")

                    if flow_adjustment > 0:
                        print(f"   - Direction: ↑ Adjusting price UP")
                    elif flow_adjustment < 0:
                        print(f"   - Direction: ↓ Adjusting price DOWN")
                    else:
                        print(f"   - Direction: ⚪ No adjustment")

            # NEW: Risk-specific logging
            current_price = fair_price or 0
            if position and hasattr(self.strategy, 'get_risk_status') and current_price > 0:
                risk_status = self.strategy.get_risk_status(position, current_price)
                
                if not risk_status.get('no_position'):
                    print(f"🛡️  Risk Management Status:")
                    
                    # Safe extraction with defaults
                    stop_distance = risk_status.get('stop_loss_distance', 0)
                    profit_distance = risk_status.get('profit_target_distance', 0)
                    
                    print(f"   - Stop-Loss Distance: {stop_distance:.2f}%")
                    print(f"   - Profit Target Distance: {profit_distance:.2f}%")
                    
                    profit_skew = 0
                    if hasattr(self.strategy, 'calculate_profit_skew'):
                        try:
                            profit_skew = self.strategy.calculate_profit_skew(position, current_price)
                            print(f"   - Current Profit Skew: {profit_skew*100:.3f}%")
                        except:
                            print(f"   - Current Profit Skew: 0.000%")
                    
                    # Risk level assessment
                    stop_distance_abs = abs(stop_distance)
                    if stop_distance_abs < 0.5:
                        print(f"   - Risk Level: 🔴 HIGH (near stop-loss)")
                    elif stop_distance_abs < 1.0:
                        print(f"   - Risk Level: 🟡 MEDIUM")
                    else:
                        print(f"   - Risk Level: 🟢 LOW")
            
            # Time since trading started
            if hasattr(self, 'trading_start_time') and self.trading_start_time:
                trading_duration = time.time() - self.trading_start_time
                print(f"⏰ Trading Duration: {trading_duration/60:.1f} minutes")
            
            # Log to main logger as well
            if position:
                self.logger.info(f"Enhanced+Risk: ${account_value:.0f} | Position: {position.size:.4f} ({position_pct:.1f}%) | PnL: ${pnl:.2f} | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")
            else:
                self.logger.info(f"Enhanced+Risk: ${account_value:.0f} | No position | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")

            # Log metrics to InfluxDB for Grafana dashboard
            metrics = {
                'fair_price': fair_price or 0,
                'account_value': account_value,
                'position_size': position.size if position else 0,
                'unrealized_pnl': pnl if position and fair_price else 0,
                'spread_pct': orderbook.get('spread_pct', 0) if 'orderbook' in locals() else 0,
                'open_orders': len(current_orders)
            }
            self.metrics_logger.log_trading_metrics(metrics)

            # Log microstructure signals
            if signals:
                self.metrics_logger.log_signals(signals)

            # Log risk metrics if position exists
            if position and hasattr(self.strategy, 'get_risk_status') and current_price > 0:
                risk_status = self.strategy.get_risk_status(position, current_price)
                if not risk_status.get('no_position'):
                    self.metrics_logger.log_risk_metrics(risk_status)

        except Exception as e:
            print(f"❌ Error logging enhanced status: {e}")
            self.logger.error(f"Error logging enhanced status: {e}")


    async def enhanced_trading_loop(self):
        """Enhanced trading loop with learning phase and orderbook analysis"""
        print("\n" + "=" * 60)
        if self.learning_phase_active:
            print("🎓 STARTING ENHANCED LEARNING PHASE")
        else:
            print("💹 STARTING ENHANCED TRADING LOOP")
        print("=" * 60)
        
        self.logger.info("Starting enhanced main loop...")
        loop_count = 0
        last_learning_log = 0
        
        while self.running:
            try:
                loop_count += 1
                current_time = time.time()
                
                # Check if learning phase should end
                if self.learning_phase_active and self._check_learning_phase_completion():
                    self._end_learning_phase()
                
                if self.learning_phase_active:
                    print(f"\n🎓 Enhanced Learning Loop #{loop_count}")
                else:
                    print(f"\n💹 Enhanced Trading Loop #{loop_count}")
                
                # WebSocket status check
                ws_status = getattr(self.data_manager, 'real_time_enabled', 'Unknown')
                print(f"🔍 WebSocket status: {ws_status}")
                
                # Get market data with enhanced analysis
                if hasattr(self.data_manager, 'real_time_enabled') and self.data_manager.real_time_enabled:
                    if not self.learning_phase_active:
                        print("📡 Using real-time data with enhanced analysis")
                    orderbook = await self.data_manager.get_orderbook()
                    if orderbook and not self.learning_phase_active:
                        print(f"📊 Enhanced orderbook analysis: Mid=${orderbook.get('mid_price', 0):.5f}")
                else:
                    if not self.learning_phase_active:
                        print("📊 Using REST API with enhanced analysis")
                    orderbook = await self.update_market_data()
                
                if not orderbook:
                    print("⚠️ No market data - waiting before next iteration")
                    sleep_time = (self.config.LEARNING_PHASE_UPDATE_INTERVAL if self.learning_phase_active 
                                else self.config.UPDATE_INTERVAL)
                    await asyncio.sleep(sleep_time)
                    continue
                
                # Update positions and orders
                await self.update_positions_and_orders()
                
                # Execute enhanced trading logic (only if not in learning phase)
                if not self.learning_phase_active:
                    await self.execute_enhanced_trading_logic(orderbook)
                
                # Calculate enhanced fair price for status
                fair_price = None
                if not self.learning_phase_active:
                    recent_trades_list = list(self.microstructure.trade_history) if hasattr(self.microstructure, 'trade_history') else []
                    recent_trades_dicts = [
                        {'price': t.price, 'size': t.size, 'side': 'B' if t.is_aggressive_buy else 'A', 'timestamp': t.timestamp}
                        for t in recent_trades_list
                    ] if recent_trades_list else []
                    fair_price = self.strategy.calculate_fair_price(orderbook, recent_trades_dicts)
                
                # Log status
                if self.learning_phase_active:
                    if current_time - last_learning_log >= self.config.LEARNING_PHASE_LOG_INTERVAL:
                        await self.log_enhanced_status(fair_price)
                        last_learning_log = current_time
                else:
                    await self.log_enhanced_status(fair_price)
                
                # Adaptive sleep timing
                if self.learning_phase_active:
                    sleep_time = self.config.LEARNING_PHASE_UPDATE_INTERVAL
                    if loop_count % 15 == 0:
                        print(f"⏰ Enhanced learning mode - waiting {sleep_time}s...")
                else:
                    sleep_time = (self.config.UPDATE_INTERVAL * 2 if ws_status else self.config.UPDATE_INTERVAL)
                    print(f"⏰ Enhanced trading mode - waiting {sleep_time}s...")
                
                print("=" * (45 + len(str(loop_count))))
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                print(f"\n❌ ERROR IN ENHANCED MAIN LOOP: {e}")
                self.logger.error(f"Error in enhanced main loop: {e}")
                await asyncio.sleep(self.config.UPDATE_INTERVAL * 5)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down enhanced bot...")
        self.logger.info(f"Received signal {signum}, shutting down enhanced bot...")
        self.running = False
    
    async def run(self):
        """Run the enhanced market maker"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            await self.initialize()
            self.running = True
            
            # Start WebSocket listener as background task
            ws_task = None
            if hasattr(self.data_manager, 'real_time_enabled') and self.data_manager.real_time_enabled:
                print("📡 Starting enhanced real-time WebSocket feeds...")
                ws_task = asyncio.create_task(self.data_manager.start_real_time_feeds())
                print("📡 Enhanced real-time data feeds started")
            else:
                print("⚠️ WebSocket not available, using enhanced REST API analysis")
            
            # Start enhanced main loop
            await self.enhanced_trading_loop()
            
        finally:
            # Cancel WebSocket task if running
            if ws_task and not ws_task.done():
                print("🛑 Stopping enhanced WebSocket feeds...")
                ws_task.cancel()
                try:
                    await ws_task
                except asyncio.CancelledError:
                    pass
            
            await self.cleanup()


# Main execution
if __name__ == "__main__":
    print("🚀 ENHANCED HYPERLIQUID MARKET MAKER")
    print("=" * 60)
    print("🎓 Learning Phase + 📊 Orderbook Analysis + 🧠 Microstructure")
    print("=" * 60)
    
    # Installation check
    try:
        import hyperliquid
        from eth_account import Account
        import numpy as np
        import websockets
        print("✅ Required packages detected")
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("💡 Run: pip install hyperliquid-python-sdk eth-account numpy websockets")
        exit(1)
    
    bot = EnhancedHyperliquidMarketMaker()
    
    # Enhanced safety checks
    print("\n🔍 ENHANCED SAFETY CHECKS")
    print("-" * 30)
    
    if not bot.config.PRIVATE_KEY:
        print("⚠️  No private key found - set HYPERLIQUID_PRIVATE_KEY environment variable")
        print("📝 Will run in read-only mode with enhanced analysis")
    else:
        print("✅ Private key configured")
    
    if not bot.config.ENABLE_TRADING:
        print("⚠️  TRADING IS DISABLED - Set ENABLE_TRADING=True in config to enable real trading")
        print("📝 Currently running in enhanced paper trading mode")
    else:
        print("🚨 LIVE TRADING ENABLED with enhanced risk management")
    
    if bot.config.TESTNET:
        print("🧪 Running on TESTNET with enhanced features")
    else:
        print("🚀 Running on MAINNET with enhanced features")
    
    print(f"💱 Trading symbol: {bot.config.SYMBOL}")
    print(f"🎓 Learning phase: {'ENABLED' if bot.config.ENABLE_LEARNING_PHASE else 'DISABLED'}")
    if bot.config.ENABLE_LEARNING_PHASE:
        print(f"   Duration: {bot.config.LEARNING_PHASE_DURATION/60:.1f} minutes")
    print(f"📊 Update interval: {bot.config.UPDATE_INTERVAL}s")
    print(f"🧠 Microstructure analysis: ENHANCED")
    print(f"📈 Orderbook analysis: ENABLED")
    print(f"🎯 Adverse selection protection: ACTIVE")
    print(f"🌊 Dynamic spread calculation: ENABLED")
    
    print("\n" + "=" * 60)
    print("🎓 ENHANCED LEARNING PHASE WORKFLOW")
    print("   1. 📚 Observe market for comprehensive data collection")
    print("   2. 📊 Analyze orderbook patterns and liquidity distribution")
    print("   3. ⚖️  Measure volume imbalances and spread dynamics")
    print("   4. 🎯 Calibrate adverse selection detection thresholds")
    print("   5. 🧠 Establish microstructure analysis baselines")
    print("   6. 🚀 Begin intelligent order placement with enhanced algorithms")
    print("")
    print("💹 ENHANCED TRADING FEATURES")
    print("   ✅ Smart fair price calculation using volume-weighted analysis")
    print("   ✅ Dynamic spread adjustment based on market conditions")
    print("   ✅ Orderbook gap detection for optimal order placement")
    print("   ✅ Adverse selection risk assessment and protection")
    print("   ✅ Market condition classification (CALM/TRENDING/VOLATILE/ILLIQUID)")
    print("   ✅ Liquidity concentration analysis")
    print("   ✅ Position-aware order sizing and skewing")
    print("   ✅ Microstructure-informed cancellation logic")
    print("=" * 60)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Enhanced bot stopped by user")
    except Exception as e:
        print(f"\n❌ Enhanced bot crashed: {e}")
        import traceback
        traceback.print_exc()