# Dashboard Quick Start Guide

This guide will get you up and running with the Grafana dashboard in minutes.

## ✅ Prerequisites Checklist

Run the verification script first:
```bash
python verify_dashboard_setup.py
```

This checks:
- ✅ Python packages installed (influxdb-client, flask, flask-cors)
- ✅ All required files present
- ✅ Configuration files valid
- ⚠️ Environment variables (optional until InfluxDB setup)

## 🚀 Quick Setup (5 minutes)

### Step 1: Download InfluxDB & Grafana

**InfluxDB:**
1. Download from https://portal.influxdata.com/downloads/
2. Extract to `C:\influxdb`

**Grafana:**
1. Download from https://grafana.com/grafana/download
2. Extract to `C:\grafana`

### Step 2: Start All Services

**Windows:**
```cmd
start_dashboard.bat
```

This will:
- ✅ Start InfluxDB on http://localhost:8086
- ✅ Start Grafana on http://localhost:3000
- ✅ Start Control API on http://localhost:5000
- ✅ Open browser to Grafana

### Step 3: Configure InfluxDB (First Time Only)

1. Go to http://localhost:8086 (automatically opened)
2. Click "Get Started"
3. Fill in:
   - Username: `admin`
   - Password: `admin123` (or your choice)
   - Organization: `trading`
   - Bucket: `metrics`
4. Click "Continue"
5. **IMPORTANT**: Copy the API token shown
6. Click "Configure Later"

### Step 4: Set Environment Variable

**Windows PowerShell:**
```powershell
# Set for current session
$env:INFLUXDB_TOKEN="paste-your-token-here"

# Make permanent
[System.Environment]::SetEnvironmentVariable('INFLUXDB_TOKEN', 'paste-your-token-here', 'User')
```

**Verify it's set:**
```powershell
echo $env:INFLUXDB_TOKEN
```

### Step 5: Configure Grafana Data Source

1. Go to http://localhost:3000
2. Login: `admin` / `admin` (change password if prompted)
3. Click gear icon (⚙️) → Data Sources → Add data source
4. Select "InfluxDB"
5. Configure:
   - **Query Language**: `Flux` (NOT InfluxQL)
   - **URL**: `http://localhost:8086`
   - **Organization**: `trading`
   - **Token**: Paste your token from Step 3
   - **Default Bucket**: `metrics`
6. Click "Save & Test" → Should show green checkmark

### Step 6: Import Dashboard

1. In Grafana, click "+" (plus icon) → Import
2. Click "Upload JSON file"
3. Select `grafana_dashboard.json` from your project folder
4. Select "InfluxDB" as data source
5. Click "Import"

### Step 7: Start Trading Bot

```bash
python main.py
```

**That's it!** The dashboard should now show real-time data!

---

## 🎯 Quick Test

### Test Control API
```bash
# Windows PowerShell
Invoke-RestMethod -Uri http://localhost:5000/health

# Should return: {"status":"ok","message":"Control API is running"}
```

### Test Configuration
```bash
# Get current config
Invoke-RestMethod -Uri http://localhost:5000/config

# Update risk multiplier
Invoke-RestMethod -Method POST -Uri http://localhost:5000/config `
  -ContentType "application/json" `
  -Body '{"risk_multiplier": 0.8}'

# Emergency stop
Invoke-RestMethod -Method POST -Uri http://localhost:5000/emergency_stop
```

### Test Dashboard
1. Open http://localhost:3000
2. You should see:
   - Account Value panel (top left)
   - Fair Price panel
   - Position Size
   - Charts updating every 5 seconds
   - Signal gauges showing values

---

## 🐛 Troubleshooting

### "No data in dashboard"
- **Check bot is running**: `python main.py`
- **Check INFLUXDB_TOKEN is set**: `echo $env:INFLUXDB_TOKEN`
- **Check InfluxDB has data**:
  1. Go to http://localhost:8086
  2. Click Data Explorer
  3. Select bucket: `metrics`
  4. Should see measurements: trading_metrics, signals, order_events

### "Can't connect to InfluxDB"
- **Check InfluxDB is running**: Go to http://localhost:8086
- **Check token is correct**: Re-copy from InfluxDB UI
- **Check organization name**: Must be exactly `trading` (case sensitive)
- **Check query language**: Must be `Flux` not InfluxQL

### "Control API not responding"
- **Check if running**: `netstat -an | findstr 5000`
- **Restart API**: Kill python process and run `python control_api.py`
- **Check logs**: Look at Control API window for errors

### "Bot says InfluxDB disabled"
- **INFLUXDB_TOKEN not set**: Set environment variable (Step 4)
- **Restart bot**: After setting token, restart `python main.py`
- **Check bot logs**: Should see "Connected to InfluxDB"

---

## 📱 Dashboard Features

### Panels Available:
1. **Account Value** - Current account balance
2. **Fair Price** - Calculated fair market price
3. **Position Size** - Current position with color coding
4. **Unrealized PnL** - Current profit/loss
5. **Fair Price History** - 1 hour time series
6. **Account Value History** - 4 hour time series
7. **PnL History** - 4 hour time series
8. **Flow Confidence** - Market microstructure signal
9. **Net Buying** - Buy vs sell pressure
10. **Volume Imbalance** - Order book imbalance
11. **Momentum** - Price momentum signal
12. **Stop Loss Distance** - % to stop loss
13. **Profit Target Distance** - % to profit target
14. **Open Orders** - Current order count
15. **Order Events Table** - Last 50 orders

### Control Features:
- 🛑 **Emergency Stop**: Instantly disable trading
- ✅ **Resume Trading**: Re-enable trading
- 📊 **Live Config**: View/update parameters in real-time

---

## ⚙️ Configuration Files

### `live_config.json`
Controls bot behavior in real-time (auto-reloads every 5 seconds):

```json
{
  "enable_trading": true,        // Master on/off switch
  "risk_multiplier": 1.0,        // Size multiplier (0.5 = half size)
  "max_orders_per_side": 3,      // Max orders per side
  "max_position_pct": 50.0,      // Max position as % of account
  "base_spread": 0.001,          // Base spread (0.1%)
  "order_size_pct": 5.0,         // Order size as % of account
  "stop_loss_pct": 2.0,          // Stop loss % from entry
  "profit_target_pct": 3.0       // Profit target % from entry
}
```

**Edit this file anytime** - bot will pick up changes within 5 seconds!

---

## 🎓 Advanced Features

### Custom Time Ranges
Click the time picker in Grafana (top right) to change:
- Last 5 minutes
- Last 1 hour (default)
- Last 6 hours
- Last 24 hours
- Custom range

### Panel Customization
Click any panel title → Edit to:
- Adjust queries
- Change visualization type
- Modify thresholds and colors
- Add alerts

### Dashboard Variables
Create variables for:
- Symbol selection
- Time aggregation
- Account filtering

---

## 📞 Support

**Issues?**
1. Run `python verify_dashboard_setup.py` to check setup
2. Review logs from InfluxDB, Grafana, Control API, and trading bot
3. See full setup guide: `GRAFANA_SETUP.md`
4. Check main README: `README.md`

**File Locations:**
- InfluxDB: `C:\influxdb`
- Grafana: `C:\grafana`
- Bot files: Current directory
- Logs: Check console windows

---

## 🎉 You're All Set!

Your professional trading dashboard is now running with:
- ✅ Real-time metrics visualization
- ✅ Historical performance tracking
- ✅ Live parameter control
- ✅ Emergency stop capability
- ✅ Complete order history

**Happy Trading! 🚀📈**
