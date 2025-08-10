import asyncio
import logging
import signal
from typing import Optional, Dict, List
from config import TradingConfig
from data_manager import DataManager
from position_tracker import PositionTracker, Order
from strategy import MarketMakingStrategy
from trading_client import TradingClient
from market_microstructure import MarketMicrostructure
from websocket_manager import DataManagerWithWebSocket
from data_manager import DataManager
import time

class HyperliquidMarketMaker:
    def __init__(self):
        print("🚀 Initializing Hyperliquid Market Maker...")
        
        self.config = TradingConfig()
        print(f"   📋 Configuration loaded for {self.config.SYMBOL}")
        
        base_data_manager = DataManager(self.config)
        self.data_manager = DataManagerWithWebSocket(self.config, base_data_manager)
        print("   📊 Data manager with WebSocket initialized")
        
        self.position_tracker = PositionTracker(self.config)
        print("   📈 Position tracker initialized")
        
        self.strategy = MarketMakingStrategy(self.config)
        print("   🎯 Strategy initialized")
        
        self.trading_client = TradingClient(self.config)
        print("   💱 Trading client initialized")
        
        # NEW: Initialize microstructure analysis
        self.microstructure = MarketMicrostructure(self.config)
        print("   🧠 Microstructure analyzer initialized")
        
        self.running = False
        self.logger = self._setup_logging()
        print("   📝 Logging configured")
        print("")

    def handle_real_time_trades(self, trades: List[Dict]):
        """Handle real-time trade data from WebSocket"""
        if trades:
            print(f"🔄 Processing {len(trades)} real-time trades...")
            # Debug: Show first few trades
            for trade in trades[:5]:
                print(f"   Trade: ${trade.get('price', 0):.5f} size={trade.get('size', 0):.6f} side={trade.get('side', 'N/A')}")
            
            # Feed to microstructure analyzer
            self.microstructure.add_trade_events(trades)
        
        else:
            print("🚀 WEBSOCKET: Received empty trade list")

    def handle_real_time_orderbook(self, orderbook: Dict):
        """Handle real-time orderbook data from WebSocket"""
        if orderbook:
            print(f"🔄 Processing real-time orderbook update...")
            print(f"   Mid: ${orderbook.get('mid_price', 0):.5f}")
            
            # Feed to microstructure analyzer
            self.microstructure.add_orderbook_snapshot(orderbook)

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize all components"""
        print("=" * 60)
        print("🔧 INITIALIZATION PHASE")
        print("=" * 60)
        
        self.logger.info("Initializing Hyperliquid Market Maker with SDK...")
        
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
        
        # NEW: Set up real-time callbacks
        print("🔗 Setting up real-time data callbacks...")
        self.data_manager.set_trade_callback(self.handle_real_time_trades)
        self.data_manager.set_orderbook_callback(self.handle_real_time_orderbook)
        
        # Display symbol-specific parameters that were fetched
        symbol_info = self.data_manager.get_symbol_info()
        print(f"\n📊 Symbol Configuration:")
        print(f"   🎯 Symbol: {symbol_info['symbol']}")
        print(f"   📏 Size decimals: {symbol_info['size_decimals']}")
        print(f"   ⚡ Max leverage: {symbol_info['max_leverage']}x")
        print(f"   📊 Max position: {symbol_info['max_position_pct']}x")
        
        print("\n✅ Initialization complete!")
        print("=" * 60)
        self.logger.info("Initialization complete")
    
    async def cleanup(self):
        """Cleanup all components"""
        print("\n" + "=" * 60)
        print("🧹 CLEANUP PHASE")
        print("=" * 60)
        
        self.logger.info("Cleaning up...")
        await self.data_manager.cleanup()
        print("✅ Cleanup complete!")
        print("=" * 60)
        self.logger.info("Cleanup complete")
    
    async def update_positions_and_orders(self):
        """Update position and order information from exchange"""
        print("\n📊 UPDATING ACCOUNT STATE")
        print("-" * 40)
        
        if not self.trading_client.user_address:
            print("⚠️  No user address - skipping account update")
            return
            
        try:
            # Use MASTER wallet address for account data
            master_address = self.config.MASTER_WALLET_ADDRESS
            print(f"👤 Using master wallet: {master_address[:10]}...")
            
            # Fetch account state from master wallet
            print("💰 Fetching account information...")
            account_info = await self.data_manager.get_account_info(master_address)
            if account_info:
                print("✅ Account info retrieved - updating position tracker")
                self.position_tracker.update_from_account_state(account_info)
            else:
                print("❌ Failed to retrieve account info")
            
            # Use your specified account address for order queries
            account_address = "0x32BE427D44f7eA8076f62190bd3a7d0FDceF076c"
            
            # Fetch open orders using account address (where orders actually are)
            print("📋 Fetching open orders...")
            print(f"🔍 API wallet address: {self.trading_client.user_address}")
            print(f"🔍 Master wallet address: {master_address}")
            print(f"🔍 Account address for orders: {account_address}")
            
            open_orders = await self.data_manager.get_open_orders(account_address)
            if open_orders is not None:
                print(f"✅ Retrieved {len(open_orders)} open orders")
                self.position_tracker.update_from_open_orders(open_orders)
            else:
                print("❌ Failed to retrieve open orders")
        
        except Exception as e:
            print(f"❌ Error updating positions and orders: {e}")
            self.logger.error(f"Error updating positions and orders: {e}")

    async def update_market_data(self):
        """Update market data and microstructure analysis"""
        print("\n📈 UPDATING MARKET DATA")
        print("-" * 40)
        
        try:
            # Fetch orderbook
            print("📊 Fetching orderbook...")
            orderbook = await self.data_manager.get_orderbook()
            if orderbook:
                print("✅ Orderbook retrieved - updating microstructure")
                self.microstructure.add_orderbook_snapshot(orderbook)
            else:
                print("❌ Failed to retrieve orderbook")
                return None
            
            # Fetch recent trades
            print("💹 Fetching recent trades...")
            recent_trades = await self.data_manager.get_recent_trades()
            if recent_trades:
                print(f"✅ Retrieved {len(recent_trades)} new trades - updating microstructure")
                self.microstructure.add_trade_events(recent_trades)
            else:
                print("📊 No new trades since last update")
            
            return orderbook
                    
        except Exception as e:
            print(f"❌ Error updating market data: {e}")
            self.logger.error(f"Error updating market data: {e}")
            return None

    async def execute_trading_logic(self, orderbook: Dict):
        """Execute main trading logic with microstructure signals"""
        print("\n🎯 EXECUTING TRADING LOGIC")
        print("-" * 40)
        
        try:
            # Get current market signals
            print("🧠 Retrieving microstructure signals...")
            signals = self.microstructure.get_current_signals()
            signal_summary = self.microstructure.get_signal_summary()
            print(f"📊 Market signals: {signal_summary}")
            
            # Get current position and orders
            position = self.position_tracker.get_position(self.config.SYMBOL)
            current_orders = self.position_tracker.get_open_orders(self.config.SYMBOL)
            
            print(f"📋 Current state: {len(current_orders)} open orders")
            if position:
                print(f"📊 Position: {position.size:.4f} {self.config.SYMBOL}")
            else:
                print("📊 No position")
            
            # Calculate fair price for order management
            fair_price = self.strategy.calculate_fair_price(orderbook)
            if not fair_price:
                print("❌ Cannot determine fair price - skipping trading logic")
                return
            
            # Cancel orders that are too far from fair price or based on microstructure signals
            if current_orders and fair_price:
                print("🔍 Evaluating existing orders...")
                orders_to_cancel = self.strategy.should_cancel_orders(current_orders, fair_price, signals)
                
                if orders_to_cancel:
                    print(f"❌ Cancelling {len(orders_to_cancel)} orders...")
                    success = await self.trading_client.cancel_orders(orders_to_cancel)
                    if success:
                        print("✅ Orders cancelled successfully")
                        # Remove cancelled orders from tracking
                        for order_id in orders_to_cancel:
                            if order_id in self.position_tracker.open_orders:
                                del self.position_tracker.open_orders[order_id]
                                print(f"   📝 Removed order {order_id} from tracking")
                    else:
                        print("❌ Failed to cancel some orders")
                else:
                    print("✅ No orders need cancellation")
            
            # Generate new orders if needed
            max_total_orders = self.config.MAX_ORDERS_PER_SIDE * 2
            current_order_count = len(current_orders)
            
            print(f"📊 Order capacity: {current_order_count}/{max_total_orders}")
            
            if current_order_count < max_total_orders:
                print("🎯 Generating new orders...")
                account_value = self.position_tracker.get_account_value()
                new_orders = self.strategy.generate_orders(orderbook, position, account_value, signals)
                
                if new_orders:
                    print(f"📦 Placing {len(new_orders)} new orders...")
                    order_ids = await self.trading_client.place_orders(new_orders)
                    
                    # Track successful orders
                    successful_orders = 0
                    for i, order_id in enumerate(order_ids):
                        if order_id and i < len(new_orders):
                            # Create order tracking object
                            order_data = {
                                'oid': order_id,
                                'coin': new_orders[i]['coin'],
                                'side': 'B' if new_orders[i]['is_buy'] else 'A',
                                'sz': str(new_orders[i]['sz']),
                                'limitPx': str(new_orders[i]['limit_px'])
                            }
                            order = Order(order_data)
                            self.position_tracker.open_orders[order_id] = order
                            successful_orders += 1
                            print(f"   ✅ Tracking new order: {order_id}")
                    
                    print(f"📈 Successfully placed and tracking {successful_orders}/{len(new_orders)} orders")
                else:
                    print("⚠️  No new orders generated")
            else:
                print("📊 Maximum orders reached - not generating new orders")
                
        except Exception as e:
            print(f"❌ Error in trading logic: {e}")
            self.logger.error(f"Error in trading logic: {e}")

        if current_orders and fair_price:
            print("🔍 Evaluating existing orders...")
            print(f"   📋 Found {len(current_orders)} orders to evaluate")
            for order in current_orders:
                print(f"   📋 Order: {order.order_id} | {order.side} | ${order.price} | {order.size}")
            
            orders_to_cancel = self.strategy.should_cancel_orders(current_orders, fair_price, signals)
            print(f"   📋 Orders marked for cancellation: {len(orders_to_cancel)}")
            
            if orders_to_cancel:
                print(f"❌ Cancelling {len(orders_to_cancel)} orders...")
                # ... rest of cancellation logic

    async def log_status(self, fair_price: Optional[float]):
        """Log current trading status"""
        print("\n📊 CURRENT STATUS")
        print("-" * 40)
        
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
                print(f"💰 Fair Price: ${fair_price:.5f}")
            
            # Microstructure summary
            signals = self.microstructure.get_current_signals()
            print(f"🧠 Flow Confidence: {signals.flow_confidence:.3f}")
            print(f"🌊 Overall Momentum: {signals.overall_momentum:.3f}")
            print(f"⚠️  Adverse Risk: {signals.adverse_selection_risk:.3f}")
            
            # Log to main logger as well
            if position:
                self.logger.info(f"Account: ${account_value:.0f} | Position: {position.size:.4f} ({position_pct:.1f}%) | PnL: ${pnl:.2f} | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")
            else:
                self.logger.info(f"Account: ${account_value:.0f} | No position | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")
                
        except Exception as e:
            print(f"❌ Error logging status: {e}")
            self.logger.error(f"Error logging status: {e}")

    # 2. Replace your trading_loop method in main.py with this optimized version

    async def trading_loop(self):
        """Optimized trading loop with faster order management"""
        print("\n" + "=" * 60)
        print("🔄 STARTING OPTIMIZED TRADING LOOP")
        print("=" * 60)
        
        self.logger.info("Starting optimized trading loop...")
        loop_count = 0
        last_order_refresh = 0
        last_account_update = 0
        last_price = 0
        skip_counter = 0
        
        # Cache for performance
        cached_orderbook = None
        cached_signals = None
        
        while self.running:
            try:
                loop_count += 1
                current_time = asyncio.get_event_loop().time()
                
                print(f"\n{'=' * 15} FAST LOOP #{loop_count} {'=' * 15}")
                
                # Update web interface with loop count
                #update_web_interface(self, loop_count=loop_count)
                
                # 1. ALWAYS get fresh market data (this is critical for order management)
                print("📊 Fetching market data...")
                orderbook = await self.data_manager.get_orderbook()
                
                if not orderbook:
                    print("⚠️ No market data - waiting before retry")
                    await asyncio.sleep(0.5)  # Shorter wait
                    continue
                
                cached_orderbook = orderbook
                fair_price = self.strategy.calculate_fair_price(orderbook)
                current_price = orderbook.get('mid_price', 0)
                
                # 2. FAST ORDER MANAGEMENT - Check every loop
                print("⚡ Fast order management check...")
                
                # Get current orders (this should be fast)
                current_orders = self.position_tracker.get_open_orders(self.config.SYMBOL)
                
                # Quick price movement check
                price_moved_significantly = False
                if last_price > 0 and current_price > 0:
                    price_change_pct = abs(current_price - last_price) / last_price
                    if price_change_pct > self.config.PRICE_MOVEMENT_CANCEL_THRESHOLD:
                        price_moved_significantly = True
                        print(f"🚨 Price moved {price_change_pct*100:.2f}% - triggering order refresh")
                
                last_price = current_price
                
                # 3. AGGRESSIVE ORDER CANCELLATION
                should_cancel_all = False
                
                if current_orders and fair_price:
                    orders_to_cancel = []
                    
                    for order in current_orders:
                        # SAFE TIMESTAMP HANDLING
                        try:
                            if hasattr(order, 'created_at'):
                                if isinstance(order.created_at, float):
                                    order_age = current_time - order.created_at
                                elif hasattr(order.created_at, 'timestamp'):
                                    # It's a datetime object
                                    order_age = current_time - order.created_at.timestamp()
                                else:
                                    # Unknown format, treat as old
                                    order_age = 999
                            else:
                                # No creation time, assume it's old
                                order_age = 999
                        except Exception as e:
                            print(f"   ⚠️ Error calculating order age: {e}")
                            order_age = 999  # Treat as old if calculation fails
                        
                        # Cancel old orders
                        if order_age > self.config.MAX_ORDER_AGE_SECONDS:
                            orders_to_cancel.append(order.order_id)
                            print(f"   ⏰ Cancelling old order: {order.order_id} (age: {order_age:.1f}s)")
                        
                        # Cancel orders far from fair price (tighter threshold)
                        elif order.side == 'buy' and order.price < fair_price * (1 - self.config.QUICK_CANCEL_THRESHOLD):
                            orders_to_cancel.append(order.order_id)
                            print(f"   💰 Cancelling low bid: ${order.price:.2f} vs fair ${fair_price:.2f}")
                        
                        elif order.side == 'sell' and order.price > fair_price * (1 + self.config.QUICK_CANCEL_THRESHOLD):
                            orders_to_cancel.append(order.order_id)
                            print(f"   💰 Cancelling high ask: ${order.price:.2f} vs fair ${fair_price:.2f}")
                    
                    # Cancel if price moved significantly
                    if price_moved_significantly and current_orders:
                        should_cancel_all = True
                        print(f"   📈 Cancelling all orders due to price movement")
                    
                    # Execute cancellations
                    if should_cancel_all:
                        orders_to_cancel = [order.order_id for order in current_orders]
                    
                    if orders_to_cancel:
                        print(f"❌ Cancelling {len(orders_to_cancel)} orders...")
                        success = await self.trading_client.cancel_orders(orders_to_cancel)
                        
                        if success:
                            # Remove from tracking immediately
                            for order_id in orders_to_cancel:
                                if order_id in self.position_tracker.open_orders:
                                    del self.position_tracker.open_orders[order_id]
                            
                            current_orders = []  # Clear local cache
                            print("✅ Orders cancelled and removed from tracking")
                            
                            # Update web interface immediately
                        # update_web_interface(self, orders=[])
                
                # 4. FAST ORDER PLACEMENT
                remaining_orders = len(current_orders)
                max_orders = self.config.MAX_ORDERS_PER_SIDE * 2
                
                if remaining_orders < max_orders:
                    print(f"🎯 Quick order generation ({remaining_orders}/{max_orders})...")
                    
                    # Use cached signals if available and recent
                    if not cached_signals or (loop_count % 3 == 0):  # Refresh signals every 3rd loop
                        cached_signals = self.microstructure.get_current_signals()
                    
                    # Get position (this should be cached/fast)
                    position = self.position_tracker.get_position(self.config.SYMBOL)
                    account_value = self.position_tracker.get_account_value()
                    
                    # Generate new orders
                    new_orders = self.strategy.generate_orders(orderbook, position, account_value, cached_signals)
                    
                    if new_orders:
                        print(f"📦 Placing {len(new_orders)} new orders...")
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
                                    'limitPx': str(new_orders[i]['limit_px'])
                                }
                                order = Order(order_data)
                                order.created_at = current_time  # Store as float timestamp
                                self.position_tracker.open_orders[order_id] = order
                                successful_orders += 1
                        
                        print(f"📈 Placed and tracking {successful_orders}/{len(new_orders)} orders")
                        
                        # Update web interface
                        updated_orders = []
                        for order in self.position_tracker.open_orders.values():
                            updated_orders.append({
                                'oid': order.order_id,
                                'coin': order.symbol,
                                'side': order.side,
                                'sz': str(order.size),
                                'limitPx': str(order.price)
                            })
                    # update_web_interface(self, orders=updated_orders)
                
                # 5. SELECTIVE HEAVY OPERATIONS (skip some loops)
                skip_counter += 1
                
                # Only do expensive operations every few loops
                if skip_counter >= self.config.SKIP_ACCOUNT_UPDATE_FREQUENCY:
                    skip_counter = 0
                    
                    print("📊 Full account update...")
                    await self.update_positions_and_orders()
                    
                    # Update microstructure analysis
                    recent_trades = await self.data_manager.get_recent_trades()
                    if recent_trades:
                        self.microstructure.add_trade_events(recent_trades)
                        cached_signals = None  # Force refresh next time
                    
                    # Log status
                    await self.log_status(fair_price)
                else:
                    print(f"⚡ Skipping heavy operations (skip {skip_counter}/{self.config.SKIP_ACCOUNT_UPDATE_FREQUENCY})")
                
                # 6. ADAPTIVE SLEEP TIME
                if self.config.ENABLE_FAST_MODE:
                    # Faster when market is active
                    if cached_signals and cached_signals.trade_velocity > self.config.HIGH_VELOCITY_THRESHOLD:
                        sleep_time = self.config.ORDER_REFRESH_INTERVAL  # 0.5s
                        print(f"⚡ High velocity mode - sleeping {sleep_time}s")
                    else:
                        sleep_time = self.config.UPDATE_INTERVAL  # 1.0s
                        print(f"⏰ Normal mode - sleeping {sleep_time}s")
                else:
                    sleep_time = self.config.UPDATE_INTERVAL
                
                print("=" * (32 + len(str(loop_count))))
                await asyncio.sleep(sleep_time)
                    
            except Exception as e:
                print(f"\n❌ ERROR IN OPTIMIZED TRADING LOOP: {e}")
                self.logger.error(f"Error in optimized trading loop: {e}")
            # update_web_interface(self, bot_status='ERROR')
                await asyncio.sleep(1.0)  # Shorter error recovery
        
    def signal_handler(self, signum, frame):
            """Handle shutdown signals"""
            print(f"\n🛑 Received signal {signum}, shutting down...")
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
    async def run(self):
            """Run the market maker with WebSocket support"""
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            try:
                await self.initialize()
                self.running = True
                
                # Start WebSocket listener as background task
                ws_task = None
                if hasattr(self.data_manager, 'real_time_enabled') and self.data_manager.real_time_enabled:
                    print("📡 Starting real-time WebSocket feeds...")
                    ws_task = asyncio.create_task(self.data_manager.start_real_time_feeds())
                    print("📡 Real-time data feeds started in background")
                else:
                    print("⚠️ WebSocket not available, using REST API only")
                
                # Start main trading loop
                await self.trading_loop()
                
            finally:
                # Cancel WebSocket task if running
                if ws_task and not ws_task.done():
                    print("🛑 Stopping WebSocket feeds...")
                    ws_task.cancel()
                    try:
                        await ws_task
                    except asyncio.CancelledError:
                        pass
                
                await self.cleanup()

    

# Main execution
if __name__ == "__main__":
    print("🚀 HYPERLIQUID MARKET MAKER")
    print("=" * 50)
    
    # Installation check
    try:
        import hyperliquid
        from eth_account import Account
        import numpy as np
        print("✅ Required packages detected")
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("💡 Run: pip install hyperliquid-python-sdk eth-account numpy")
        exit(1)
    
    bot = HyperliquidMarketMaker()
    
    # Safety checks and warnings
    print("\n🔍 SAFETY CHECKS")
    print("-" * 30)
    
    if not bot.config.PRIVATE_KEY:
        print("⚠️  No private key found - set HYPERLIQUID_PRIVATE_KEY environment variable")
        print("📝 Will run in read-only mode")
    else:
        print("✅ Private key configured")
    
    if not bot.config.ENABLE_TRADING:
        print("⚠️  TRADING IS DISABLED - Set ENABLE_TRADING=True in config to enable real trading")
        print("📝 Currently running in paper trading mode")
    else:
        print("🚨 LIVE TRADING ENABLED")
    
    if bot.config.TESTNET:
        print("🧪 Running on TESTNET")
    else:
        print("🚀 Running on MAINNET")
    
    print(f"💱 Trading symbol: {bot.config.SYMBOL}")
    print(f"📊 Update interval: {bot.config.UPDATE_INTERVAL}s")
    print(f"🧠 Microstructure analysis: ENABLED")
    
    print("\n" + "=" * 50)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()