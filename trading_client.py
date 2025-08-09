
import asyncio
import logging
from typing import Dict, List, Optional
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from eth_account import Account
from config import TradingConfig

class TradingClient:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize exchange client
        base_url = constants.TESTNET_API_URL if config.TESTNET else constants.MAINNET_API_URL
        
        if config.PRIVATE_KEY:
            # Create account from private key
            account = Account.from_key(config.PRIVATE_KEY)
            self.exchange = Exchange(account, base_url=base_url)
            self.user_address = account.address
            self.logger.info(f"Initialized trading client for address: {self.user_address}")
        else:
            self.exchange = None
            self.user_address = None
            self.logger.warning("No private key provided - trading disabled")
    
    async def place_orders(self, orders: List[Dict]) -> List[Optional[str]]:
        """Place multiple orders"""
        if not self.exchange or not self.config.ENABLE_TRADING:
            self.logger.info(f"Paper trading: Would place {len(orders)} orders")
            return [f"paper_order_{i}_{asyncio.get_event_loop().time()}" for i in range(len(orders))]
        
        order_ids = []
        
        try:
            # Place orders individually using the correct SDK format
            for i, order in enumerate(orders):
                try:
                    # Use the correct exchange.order() method signature from examples
                    # First parameter is the coin/asset symbol directly
                    response = self.exchange.order(
                        self.config.SYMBOL,           # asset symbol as first parameter
                        order['is_buy'],              # True for buy, False for sell
                        order['sz'],                  # size as float
                        order['limit_px'],            # price as float
                        order['order_type'],          # order type dict
                        reduce_only=order.get('reduce_only', False)
                    )
                    
                    if response and response.get('status') == 'ok':
                        # Extract order ID from response
                        statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                        if statuses and len(statuses) > 0:
                            status = statuses[0]
                            if 'resting' in status:
                                order_id = status['resting']['oid']
                                order_ids.append(order_id)
                                self.logger.info(f"Order {i+1} placed successfully: {order_id}")
                            else:
                                order_ids.append(None)
                                self.logger.warning(f"Order {i+1} not resting: {status}")
                        else:
                            order_ids.append(None)
                            self.logger.warning(f"Order {i+1} - no status in response")
                    else:
                        order_ids.append(None)
                        self.logger.error(f"Order {i+1} failed: {response}")
                        
                except Exception as e:
                    self.logger.error(f"Error placing order {i+1}: {e}")
                    order_ids.append(None)
            
            successful_orders = len([oid for oid in order_ids if oid])
            self.logger.info(f"Placed {successful_orders}/{len(orders)} orders successfully")
            return order_ids
                
        except Exception as e:
            self.logger.error(f"Error in order placement: {e}")
            return [None] * len(orders)
    
    async def _place_orders_individually(self, orders: List[Dict]) -> List[Optional[str]]:
        """Fallback method to place orders individually with simpler format"""
        order_ids = []
        
        for i, order in enumerate(orders):
            try:
                # Try the simplest possible format
                simple_order = {
                    "a": self.config.SYMBOL,
                    "b": order['is_buy'],
                    "p": str(order['limit_px']),
                    "s": str(order['sz']),
                    "r": False,
                    "t": {"limit": {"tif": "Gtc"}}
                }
                
                response = self.exchange.order([simple_order])  # SDK expects a list
                
                if response and response.get('status') == 'ok':
                    statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                    if statuses and 'resting' in statuses[0]:
                        order_ids.append(statuses[0]['resting']['oid'])
                        self.logger.info(f"Individual order {i+1} placed successfully")
                    else:
                        order_ids.append(None)
                        self.logger.warning(f"Individual order {i+1} failed: {statuses}")
                else:
                    order_ids.append(None)
                    self.logger.error(f"Individual order {i+1} failed: {response}")
                    
            except Exception as e:
                self.logger.error(f"Error placing individual order {i+1}: {e}")
                order_ids.append(None)
        
        return order_ids
   
    
    async def cancel_orders(self, order_ids: List[str]) -> bool:
        """Cancel multiple orders"""
        if not self.exchange or not self.config.ENABLE_TRADING:
            self.logger.info(f"Paper trading: Would cancel orders {order_ids}")
            return True
        
        try:
            # Format for Hyperliquid cancel request
            cancels = [{'coin': self.config.SYMBOL, 'oid': oid} for oid in order_ids]
            
            response = self.exchange.cancel(cancels)
            
            if response and response.get('status') == 'ok':
                self.logger.info(f"Cancelled {len(order_ids)} orders successfully")
                return True
            else:
                self.logger.error(f"Failed to cancel orders: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")
            return False