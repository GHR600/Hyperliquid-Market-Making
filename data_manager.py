
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
        
    async def initialize(self):
        """Initialize the data manager"""
        self.logger.info(f"Initializing DataManager on {'testnet' if self.config.TESTNET else 'mainnet'}")
        
        # Test connection
        try:
            meta = self.info.meta()
            self.logger.info(f"Connected to Hyperliquid. Universe size: {len(meta.get('universe', []))}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Hyperliquid: {e}")
            raise
        
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("DataManager cleanup complete")
    
    async def get_orderbook(self, symbol: str = None) -> Optional[Dict]:
        """Fetch current orderbook data"""
        try:
            coin = symbol or self.config.SYMBOL
            
            # Get L2 orderbook
            book = self.info.l2_snapshot(coin)
            
            if not book or 'levels' not in book:
                self.logger.warning(f"No orderbook data for {coin}")
                return None
                
            return self._process_orderbook(book)
                    
        except Exception as e:
            self.logger.error(f"Error fetching orderbook for {coin}: {e}")
            return None
    
    def _process_orderbook(self, raw_data: Dict) -> Dict:
        """Process raw orderbook data from Hyperliquid SDK"""
        try:
            levels = raw_data.get('levels', [])
            if not levels or len(levels) < 2:
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
            
            return {
                'bids': bids,
                'asks': asks,
                'timestamp': raw_data.get('time', 0),
                'symbol': self.config.SYMBOL
            }
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook: {e}")
            return {}
    
    async def get_account_info(self, user_address: str) -> Optional[Dict]:
        """Fetch account information and positions"""
        try:
            # Get clearing house state
            account_state = self.info.user_state(user_address)
            return account_state
                    
        except Exception as e:
            self.logger.error(f"Error fetching account info: {e}")
            return None
    
    async def get_open_orders(self, user_address: str) -> List[Dict]:
        """Get open orders for user"""
        try:
            orders = self.info.open_orders(user_address)
            return orders or []
        except Exception as e:
            self.logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_user_fills(self, user_address: str) -> List[Dict]:
        """Get recent fills for user"""
        try:
            fills = self.info.user_fills(user_address)
            return fills or []
        except Exception as e:
            self.logger.error(f"Error fetching user fills: {e}")
            return []