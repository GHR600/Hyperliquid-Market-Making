# Replace your websocket_manager.py with this corrected version:

import asyncio
import logging
import json
from typing import Dict, List, Optional, Callable
from hyperliquid.info import Info
from hyperliquid.utils import constants
from config import TradingConfig

class WebSocketManager:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.info = None
        self.running = False
        
        # Callbacks for different data types
        self.trade_callback: Optional[Callable] = None
        self.orderbook_callback: Optional[Callable] = None
        
        print(f"🔌 Initialized WebSocket Manager for {config.SYMBOL}")
    
    async def initialize(self):
        """Initialize WebSocket connection using the official SDK"""
        print("🔌 Initializing WebSocket connection...")
        
        try:
            # Initialize Info client with WebSocket support
            base_url = constants.TESTNET_API_URL if self.config.TESTNET else constants.MAINNET_API_URL
            print(f"   🌐 Connecting to: {base_url}")
            
            # Create Info client with WebSocket enabled (skip_ws=False)
            self.info = Info(base_url=base_url, skip_ws=False)
            print(f"   ✅ Info client created with WebSocket support")
            
            # Subscribe to trades using the correct format
            print(f"📡 Subscribing to trades for {self.config.SYMBOL}...")
            
            if self.info.ws_manager:
                # Use the official SDK subscription method
                trade_subscription = {
                    "type": "trades",
                    "coin": self.config.SYMBOL
                }
                
                # Subscribe with callback
                self.info.ws_manager.subscribe(trade_subscription, self._handle_trade_message)
                print(f"   ✅ Successfully subscribed to trades")
                
                # Subscribe to orderbook updates
                print(f"📊 Subscribing to orderbook for {self.config.SYMBOL}...")
                book_subscription = {
                    "type": "l2Book", 
                    "coin": self.config.SYMBOL
                }
                
                self.info.ws_manager.subscribe(book_subscription, self._handle_orderbook_message)
                print(f"   ✅ Successfully subscribed to orderbook")
                
                print("✅ WebSocket subscriptions active via official SDK")
                self.logger.info(f"WebSocket subscribed to {self.config.SYMBOL} via official SDK")
            else:
                raise Exception("WebSocket manager not available in Info client")
            
        except Exception as e:
            print(f"❌ Failed to initialize WebSocket: {e}")
            print(f"   Error details: {type(e).__name__}: {str(e)}")
            self.logger.error(f"WebSocket initialization failed: {e}")
            raise
    
    def set_trade_callback(self, callback: Callable[[List[Dict]], None]):
        """Set callback function for trade data"""
        self.trade_callback = callback
        print("🔗 Trade callback registered")
    
    def set_orderbook_callback(self, callback: Callable[[Dict], None]):
        """Set callback function for orderbook data"""
        self.orderbook_callback = callback
        print("🔗 Orderbook callback registered")
    
    async def start_listening(self):
        """Keep the WebSocket connection alive"""
        print("👂 WebSocket listener active via SDK...")
        self.running = True
        
        if not self.info or not self.info.ws_manager:
            raise RuntimeError("WebSocket not initialized")
        
        try:
            # The SDK handles the message loop internally
            # We just need to keep this coroutine alive
            while self.running:
                await asyncio.sleep(1)  # Check every second
                
        except Exception as e:
            print(f"❌ WebSocket listener error: {e}")
            self.logger.error(f"WebSocket listener error: {e}")
            
        print("👂 WebSocket listener stopped")
    
    def _handle_trade_message(self, data):
        """Handle trade/fills messages from SDK - FIXED VERSION"""
        try:
            print(f"🔥 Raw trade message received: {data}")
            
            # Handle None data
            if data is None:
                print("⚠️ Received None trade data")
                return
            
            # The data should be a list of trade objects
            if isinstance(data, list):
                trades_data = data
            elif isinstance(data, dict) and 'data' in data:
                trades_data = data['data']
            else:
                trades_data = [data] if data else []
            
            # Handle None trades_data
            if not trades_data or trades_data is None:
                print("⚠️ Empty or None trade data received")
                return
            
            # Convert to standard format
            processed_trades = []
            for trade_data in trades_data:
                if trade_data is not None:  # Check for None trade_data
                    processed_trade = self._convert_trade_format(trade_data)
                    if processed_trade:
                        processed_trades.append(processed_trade)
            
            if processed_trades:
                print(f"💹 Processed {len(processed_trades)} real trades from WebSocket!")
                
                # Log sample trade
                sample = processed_trades[0]
                print(f"   🔥 Real Trade: ${sample.get('price', 0):.5f} size={sample.get('size', 0):.6f} side={sample.get('side', 'N/A')}")
                
                # Call the registered callback
                if self.trade_callback:
                    self.trade_callback(processed_trades)
        
        except Exception as e:
            print(f"❌ Error handling trade message: {e}")
            import traceback
            traceback.print_exc()
            self.logger.error(f"Trade message handling error: {e}")

    
    def _handle_orderbook_message(self, data):
        """Handle orderbook update messages from SDK"""
        try:
            print(f"📊 Raw orderbook message received")
            
            # Convert to standard format
            processed_book = self._convert_orderbook_format(data)
            
            if processed_book:
                print(f"📊 Processed real orderbook update from WebSocket")
                print(f"   Mid: ${processed_book.get('mid_price', 0):.5f}")
                
                # Call the registered callback
                if self.orderbook_callback:
                    self.orderbook_callback(processed_book)
                
        except Exception as e:
            print(f"❌ Error handling orderbook message: {e}")
            self.logger.error(f"Orderbook message handling error: {e}")
    
    def _convert_trade_format(self, trade_data: Dict) -> Optional[Dict]:
        """Convert SDK trade format to standard format"""
        try:
            # SDK trade format should have these fields
            return {
                'timestamp': trade_data.get('time', 0),
                'price': float(trade_data.get('px', 0)),
                'size': float(trade_data.get('sz', 0)),
                'side': trade_data.get('side', ''),  # Should be 'B' for buy, 'A' for sell
            }
        except (ValueError, TypeError, KeyError) as e:
            print(f"⚠️ Failed to convert trade format: {e}")
            print(f"   Raw trade data: {trade_data}")
            self.logger.warning(f"Trade format conversion error: {e}")
            return None
    
    def _convert_orderbook_format(self, book_data) -> Optional[Dict]:
        """Convert SDK orderbook format to standard format"""
        try:
            # Handle different possible formats
            if isinstance(book_data, dict):
                # Extract data if wrapped
                if 'data' in book_data:
                    book_data = book_data['data']
                
                coin = book_data.get('coin', self.config.SYMBOL)
                levels = book_data.get('levels', [])
                timestamp = book_data.get('time', 0)
                
                if len(levels) >= 2:
                    raw_bids = levels[0] if len(levels) > 0 else []
                    raw_asks = levels[1] if len(levels) > 1 else []
                else:
                    print("⚠️ Invalid orderbook levels format")
                    return None
            else:
                print(f"⚠️ Unexpected orderbook data format: {type(book_data)}")
                return None
            
            # Convert to [price, size] format
            processed_bids = []
            processed_asks = []
            
            for bid in raw_bids:
                if isinstance(bid, dict):
                    price = float(bid.get('px', 0))
                    size = float(bid.get('sz', 0))
                    processed_bids.append([price, size])
            
            for ask in raw_asks:
                if isinstance(ask, dict):
                    price = float(ask.get('px', 0))
                    size = float(ask.get('sz', 0))
                    processed_asks.append([price, size])
            
            if not processed_bids or not processed_asks:
                print("⚠️ No valid bids or asks after processing")
                return None
            
            # Sort properly
            processed_bids.sort(key=lambda x: x[0], reverse=True)  # Highest first
            processed_asks.sort(key=lambda x: x[0])  # Lowest first
            
            # Calculate derived metrics
            best_bid = processed_bids[0][0] if processed_bids else 0
            best_ask = processed_asks[0][0] if processed_asks else 0
            mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
            
            return {
                'bids': processed_bids,
                'asks': processed_asks,
                'timestamp': timestamp,
                'symbol': coin,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread': best_ask - best_bid if best_bid and best_ask else 0,
                'spread_pct': ((best_ask - best_bid) / mid_price * 100) if mid_price > 0 else 0
            }
            
        except (ValueError, TypeError, KeyError) as e:
            print(f"⚠️ Failed to convert orderbook format: {e}")
            print(f"   Raw orderbook data: {book_data}")
            self.logger.warning(f"Orderbook format conversion error: {e}")
            return None
    
    async def cleanup(self):
        """Cleanup WebSocket connection"""
        print("🧹 Cleaning up WebSocket connection...")
        self.running = False
        
        if self.info and self.info.ws_manager:
            try:
                # The SDK handles cleanup internally
                print("✅ WebSocket connection cleanup delegated to SDK")
            except Exception as e:
                print(f"⚠️ Error during WebSocket cleanup: {e}")
                self.logger.warning(f"WebSocket cleanup error: {e}")


# Keep the same DataManagerWithWebSocket wrapper class as before
class DataManagerWithWebSocket:
    """Enhanced DataManager that combines REST API with WebSocket feeds"""
    
    def __init__(self, config: TradingConfig, data_manager):
        self.config = config
        self.data_manager = data_manager  # Your existing DataManager instance
        self.ws_manager = WebSocketManager(config)
        self.logger = logging.getLogger(__name__)
        
        # Track if we have real-time data
        self.real_time_enabled = False
        
        print(f"🔌 Enhanced DataManager with corrected WebSocket initialized")
    
    async def initialize(self):
        """Initialize both REST API and WebSocket connections"""
        # Initialize REST API first
        await self.data_manager.initialize()
        
        # Then initialize WebSocket
        try:
            await self.ws_manager.initialize()
            self.real_time_enabled = True
            print("✅ Real-time WebSocket feeds active via official SDK")
        except Exception as e:
            print(f"⚠️ WebSocket failed, falling back to REST API only: {e}")
            self.logger.warning(f"WebSocket initialization failed: {e}")
            self.real_time_enabled = False
    
    def set_trade_callback(self, callback):
        """Set callback for real-time trade data"""
        self.ws_manager.set_trade_callback(callback)
    
    def set_orderbook_callback(self, callback):
        """Set callback for real-time orderbook data"""
        self.ws_manager.set_orderbook_callback(callback)
    
    async def start_real_time_feeds(self):
        """Start real-time data feeds"""
        if self.real_time_enabled:
            print("🚀 Starting real-time data feeds via official SDK...")
            await self.ws_manager.start_listening()
    
    # Delegate all other methods to the original data_manager
    def get_symbol_info(self):
        return self.data_manager.get_symbol_info()
    
    async def get_orderbook(self, symbol: str = None):
        return await self.data_manager.get_orderbook(symbol)
    
    async def get_recent_trades(self, symbol: str = None):
        return await self.data_manager.get_recent_trades(symbol)
    
    async def get_account_info(self, user_address: str):
        return await self.data_manager.get_account_info(user_address)
    
    async def get_open_orders(self, user_address: str):
        return await self.data_manager.get_open_orders(user_address)
    
    async def get_user_fills(self, user_address: str):
        return await self.data_manager.get_user_fills(user_address)
    
    async def cleanup(self):
        """Cleanup both REST and WebSocket connections"""
        await self.data_manager.cleanup()
        await self.ws_manager.cleanup()