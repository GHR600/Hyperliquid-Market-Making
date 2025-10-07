# Grafana Dashboard Setup Guide

Complete step-by-step instructions for setting up the Hyperliquid Market Maker monitoring dashboard.

---

## Prerequisites

Before starting, ensure you have installed:
- InfluxDB 2.7+
- Grafana 8.0+
- Python packages: `influxdb-client`, `flask`, `flask-cors`

---

## Step 1: Install and Start InfluxDB

### Windows
1. Download InfluxDB from https://portal.influxdata.com/downloads/
2. Extract to `C:\influxdb`
3. Open Command Prompt and navigate to `C:\influxdb`
4. Run: `influxd.exe`
5. Open browser to http://localhost:8086

### Mac/Linux
```bash
brew install influxdb
brew services start influxdb
```
Then open browser to http://localhost:8086

### Initial Setup
1. Click "Get Started"
2. Set up initial user:
   - Username: `admin`
   - Password: `admin123` (or your preferred password)
   - Organization: `trading`
   - Bucket: `metrics`
3. Click "Continue"
4. **IMPORTANT**: Copy and save the API token generated
5. Click "Configure Later"

### Set Environment Variable
Set the token as an environment variable so the bot can access InfluxDB:

**Windows (PowerShell)**:
```powershell
$env:INFLUXDB_TOKEN="your-token-here"
# To make it permanent:
[System.Environment]::SetEnvironmentVariable('INFLUXDB_TOKEN', 'your-token-here', 'User')
```

**Mac/Linux (bash)**:
```bash
export INFLUXDB_TOKEN="your-token-here"
# Add to ~/.bashrc or ~/.zshrc to make permanent:
echo 'export INFLUXDB_TOKEN="your-token-here"' >> ~/.bashrc
```

---

## Step 2: Install and Start Grafana

### Windows
1. Download Grafana from https://grafana.com/grafana/download
2. Extract to `C:\grafana`
3. Navigate to `C:\grafana\bin`
4. Run: `grafana-server.exe`
5. Open browser to http://localhost:3000

### Mac/Linux
```bash
brew install grafana
brew services start grafana
```
Then open browser to http://localhost:3000

### Initial Login
- Username: `admin`
- Password: `admin`
- You'll be prompted to change the password (optional)

---

## Step 3: Add InfluxDB Data Source in Grafana

1. In Grafana, click the gear icon (⚙️) on the left sidebar
2. Click "Data Sources"
3. Click "Add data source"
4. Select "InfluxDB"
5. Configure the data source:
   - **Name**: `InfluxDB` (exactly this name)
   - **Query Language**: Select `Flux` (NOT InfluxQL)
   - **URL**: `http://localhost:8086`
   - **Auth**: Leave all toggles OFF
   - Scroll down to "InfluxDB Details" section:
     - **Organization**: `trading`
     - **Token**: Paste your API token from Step 1
     - **Default Bucket**: `metrics`
6. Click "Save & Test"
7. You should see a green checkmark: "datasource is working"

---

## Step 4: Import Dashboard

1. In Grafana, hover over the "+" icon on the left sidebar
2. Click "Import"
3. Click "Upload JSON file"
4. Navigate to your project directory and select `grafana_dashboard.json`
5. On the import page:
   - **Name**: You can keep "Hyperliquid Market Maker Dashboard" or rename it
   - **Folder**: Select "General" or create a new folder
   - **InfluxDB**: Select the "InfluxDB" data source you created in Step 3
6. Click "Import"
7. You should now see the dashboard with all panels

---

## Step 5: Install Required Grafana Plugins (for Control Buttons)

### Install Button Panel Plugin
1. In Grafana, click the gear icon (⚙️) on the left sidebar
2. Click "Plugins"
3. Search for "Button Panel"
4. Click on it and click "Install"

### Install Infinity Data Source Plugin
1. Still in Plugins section
2. Search for "Infinity"
3. Click on it and click "Install"

---

## Step 6: Add Control Panels to Dashboard

After importing the dashboard, you can manually add control buttons for emergency stop and trading resume:

### Add Emergency Stop Button

1. Click "Add panel" (📊+) at the top of the dashboard
2. Select "Add a new panel"
3. In the panel type dropdown (top right), select "Button Panel"
4. Configure the button:
   - **Button Text**: `🛑 EMERGENCY STOP`
   - **Method**: `POST`
   - **URL**: `http://localhost:5000/emergency_stop`
   - **Content-Type**: `application/json`
5. Under "Display Options":
   - **Variant**: `destructive` or `danger`
   - **Orientation**: `center`
6. Save the panel with title "Emergency Stop"

### Add Resume Trading Button

1. Click "Add panel" again
2. Select "Add a new panel"
3. Select "Button Panel" as panel type
4. Configure the button:
   - **Button Text**: `✅ RESUME TRADING`
   - **Method**: `POST`
   - **URL**: `http://localhost:5000/resume_trading`
   - **Content-Type**: `application/json`
5. Under "Display Options":
   - **Variant**: `primary`
   - **Orientation**: `center`
6. Save the panel with title "Resume Trading"

### Add Configuration Display Panel

1. Click "Add panel" again
2. Select "Add a new panel"
3. Select panel type "Infinity"
4. Configure:
   - **Type**: `JSON`
   - **URL**: `http://localhost:5000/config`
   - **Method**: `GET`
5. Under "Parsing Options":
   - **Format**: `Table`
6. Save the panel with title "Current Configuration"

---

## Step 7: Start the Control API

Before the dashboard can send commands, you need to start the control API:

**Windows (Command Prompt)**:
```cmd
cd C:\Hyperliquid-Market-Making
python control_api.py
```

**Mac/Linux**:
```bash
cd ~/Hyperliquid-Market-Making
python control_api.py
```

You should see:
```
🚀 Trading Bot Control API Starting...
✅ API running on http://0.0.0.0:5000
```

---

## Step 8: Start Your Trading Bot

Now start your trading bot as usual. Make sure the `INFLUXDB_TOKEN` environment variable is set:

**Windows (PowerShell)**:
```powershell
cd C:\Hyperliquid-Market-Making
python main.py
```

**Mac/Linux**:
```bash
cd ~/Hyperliquid-Market-Making
python main.py
```

The bot will now send metrics to InfluxDB, and you should see data appearing in your Grafana dashboard within a few seconds!

---

## Step 9: Verify Everything is Working

### Check InfluxDB is Receiving Data
1. Go to http://localhost:8086
2. Click "Data Explorer" (graph icon on left)
3. Select bucket: `metrics`
4. You should see measurements: `trading_metrics`, `signals`, `order_events`, `risk_metrics`
5. Click on any measurement and field to verify data is coming in

### Check Grafana Dashboard
1. Go to http://localhost:3000
2. Open the "Hyperliquid Market Maker Dashboard"
3. You should see:
   - Account Value updating
   - Fair Price updating
   - Position Size
   - Charts showing historical data
   - Signal gauges moving
   - Order events table populating

### Test Control API
1. Click the "Emergency Stop" button in Grafana
2. Check that trading stops in your bot logs
3. Click the "Resume Trading" button
4. Verify trading resumes

---

## Troubleshooting

### No Data Appearing in Grafana
- **Check InfluxDB token**: Ensure `INFLUXDB_TOKEN` environment variable is set correctly
- **Verify InfluxDB is running**: Go to http://localhost:8086
- **Check bot logs**: Look for "Connected to InfluxDB" message
- **Check Data Explorer**: Verify data is in InfluxDB (Step 9)

### Control Buttons Not Working
- **Check Control API is running**: Should see "API running on http://0.0.0.0:5000"
- **Check browser console**: Open browser dev tools (F12) and check for errors
- **Verify URL**: Make sure button URL is `http://localhost:5000/emergency_stop` (not https)
- **CORS issues**: The API has CORS enabled, but some browsers may block localhost requests

### Dashboard Shows "No Data"
- **Check time range**: Make sure dashboard time range includes recent data (default is "Last 1 hour")
- **Check queries**: Click on a panel, then "Edit" to see the query
- **Verify bucket name**: Should be `metrics` (case sensitive)
- **Check organization**: Should be `trading`

### Grafana Can't Connect to InfluxDB
- **Verify InfluxDB is running**: `http://localhost:8086` should be accessible
- **Check token**: Make sure you copied the full token from InfluxDB setup
- **Query language**: Must be `Flux`, not `InfluxQL`
- **URL format**: Should be `http://localhost:8086` (include `http://`)

---

## Quick Start Script

For convenience, use the provided startup scripts:

**Windows**: Double-click `start_dashboard.bat`

**Mac/Linux**:
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

These scripts will:
1. Start InfluxDB
2. Start Grafana
3. Start Control API
4. Open browser to dashboard

---

## Configuration Options

You can adjust refresh rates and time windows in the dashboard:

1. Click the gear icon (⚙️) at the top of the dashboard
2. Go to "Settings"
3. Under "General":
   - **Auto-refresh**: Default is 5 seconds, you can change this
   - **Time range**: Default is "Last 1 hour"
4. Click "Save dashboard"

For individual panels:
1. Click the panel title → "Edit"
2. Adjust queries, time ranges, or refresh rates
3. Save changes

---

## Security Notes

- This setup is designed for **LOCAL USE ONLY**
- InfluxDB and Grafana are accessible on localhost
- Control API accepts connections from any IP (0.0.0.0)
- For production use, add authentication and restrict access
- Never expose these services to the public internet without proper security

---

## Additional Resources

- InfluxDB Flux Documentation: https://docs.influxdata.com/flux/
- Grafana Documentation: https://grafana.com/docs/
- Flask Documentation: https://flask.palletsprojects.com/

---

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review logs from InfluxDB, Grafana, Control API, and the trading bot
3. Ensure all prerequisites are installed and running
4. Verify environment variables are set correctly
