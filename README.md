# 🚀 Hyperliquid Market Maker

A production-ready, feature-rich market making bot for Hyperliquid DEX with advanced orderbook analysis, microstructure signals, and risk management.

## ✨ Features

### Core Trading
- 🎯 **Market Making Strategy** - Intelligent bid/ask order placement
- 📊 **Orderbook Analysis** - Real-time order flow and liquidity analysis
- 🧠 **Market Microstructure** - Trade flow analysis and adverse selection detection
- 📡 **WebSocket Integration** - Real-time market data feeds
- 💱 **Hyperliquid SDK** - Native integration with Hyperliquid DEX

### Advanced Features
- 🎓 **Learning Phase** - Calibrate strategy parameters before trading
- 🛡️ **Risk Management** - Stop-loss, trailing stops, profit-taking
- 📈 **Dynamic Spreads** - Market condition-based spread adjustment
- ⚖️ **Position Skewing** - Inventory management and position rebalancing
- 🌊 **Flow Analysis** - Order flow confidence and momentum tracking

### Safety Features
- 🔒 **Environment Variables** - Secure credential management
- 🧪 **Paper Trading Mode** - Test without real money
- 📝 **Comprehensive Logging** - Detailed operation logs
- ⚠️ **Position Limits** - Configurable risk constraints

## 📁 Project Structure

```
Hyperliquid-Market-Making/
│
├── main.py                      # Main entry point
├── config.py                    # Configuration management
├── strategy.py                  # Trading strategy with risk management
│
├── core/                        # Core trading modules
│   ├── data_manager.py         # Market data fetching
│   ├── trading_client.py       # Order execution
│   ├── position_tracker.py     # Position & order tracking
│   └── websocket_manager.py    # Real-time data feeds
│
├── analysis/                    # Market analysis
│   ├── market_microstructure.py # Microstructure analysis
│   └── orderbook_analyzer.py    # Orderbook analytics
│
├── utils/                       # Utilities
│   └── test_connection.py      # Connection testing
│
├── .env                         # Environment variables (create from .env.example)
├── .env.example                 # Template for environment variables
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Hyperliquid account
- API credentials (private key)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Hyperliquid-Market-Making
   ```

2. **Install dependencies:**
   ```bash
   pip install hyperliquid-python-sdk eth-account numpy websockets python-dotenv
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Configure `.env` file:**
   ```env
   HYPERLIQUID_PRIVATE_KEY=your_private_key_here
   MASTER_WALLET_ADDRESS=your_wallet_address_here
   ENABLE_TRADING=False  # Set to True for live trading
   TESTNET=False         # Set to True for testnet
   SYMBOL=LINK          # Trading symbol
   ```

### Testing Connection

Before running the bot, test your connection:

```bash
python utils/test_connection.py
```

This will verify:
- ✅ Credentials loaded correctly
- ✅ API connection works
- ✅ Account accessible
- ✅ Can fetch positions and orders

### Running the Bot

**Paper Trading (Recommended First):**
```bash
# Make sure ENABLE_TRADING=False in .env
python main.py
```

**Live Trading:**
```bash
# Set ENABLE_TRADING=True in .env
python main.py
```

## ⚙️ Configuration

Key configuration options in `config.py`:

### Trading Parameters
```python
SYMBOL = "LINK"                    # Trading pair
BASE_SPREAD = 0.002                # 0.2% base spread
ORDER_SIZE_PCT = 1.0               # 1% of account per order
MAX_POSITION_PCT = 10.0            # Max 10% of account in position
MIN_ORDER_SIZE = 0.01              # Minimum order size
```

### Risk Management
```python
ENABLE_STOP_LOSS = True            # Enable stop-loss
STOP_LOSS_PCT = 2.0                # 2% stop-loss
TRAILING_STOP_LOSS = True          # Enable trailing stops
PROFIT_TARGET_PCT = 1.5            # 1.5% profit target
```

### Learning Phase
```python
ENABLE_LEARNING_PHASE = True       # Enable learning mode
LEARNING_PHASE_DURATION = 1800     # 30 minutes
MIN_ORDERBOOK_SNAPSHOTS = 100      # Minimum data to collect
```

## 🎓 Learning Phase

The bot includes a learning phase that:
1. Observes market for configured duration
2. Collects orderbook patterns and spread statistics
3. Analyzes volume imbalances and liquidity distribution
4. Calibrates adverse selection thresholds
5. Establishes microstructure baselines

**Benefits:**
- Better risk assessment
- Optimized spread placement
- Market-aware order sizing
- Reduced adverse selection

## 📊 Strategy Overview

### Order Placement
1. **Fair Price Calculation** - Volume-weighted mid using orderbook depth
2. **Dynamic Spreads** - Adjusted based on volatility, liquidity, and conditions
3. **Gap Analysis** - Places orders in orderbook gaps for better fill probability
4. **Size Optimization** - Condition-based sizing (calm = larger, volatile = smaller)

### Risk Management
- **Stop-Loss**: Automatic position closure on excessive loss
- **Trailing Stops**: Lock in profits as position moves favorably
- **Profit Taking**: Partial exits at predetermined profit levels
- **Position Skewing**: Encourages inventory rebalancing

### Market Conditions
The strategy adapts to detected market conditions:
- **CALM**: Tighter spreads, larger sizes
- **NORMAL**: Base parameters
- **TRENDING**: Wider spreads, moderate sizes
- **VOLATILE**: Much wider spreads, smaller sizes
- **ILLIQUID**: Skip trading, wait for better conditions

## 🔍 Monitoring

The bot provides real-time status updates:

```
📊 ENHANCED STATUS REPORT
--------------------------------------------------
💰 Account Value: $10,000.00
📊 Position: 25.0000 LINK (4.5% of account)
💹 Unrealized PnL: $45.67
📋 Open Orders: 4
💰 Enhanced Fair Price: $18.2345

🧠 Microstructure Analysis:
   - Flow Confidence: 0.725
   - Overall Momentum: 0.145
   - Adverse Risk: 0.234
   - Volume Imbalance: -0.123

🛡️ Risk Management Status:
   - Stop-Loss Distance: 1.45%
   - Profit Target Distance: 0.87%
   - Risk Level: 🟢 LOW
```

## 🧪 Testing

### Connection Test
```bash
python utils/test_connection.py
```

### Paper Trading
Set `ENABLE_TRADING=False` in `.env` to run without executing real trades.

### Testnet
Set `TESTNET=True` in `.env` to use Hyperliquid testnet.

## 🛡️ Security

- Never commit `.env` file (already in `.gitignore`)
- Keep private keys secure
- Use environment variables for all secrets
- Start with paper trading and small positions
- Monitor the bot actively, especially initially

## 📈 Performance Optimization

The bot includes several optimizations:
- Cached calculations for frequently-used values
- Efficient orderbook analysis algorithms
- Batched API calls where possible
- WebSocket for real-time data (reduces polling)

## 🐛 Troubleshooting

### Bot won't start
- Check `.env` file is properly configured
- Verify credentials with `python utils/test_connection.py`
- Ensure all dependencies installed

### No orders being placed
- Check `ENABLE_TRADING` is set to `True`
- Verify account has sufficient balance
- Check logs for specific error messages
- Market conditions might not be favorable

### Import errors
- Ensure running from project root directory
- Check Python version (3.8+ required)
- Verify all dependencies installed

## 📚 Advanced Usage

### Custom Strategy Parameters

Edit `config.py` to customize:
- Spread calculation
- Order sizing logic
- Risk management thresholds
- Learning phase duration

### Multiple Symbols

Run multiple instances with different symbols:
```bash
# Terminal 1
SYMBOL=LINK python main.py

# Terminal 2
SYMBOL=ETH python main.py
```

## 🔄 Recent Updates

**Codebase Cleanup (Latest)**
- Consolidated 18 files → 11 files (39% reduction)
- Organized into logical folder structure
- Single entry point (`main.py`)
- Unified strategy file with all features
- See `MIGRATION_GUIDE.md` for details

## 📝 License

This project is provided as-is for educational and trading purposes.

## ⚠️ Disclaimer

**Trading cryptocurrencies carries significant risk. This bot is provided as-is without any guarantees. Use at your own risk. Always:**
- Start with paper trading
- Test thoroughly on testnet
- Use small positions initially
- Monitor actively
- Understand the code before using
- Never risk more than you can afford to lose

## 🤝 Contributing

Contributions welcome! Please:
1. Test changes thoroughly
2. Follow existing code style
3. Update documentation
4. Create detailed pull requests

## 📞 Support

For issues or questions:
1. Check `MIGRATION_GUIDE.md` for recent changes
2. Review logs for error messages
3. Test connection with `utils/test_connection.py`
4. Open an issue with detailed information

---

**Happy Trading! 🚀📈**
