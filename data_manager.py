import asyncio
import logging
from typing import Dict, Optional, List
from hyperliquid.info import Info
from hyperliquid.utils import constants
from config import TradingConfig

class DataManager:
    def __init__(self, config: TradingConfig):
        self.config = config
        # Initialize Hyperliquid Info client for market data
        base_url = constants.TESTNET_API_URL if config.TESTNET else constants.MAINNET_API_URL
        self.info = Info(base_url=base_url, skip_ws=True)
        self.logger = logging.getLogger(__name__)
        
        # Track last seen trade to avoid duplicates
        self.last_trade_timestamp = 0
        
    async def initialize(self):
        """Initialize the data manager"""
        print(f"🔌 Initializing DataManager on {'testnet' if self.config.TESTNET else 'mainnet'}")
        self.logger.info(f"Initializing DataManager on {'testnet' if self.config.TESTNET else 'mainnet'}")
        
        # Test connection
        try:
            print("🔍 Testing connection to Hyperliquid...")
            meta = self.info.meta()
            universe_size = len(meta.get('universe', []))
            print(f"✅ Connected to Hyperliquid successfully")
            print(f"   - Universe size: {universe_size} markets")
            print(f"   - Target symbol: {self.config.SYMBOL}")
            
            # Fetch and update symbol-specific parameters
            await self._fetch_symbol_parameters(meta)
            
            # Verify our symbol exists
            symbols = [coin['name'] for coin in meta.get('universe', [])]
            if self.config.SYMBOL in symbols:
                print(f"✅ Symbol {self.config.SYMBOL} found in universe")
            else:
                print(f"⚠️  Warning: Symbol {self.config.SYMBOL} not found in universe")
                print(f"   Available symbols: {symbols[:10]}..." if len(symbols) > 10 else f"   Available symbols: {symbols}")
            
            self.logger.info(f"Connected to Hyperliquid. Universe size: {universe_size}")
        except Exception as e:
            print(f"❌ Failed to connect to Hyperliquid: {e}")
            self.logger.error(f"Failed to connect to Hyperliquid: {e}")
            raise
        
    async def _fetch_symbol_parameters(self, meta_data: Dict):
        """Fetch symbol-specific parameters and update config"""
        print(f"🔍 Fetching parameters for {self.config.SYMBOL}...")
        
        try:
            # Find our symbol in the universe
            symbol_info = None
            for asset in meta_data.get("universe", []):
                if asset.get("name") == self.config.SYMBOL:
                    symbol_info = asset
                    break
            
            if not symbol_info:
                print(f"⚠️  Symbol {self.config.SYMBOL} not found in universe - using defaults")
                return
            
        
            # Extract size decimals
            size_decimals = symbol_info.get("szDecimals")
            if size_decimals is not None:
                self.config.SIZE_DECIMALS = int(size_decimals)
                print(f"   📏 Size decimals: {self.config.SIZE_DECIMALS}")
                
                # Calculate price decimals based on Hyperliquid rules
                # For perps: MAX_DECIMALS (6) - szDecimals
                # For spot: MAX_DECIMALS (8) - szDecimals  
                is_spot = symbol_info.get("type") == "spot"  # Check if this field exists

                MAX_DECIMALS = 8 if is_spot else 6  # Assuming perps, change to 8 for spot
                self.config.PRICE_DECIMALS = MAX_DECIMALS - self.config.SIZE_DECIMALS
                print(f"   💰 Price decimals: {self.config.PRICE_DECIMALS} (calculated: {MAX_DECIMALS} - {self.config.SIZE_DECIMALS})")
            else:
                print(f"   ⚠️  Size decimals not found - using defaults")
        

            # Extract size decimals
            size_decimals = symbol_info.get("szDecimals")
            if size_decimals is not None:
                self.config.SIZE_DECIMALS = int(size_decimals)
                print(f"   📏 Size decimals: {self.config.SIZE_DECIMALS}")
            else:
                print(f"   ⚠️  Size decimals not found - using default: {self.config.SIZE_DECIMALS}")
            
            # Extract max leverage
            max_leverage = symbol_info.get("maxLeverage")
            if max_leverage is not None:
                self.config.MAX_LEVERAGE = float(max_leverage)
                # Update max position to use max leverage
                #self.config.MAX_POSITION_PCT = self.config.MAX_LEVERAGE  ##------THIS ENABLES MANUAL OVERIDE-----
                print(f"   ⚡ Max leverage: {self.config.MAX_LEVERAGE}x")
                print(f"   📊 Max position updated to: {self.config.MAX_POSITION_PCT}x")
            else:
                print(f"   ⚠️  Max leverage not found - using default: {self.config.MAX_LEVERAGE}x")
            
            # Log other useful symbol info
            if symbol_info.get("onlyIsolated"):
                print(f"   ⚠️  Symbol is isolated margin only")
            
            # Check if there are any trading restrictions
            if "maxLeverage" in symbol_info and symbol_info["maxLeverage"] == 1:
                print(f"   ⚠️  Symbol has no leverage (spot only)")
            
            self.logger.info(f"Symbol parameters: decimals={self.config.SIZE_DECIMALS}, max_leverage={self.config.MAX_LEVERAGE}")
            
        except Exception as e:
            print(f"❌ Error fetching symbol parameters: {e}")
            self.logger.error(f"Error fetching symbol parameters: {e}")
            print(f"   📋 Using default values: decimals={self.config.SIZE_DECIMALS}, leverage={self.config.MAX_LEVERAGE}")
    
    def get_symbol_info(self) -> Dict[str, any]:
        """Get current symbol configuration"""
        return {
            'symbol': self.config.SYMBOL,
            'size_decimals': self.config.SIZE_DECIMALS,
            'price_decimals': self.config.PRICE_DECIMALS,
            'max_leverage': self.config.MAX_LEVERAGE,
            'max_position_pct': self.config.MAX_POSITION_PCT
        }


    async def cleanup(self):
        """Cleanup resources"""
        print("🧹 DataManager cleanup complete")
        self.logger.info("DataManager cleanup complete")
    
    async def get_orderbook(self, symbol: str = None) -> Optional[Dict]:
        """Fetch current orderbook data"""
        coin = symbol or self.config.SYMBOL
        print(f"📊 Fetching orderbook for {coin}...")
        
        try:
            # Get L2 orderbook
            book = self.info.l2_snapshot(coin)
            
            if not book or 'levels' not in book:
                print(f"⚠️  No orderbook data received for {coin}")
                self.logger.warning(f"No orderbook data for {coin}")
                return None
            
            processed_book = self._process_orderbook(book)

            if processed_book:
                # Detect and store tick size
                tick_size = self._detect_tick_size(processed_book)
                processed_book['tick_size'] = tick_size  # Add this
                print(f"✅ Orderbook fetched - Mid: ${processed_book.get('mid_price', 0):.5f}, Tick: ${tick_size}")
            
            return processed_book
                    
        except Exception as e:
            print(f"❌ Error fetching orderbook for {coin}: {e}")
            self.logger.error(f"Error fetching orderbook for {coin}: {e}")
            return None
    
    def _process_orderbook(self, raw_data: Dict) -> Dict:
        """Process raw orderbook data from Hyperliquid SDK"""
        try:
            levels = raw_data.get('levels', [])
            if not levels or len(levels) < 2:
                print("⚠️  Insufficient orderbook levels received")
                return {}
            
            # Hyperliquid returns [bids, asks] format
            raw_bids = levels[0] if len(levels) > 0 else []
            raw_asks = levels[1] if len(levels) > 1 else []
            
            # Convert to [price, size] format
            bids = [[float(bid['px']), float(bid['sz'])] for bid in raw_bids]
            asks = [[float(ask['px']), float(ask['sz'])] for ask in raw_asks]
            
            # Sort bids (highest first) and asks (lowest first)
            bids.sort(key=lambda x: x[0], reverse=True)
            asks.sort(key=lambda x: x[0])
            
            if not bids or not asks:
                print("⚠️  No valid bids or asks after processing")
                return {}
            
            # Calculate derived metrics
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0
            
            result = {
                'bids': bids,
                'asks': asks,
                'timestamp': raw_data.get('time', 0),
                'symbol': self.config.SYMBOL,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread': spread,
                'spread_pct': spread_pct
            }
            
            print(f"   📋 Processed orderbook: {len(bids)} bids, {len(asks)} asks")
            return result
            
        except Exception as e:
            print(f"❌ Error processing orderbook: {e}")
            self.logger.error(f"Error processing orderbook: {e}")
            return {}
    
    async def get_recent_trades(self, symbol: str = None) -> List[Dict]:
        """Fetch recent trades (time and sales) data"""
        coin = symbol or self.config.SYMBOL
        print(f"💹 Fetching recent trades for {coin}...")
        
        try:
            # Get recent trades from Hyperliquid - correct method name
            # Try different possible method names
            if hasattr(self.info, 'recent_trades'):
                recent_trades_data = self.info.recent_trades(coin)
            elif hasattr(self.info, 'user_fills'):
                # Fallback - this gets fills but might not be public trades
                print(f"   ⚠️  Using user_fills as fallback for trade data")
                recent_trades_data = {'trades': []}  # Return empty for now
            elif hasattr(self.info, 'candles'):
                # Another fallback - get candle data instead
                print(f"   ⚠️  recent_trades not available, using candles as proxy")
                recent_trades_data = {'trades': []}  # Return empty for now
            else:
                print(f"   ❌ No trade data method available in SDK")
                return []
            
            # Let's also try to find what methods are actually available
            print(f"   🔍 Available Info methods: {[method for method in dir(self.info) if not method.startswith('_')]}")
            
            if not recent_trades_data or 'trades' not in recent_trades_data:
                print(f"⚠️  No trade data received for {coin}")
                return []
            
            trades = recent_trades_data.get('trades', [])
            print(f"✅ Fetched {len(trades)} recent trades")
            
            # Filter out trades we've already seen
            new_trades = []
            for trade in trades:
                timestamp = trade.get('timestamp', 0)
                if timestamp > self.last_trade_timestamp:
                    new_trades.append(trade)
            
            if new_trades:
                # Update last seen timestamp
                self.last_trade_timestamp = max(trade.get('timestamp', 0) for trade in new_trades)
                print(f"   📈 {len(new_trades)} new trades since last update")
                
                # Log sample of recent trades
                for i, trade in enumerate(new_trades[-3:]):  # Show last 3 trades
                    price = trade.get('price')
                    size = trade.get('size')
                    side = trade.get('side')
                    side_text = "At Ask (Buy)" if side == "B" else "At Bid (Sell)" if side == "A" else "Unknown"
                    print(f"   Trade {i+1}: ${price} size={size} {side_text}")
            else:
                print("   📊 No new trades since last update")
            
            return new_trades
                    
        except Exception as e:
            print(f"❌ Error fetching recent trades for {coin}: {e}")
            self.logger.error(f"Error fetching recent trades for {coin}: {e}")
            
            # Let's debug what's actually available
            print(f"   🔧 Debug: Available Info object methods:")
            methods = [method for method in dir(self.info) if not method.startswith('_') and callable(getattr(self.info, method))]
            for method in methods[:10]:  # Show first 10 methods
                print(f"      - {method}")
            if len(methods) > 10:
                print(f"      ... and {len(methods) - 10} more methods")
            
            return []
    
    async def get_account_info(self, user_address: str) -> Optional[Dict]:
        """Fetch account information and positions"""
        print(f"👤 Fetching account info for {user_address[:10]}...")
        
        try:
            # Get clearing house state
            account_state = self.info.user_state(user_address)
            
            if account_state:
                print("✅ Account info retrieved successfully")
                
                # Log account summary
                margin_summary = account_state.get('marginSummary', {})
                account_value = float(margin_summary.get('accountValue', 0))
                
                if account_value > 0:
                    print(f"   💰 Account value: ${account_value:.2f}")
                
                # Log positions
                asset_positions = account_state.get('assetPositions', [])
                active_positions = []
                for pos_data in asset_positions:
                    position_info = pos_data.get('position', {})
                    coin = position_info.get('coin', '')
                    size = float(position_info.get('szi', 0))
                    if abs(size) > 0.0001:  # Only show significant positions
                        active_positions.append(f"{coin}: {size}")
                
                if active_positions:
                    print(f"   📊 Active positions: {', '.join(active_positions)}")
                else:
                    print("   📊 No active positions")
            else:
                print("⚠️  No account data received")
            
            return account_state
                    
        except Exception as e:
            print(f"❌ Error fetching account info: {e}")
            self.logger.error(f"Error fetching account info: {e}")
            return None
    
    async def get_open_orders(self, user_address: str) -> List[Dict]:
        """Get open orders for user"""
        print(f"📋 Fetching open orders for {user_address[:10]}...")
        
        try:
            orders = self.info.open_orders(user_address)
            order_list = orders or []
            
            print(f"✅ Found {len(order_list)} open orders")
            print(f"🔍 Raw API response: {orders}")  # Add this line

            #Log each order
            for i, order in enumerate(order_list):
                oid = order.get('oid', 'N/A')
                coin = order.get('coin', 'N/A') 
                side = order.get('side', 'N/A')
                size = order.get('sz', 'N/A')
                price = order.get('limitPx', 'N/A')
                print(f"   📋 Order {i+1}: {oid} | {coin} | {side} | {size} @ ${price}")

            
            # Log order summary
            if order_list:
                for i, order in enumerate(order_list[:5]):  # Show first 5 orders
                    coin = order.get('coin', '')
                    side = 'BUY' if order.get('side') == 'B' else 'SELL'
                    size = order.get('sz', '')
                    price = order.get('limitPx', '')
                    print(f"   Order {i+1}: {side} {size} {coin} @ ${price}")
                
                if len(order_list) > 5:
                    print(f"   ... and {len(order_list) - 5} more orders")
            
            return order_list
            
        except Exception as e:
            print(f"❌ Error fetching open orders: {e}")
            self.logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_user_fills(self, user_address: str) -> List[Dict]:
        """Get recent fills for user"""
        print(f"🎯 Fetching recent fills for {user_address[:10]}...")
        
        try:
            fills = self.info.user_fills(user_address)
            fill_list = fills or []
            
            print(f"✅ Found {len(fill_list)} recent fills")
            
            # Log fill summary
            if fill_list:
                for i, fill in enumerate(fill_list[:3]):  # Show first 3 fills
                    coin = fill.get('coin', '')
                    side = fill.get('side', '')
                    size = fill.get('sz', '')
                    price = fill.get('px', '')
                    print(f"   Fill {i+1}: {side} {size} {coin} @ ${price}")
            
            return fill_list
            
        except Exception as e:
            print(f"❌ Error fetching user fills: {e}")
            self.logger.error(f"Error fetching user fills: {e}")
            return []
        
    def _detect_tick_size(self, orderbook: Dict) -> float:
        """Detect tick size by analyzing current orderbook prices"""
        try:
            bids = orderbook.get('bids', [])
            if len(bids) >= 2:
                # Calculate difference between consecutive bid levels
                price_diffs = []
                for i in range(min(5, len(bids)-1)):  # Check first 5 levels
                    diff = abs(bids[i][0] - bids[i+1][0])
                    if diff > 0:
                        price_diffs.append(diff)
                
                if price_diffs:
                    # The minimum difference is likely the tick size
                    tick_size = min(price_diffs)
                    print(f"   📏 Detected tick size: ${tick_size}")
                    return tick_size
        except:
            pass
        
        # Fallback for BTC
        return 1