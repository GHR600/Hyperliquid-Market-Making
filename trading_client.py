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
        
        print(f"💱 Initializing TradingClient...")
        
        # Initialize exchange client
        base_url = constants.TESTNET_API_URL if config.TESTNET else constants.MAINNET_API_URL
        print(f"   🌐 Using {'TESTNET' if config.TESTNET else 'MAINNET'} API: {base_url}")
        
        if config.PRIVATE_KEY:
            try:
                # Create account from private key
                print("   🔐 Creating account from private key...")
                account = Account.from_key(config.PRIVATE_KEY)
                self.exchange = Exchange(account, base_url=base_url)
                self.user_address = account.address
                
                print(f"   ✅ Trading account initialized")
                print(f"   👤 Address: {self.user_address}")
                
                if config.ENABLE_TRADING:
                    print("   🚨 LIVE TRADING ENABLED")
                else:
                    print("   📝 Paper trading mode (ENABLE_TRADING=False)")
                
                self.logger.info(f"Initialized trading client for address: {self.user_address}")
            except Exception as e:
                print(f"   ❌ Failed to initialize trading account: {e}")
                self.exchange = None
                self.user_address = None
                raise
        else:
            print("   ⚠️  No private key provided - trading disabled")
            self.exchange = None
            self.user_address = None
            self.logger.warning("No private key provided - trading disabled")
    
    async def place_orders(self, orders: List[Dict]) -> List[Optional[str]]:
        """Place multiple orders with detailed logging"""
        print(f"\n📦 PLACING {len(orders)} ORDERS")
        print("-" * 30)
        
        if not self.exchange or not self.config.ENABLE_TRADING:
            print("📝 Paper trading mode - simulating order placement")
            paper_order_ids = []
            for i, order in enumerate(orders):
                paper_id = f"paper_order_{i}_{asyncio.get_event_loop().time()}"
                paper_order_ids.append(paper_id)
                side_text = "BUY" if order['is_buy'] else "SELL"
                print(f"   📄 Paper order {i+1}: {side_text} {order['sz']:.2f} @ ${order['limit_px']:.5f} -> ID: {paper_id}")
            
            self.logger.info(f"Paper trading: Would place {len(orders)} orders")
            return paper_order_ids
        
        print(f"🚨 LIVE TRADING - Placing {len(orders)} real orders")
        order_ids = []
        
        try:
            # Place orders individually using the correct SDK format
            for i, order in enumerate(orders):
                print(f"\n   📋 Order {i+1}/{len(orders)}:")
                side_text = "BUY" if order['is_buy'] else "SELL"
                print(f"      {side_text} {order['sz']:.2f} {order['coin']} @ ${order['limit_px']:.5f}")
                
                try:
                    # Use the correct exchange.order() method signature
                    print(f"      🔄 Submitting to exchange...")
                    response = self.exchange.order(
                        self.config.SYMBOL,           # asset symbol as first parameter
                        order['is_buy'],              # True for buy, False for sell
                        order['sz'],                  # size as float
                        order['limit_px'],            # price as float
                        order['order_type'],          # order type dict
                        reduce_only=order.get('reduce_only', False)
                    )
                    
                    print(f"      📡 Response received: {response}")
                    
                    if response and response.get('status') == 'ok':
                        # Extract order ID from response
                        statuses = response.get('response', {}).get('data', {}).get('statuses', [])
                        if statuses and len(statuses) > 0:
                            status = statuses[0]
                            if 'resting' in status:
                                order_id = status['resting']['oid']
                                order_ids.append(order_id)
                                print(f"      ✅ Order placed successfully!")
                                print(f"         Order ID: {order_id}")
                                self.logger.info(f"Order {i+1} placed successfully: {order_id}")
                            else:
                                order_ids.append(None)
                                print(f"      ⚠️  Order not resting: {status}")
                                self.logger.warning(f"Order {i+1} not resting: {status}")
                        else:
                            order_ids.append(None)
                            print(f"      ❌ No status in response")
                            self.logger.warning(f"Order {i+1} - no status in response")
                    else:
                        order_ids.append(None)
                        print(f"      ❌ Order failed: {response}")
                        self.logger.error(f"Order {i+1} failed: {response}")
                        
                except Exception as e:
                    print(f"      ❌ Exception placing order: {e}")
                    self.logger.error(f"Error placing order {i+1}: {e}")
                    order_ids.append(None)
            
            successful_orders = len([oid for oid in order_ids if oid])
            print(f"\n📊 ORDER PLACEMENT SUMMARY:")
            print(f"   ✅ Successful: {successful_orders}/{len(orders)}")
            print(f"   ❌ Failed: {len(orders) - successful_orders}/{len(orders)}")
            
            self.logger.info(f"Placed {successful_orders}/{len(orders)} orders successfully")
            return order_ids
                
        except Exception as e:
            print(f"❌ CRITICAL ERROR in order placement: {e}")
            self.logger.error(f"Error in order placement: {e}")
            return [None] * len(orders)
    
    async def cancel_orders(self, order_ids: List[str]) -> bool:
        """Cancel orders one by one using single order cancel"""
        print(f"\n❌ CANCELLING {len(order_ids)} ORDERS (ONE BY ONE)")
        print("-" * 30)
        
        if not self.exchange or not self.config.ENABLE_TRADING:
            print("📝 Paper trading mode - simulating order cancellation")
            for i, order_id in enumerate(order_ids):
                print(f"   📄 Paper cancel {i+1}: {order_id}")
            self.logger.info(f"Paper trading: Would cancel orders {order_ids}")
            return True
        
        if not order_ids:
            print("⚠️ No orders to cancel")
            return True
        
        print(f"🚨 LIVE TRADING - Cancelling {len(order_ids)} orders individually")
        
        successful_cancels = 0
        failed_cancels = 0
        
        for i, order_id in enumerate(order_ids):
            try:
                print(f"   🔄 Cancelling order {i+1}/{len(order_ids)}: {order_id}")
                
                # Convert order_id to int if it's a string (common Hyperliquid requirement)
                try:
                    oid_param = int(order_id)
                    print(f"      Using integer oid: {oid_param}")
                except ValueError:
                    oid_param = order_id
                    print(f"      Using string oid: {oid_param}")
                
                # Call exchange.cancel() with single oid parameter
                response = self.exchange.cancel(oid=oid_param)
                
                print(f"      📡 Response: {response}")
                
                # Check if cancellation was successful
                if response and response.get('status') == 'ok':
                    successful_cancels += 1
                    print(f"      ✅ Order {order_id} cancelled successfully")
                    self.logger.info(f"Successfully cancelled order {order_id}")
                else:
                    failed_cancels += 1
                    print(f"      ❌ Order {order_id} cancel failed: {response}")
                    self.logger.warning(f"Failed to cancel order {order_id}: {response}")
                    
            except Exception as e:
                failed_cancels += 1
                print(f"      ❌ Exception cancelling order {order_id}: {e}")
                self.logger.error(f"Exception cancelling order {order_id}: {e}")
                
                # Try alternative format as fallback
                try:
                    print(f"      🔄 Trying alternative format for {order_id}...")
                    # Some SDKs expect exchange.cancel(coin, oid)
                    alt_response = self.exchange.cancel(self.config.SYMBOL, order_id)
                    
                    if alt_response and alt_response.get('status') == 'ok':
                        successful_cancels += 1
                        failed_cancels -= 1  # Correct the count
                        print(f"      ✅ Order {order_id} cancelled with alternative method")
                    else:
                        print(f"      ❌ Alternative method also failed for {order_id}")
                        
                except Exception as alt_error:
                    print(f"      ❌ Alternative method exception: {alt_error}")
        
        print(f"\n📊 CANCELLATION SUMMARY:")
        print(f"   ✅ Successful: {successful_cancels}/{len(order_ids)}")
        print(f"   ❌ Failed: {failed_cancels}/{len(order_ids)}")
        
        # Consider it successful if we cancelled more than half
        success = successful_cancels > len(order_ids) // 2
        
        if successful_cancels > 0:
            self.logger.info(f"Cancelled {successful_cancels}/{len(order_ids)} orders")
        
        if failed_cancels > 0:
            self.logger.warning(f"Failed to cancel {failed_cancels}/{len(order_ids)} orders")
        
        return success