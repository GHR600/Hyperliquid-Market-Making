@echo off
REM Startup script for Grafana Dashboard on Windows
REM This script starts InfluxDB, Grafana, and the Control API

echo ============================================================
echo  Hyperliquid Market Maker - Dashboard Startup
echo ============================================================
echo.

REM Check if InfluxDB exists
if not exist "C:\influxdb\influxd.exe" (
    echo [ERROR] InfluxDB not found at C:\influxdb\influxd.exe
    echo Please install InfluxDB and extract to C:\influxdb
    echo Download: https://portal.influxdata.com/downloads/
    pause
    exit /b 1
)

REM Check if Grafana exists
if not exist "C:\grafana\grafana\bin\grafana-server.exe" (
    echo [ERROR] Grafana not found at C:\grafana\bin\grafana-server.exe
    echo Please install Grafana and extract to C:\grafana
    echo Download: https://grafana.com/grafana/download
    pause
    exit /b 1
)

REM Check if control_api.py exists
if not exist "control_api.py" (
    echo [ERROR] control_api.py not found in current directory
    echo Please run this script from the Hyperliquid-Market-Making directory
    pause
    exit /b 1
)

echo [1/4] Starting InfluxDB...
start "InfluxDB" /MIN cmd /c "cd /d C:\influxdb && influxd.exe"
timeout /t 3 /nobreak >nul
echo      InfluxDB started on http://localhost:8086

echo.
echo [2/4] Starting Grafana...
start "Grafana" /MIN cmd /c "cd /d C:\grafana\bin && grafana-server.exe"
timeout /t 3 /nobreak >nul
echo      Grafana started on http://localhost:3000

echo.
echo [3/4] Starting Control API...
start "Control API" cmd /c "python control_api.py"
timeout /t 2 /nobreak >nul
echo      Control API started on http://localhost:5000

echo.
echo [4/4] Opening Grafana Dashboard in browser...
timeout /t 5 /nobreak >nul
start http://localhost:3000

echo.
echo ============================================================
echo  Dashboard Services Started Successfully!
echo ============================================================
echo.
echo   InfluxDB:    http://localhost:8086
echo   Grafana:     http://localhost:3000  (admin/admin)
echo   Control API: http://localhost:5000
echo.
echo To stop services: Close the opened windows
echo.
echo IMPORTANT: Make sure to set INFLUXDB_TOKEN environment variable
echo            Run in PowerShell:
echo            $env:INFLUXDB_TOKEN="your-token-here"
echo.
echo Next steps:
echo   1. Configure InfluxDB at http://localhost:8086
echo   2. Setup Grafana data source (see GRAFANA_SETUP.md)
echo   3. Import dashboard from grafana_dashboard.json
echo   4. Start trading bot: python main.py
echo.
echo ============================================================
pause
