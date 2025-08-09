import asyncio
import logging
import signal
from typing import Optional, Dict
from config import TradingConfig
from data_manager import DataManager
from position_tracker import PositionTracker, Order
from strategy import MarketMakingStrategy
from trading_client import TradingClient

class HyperliquidMarketMaker:
    def __init__(self):
        self.config = TradingConfig()
        self.data_manager = DataManager(self.config)
        self.position_tracker = PositionTracker(self.config)
        self.strategy = MarketMakingStrategy(self.config)
        self.trading_client = TradingClient(self.config)
        self.running = False
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize all components"""
        self.logger.info("Initializing Hyperliquid Market Maker with SDK...")
        
        # Validate configuration
        if not self.config.PRIVATE_KEY and self.config.ENABLE_TRADING:
            raise ValueError("Private key required for trading")
        
        await self.data_manager.initialize()
        self.logger.info("Initialization complete")
    
    async def cleanup(self):
        """Cleanup all components"""
        self.logger.info("Cleaning up...")
        await self.data_manager.cleanup()
        self.logger.info("Cleanup complete")
    
    async def update_positions_and_orders(self):
        """Update position and order information from exchange"""
        if not self.trading_client.user_address:
            return
            
        try:
            # Use MASTER wallet address for account data
            master_address = self.config.MASTER_WALLET_ADDRESS
            self.logger.info(f"Fetching account data for master wallet: {master_address}")
            
            # Fetch account state from master wallet
            account_info = await self.data_manager.get_account_info(master_address)
            if account_info:
                self.position_tracker.update_from_account_state(account_info)
            
            # Fetch open orders using API wallet (the one that placed them)
            open_orders = await self.data_manager.get_open_orders(self.trading_client.user_address)
            self.position_tracker.update_from_open_orders(open_orders)
            
        except Exception as e:
            self.logger.error(f"Error updating positions and orders: {e}")

    async def trading_loop(self):
        """Main trading loop"""
        self.logger.info("Starting trading loop...")
        
        while self.running:
            try:
                # Fetch market data
                orderbook = await self.data_manager.get_orderbook()
                if not orderbook:
                    await asyncio.sleep(self.config.UPDATE_INTERVAL)
                    continue
                
                # Update positions and orders
                await self.update_positions_and_orders()
                
                position = self.position_tracker.get_position(self.config.SYMBOL)
                current_orders = self.position_tracker.get_open_orders(self.config.SYMBOL)
                
                # Calculate fair price for order management
                fair_price = self.strategy.calculate_fair_price(orderbook)
                if not fair_price:
                    await asyncio.sleep(self.config.UPDATE_INTERVAL)
                    continue
                
                # Cancel orders that are too far from fair price
                if current_orders and fair_price:
                    orders_to_cancel = self.strategy.should_cancel_orders(current_orders, fair_price)
                    if orders_to_cancel:
                        success = await self.trading_client.cancel_orders(orders_to_cancel)
                        if success:
                            for order_id in orders_to_cancel:
                                if order_id in self.position_tracker.open_orders:
                                    del self.position_tracker.open_orders[order_id]
                
                # Generate new orders if needed
                if len(current_orders) < self.config.MAX_ORDERS_PER_SIDE * 2:
                    new_orders = self.strategy.generate_orders(orderbook, position, self.position_tracker.get_account_value())
                    
                    
                    if new_orders:
                        order_ids = await self.trading_client.place_orders(new_orders)
                        
                        # Track successful orders
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
                
                # Log current status
                account_value = self.position_tracker.get_account_value()
                if position:
                    pnl = position.calculate_unrealized_pnl(fair_price)
                    position_pct = (abs(position.size) * fair_price / account_value * 100) if account_value > 0 else 0
                    self.logger.info(f"Account: ${account_value:.0f} | Position: {position.size:.4f} ({position_pct:.1f}%) | PnL: ${pnl:.5f} | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")
                else:
                    self.logger.info(f"Account: ${account_value:.0f} | No position | Orders: {len(current_orders)} | Fair: ${fair_price:.5f}")
                
                await asyncio.sleep(self.config.UPDATE_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(self.config.UPDATE_INTERVAL * 5)  # Wait longer on error
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def run(self):
        """Run the market maker"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            await self.initialize()
            self.running = True
            await self.trading_loop()
        finally:
            await self.cleanup()

# Main execution
if __name__ == "__main__":
    # Installation check
    try:
        import hyperliquid
        from eth_account import Account
    except ImportError:
        print("❌ Required packages not installed. Run:")
        print("pip install hyperliquid-python-sdk eth-account")
        exit(1)
    
    bot = HyperliquidMarketMaker()
    
    # Safety checks
    if not bot.config.PRIVATE_KEY:
        print("⚠️  No private key found - set HYPERLIQUID_PRIVATE_KEY environment variable")
        print("📝 Will run in read-only mode")
    
    if not bot.config.ENABLE_TRADING:
        print("⚠️  TRADING IS DISABLED - Set ENABLE_TRADING=True in config to enable real trading")
        print("📝 Currently running in paper trading mode")
    
    if bot.config.TESTNET:
        print("🧪 Running on TESTNET")
    else:
        print("🚀 Running on MAINNET")
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()