#!/bin/bash
# Startup script for Grafana Dashboard on Mac/Linux
# This script starts InfluxDB, Grafana, and the Control API

echo "============================================================"
echo " Hyperliquid Market Maker - Dashboard Startup"
echo "============================================================"
echo ""

# Check if InfluxDB is installed
if ! command -v influxd &> /dev/null; then
    echo "[ERROR] InfluxDB not found"
    echo "Please install InfluxDB:"
    echo "  Mac: brew install influxdb"
    echo "  Linux: See https://portal.influxdata.com/downloads/"
    exit 1
fi

# Check if Grafana is installed
if ! command -v grafana-server &> /dev/null; then
    echo "[ERROR] Grafana not found"
    echo "Please install Grafana:"
    echo "  Mac: brew install grafana"
    echo "  Linux: See https://grafana.com/grafana/download"
    exit 1
fi

# Check if control_api.py exists
if [ ! -f "control_api.py" ]; then
    echo "[ERROR] control_api.py not found in current directory"
    echo "Please run this script from the Hyperliquid-Market-Making directory"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found"
    echo "Please install Python 3"
    exit 1
fi

echo "[1/4] Starting InfluxDB..."
# Check if InfluxDB is already running
if pgrep -x "influxd" > /dev/null; then
    echo "     InfluxDB is already running"
else
    if command -v brew &> /dev/null; then
        # Mac with Homebrew
        brew services start influxdb
    else
        # Linux - start in background
        nohup influxd > /tmp/influxdb.log 2>&1 &
    fi
    sleep 3
    echo "     InfluxDB started on http://localhost:8086"
fi

echo ""
echo "[2/4] Starting Grafana..."
# Check if Grafana is already running
if pgrep -x "grafana-server" > /dev/null; then
    echo "     Grafana is already running"
else
    if command -v brew &> /dev/null; then
        # Mac with Homebrew
        brew services start grafana
    else
        # Linux - start in background
        nohup grafana-server > /tmp/grafana.log 2>&1 &
    fi
    sleep 3
    echo "     Grafana started on http://localhost:3000"
fi

echo ""
echo "[3/4] Starting Control API..."
# Check if Control API is already running
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "     Control API is already running on port 5000"
else
    nohup python3 control_api.py > /tmp/control_api.log 2>&1 &
    sleep 2
    echo "     Control API started on http://localhost:5000"
fi

echo ""
echo "[4/4] Opening Grafana Dashboard in browser..."
sleep 3

# Open browser (cross-platform)
if command -v open &> /dev/null; then
    # Mac
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:3000
else
    echo "     Please open http://localhost:3000 in your browser"
fi

echo ""
echo "============================================================"
echo " Dashboard Services Started Successfully!"
echo "============================================================"
echo ""
echo "  InfluxDB:    http://localhost:8086"
echo "  Grafana:     http://localhost:3000  (admin/admin)"
echo "  Control API: http://localhost:5000"
echo ""
echo "To stop services:"
echo "  Mac:   brew services stop influxdb && brew services stop grafana"
echo "  Linux: killall influxd grafana-server python3"
echo ""
echo "IMPORTANT: Make sure to set INFLUXDB_TOKEN environment variable"
echo "           Run: export INFLUXDB_TOKEN=\"your-token-here\""
echo "           Add to ~/.bashrc or ~/.zshrc to make permanent"
echo ""
echo "Next steps:"
echo "  1. Configure InfluxDB at http://localhost:8086"
echo "  2. Setup Grafana data source (see GRAFANA_SETUP.md)"
echo "  3. Import dashboard from grafana_dashboard.json"
echo "  4. Start trading bot: python3 main.py"
echo ""
echo "============================================================"
