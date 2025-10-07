"""
Verification script for dashboard setup
Checks if all components are ready
"""
import os
import sys
import json

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def check_file(filepath):
    """Check if a file exists"""
    return os.path.exists(filepath)

def check_env_var(var_name):
    """Check if environment variable is set"""
    return var_name in os.environ

def main():
    print("=" * 60)
    print("Dashboard Setup Verification")
    print("=" * 60)
    print()

    all_good = True

    # Check Python packages
    print("📦 Checking Python Packages...")
    packages = {
        'influxdb_client': 'influxdb-client',
        'flask': 'flask',
        'flask_cors': 'flask-cors'
    }

    for module, name in packages.items():
        if check_package(module):
            print(f"   ✅ {name} installed")
        else:
            print(f"   ❌ {name} NOT installed")
            all_good = False

    print()

    # Check required files
    print("📁 Checking Required Files...")
    files = [
        'control_api.py',
        'grafana_dashboard.json',
        'GRAFANA_SETUP.md',
        'live_config.json',
        'core/metrics_logger.py',
        'utils/dynamic_config.py',
        'start_dashboard.bat'
    ]

    for filepath in files:
        if check_file(filepath):
            print(f"   ✅ {filepath}")
        else:
            print(f"   ❌ {filepath} NOT found")
            all_good = False

    print()

    # Check configuration
    print("⚙️  Checking Configuration...")
    if check_file('live_config.json'):
        try:
            with open('live_config.json', 'r') as f:
                config = json.load(f)
            print(f"   ✅ live_config.json valid JSON")
            print(f"      enable_trading: {config.get('enable_trading')}")
            print(f"      risk_multiplier: {config.get('risk_multiplier')}")
        except json.JSONDecodeError:
            print(f"   ❌ live_config.json is invalid JSON")
            all_good = False

    print()

    # Check environment variable
    print("🔐 Checking Environment Variables...")
    if check_env_var('INFLUXDB_TOKEN'):
        print(f"   ✅ INFLUXDB_TOKEN is set")
    else:
        print(f"   ⚠️  INFLUXDB_TOKEN NOT set (optional if not using InfluxDB yet)")
        print(f"      Set with: $env:INFLUXDB_TOKEN=\"your-token-here\"")

    print()

    # Check external dependencies (informational)
    print("🔧 External Dependencies (Manual Installation Required)...")
    print("   ℹ️  InfluxDB - Check if running at http://localhost:8086")
    print("   ℹ️  Grafana - Check if running at http://localhost:3000")

    print()
    print("=" * 60)

    if all_good:
        print("✅ All Python components are ready!")
        print()
        print("Next steps:")
        print("1. Install InfluxDB (if not installed)")
        print("   Download: https://portal.influxdata.com/downloads/")
        print("   Extract to C:\\influxdb")
        print()
        print("2. Install Grafana (if not installed)")
        print("   Download: https://grafana.com/grafana/download")
        print("   Extract to C:\\grafana")
        print()
        print("3. Run start_dashboard.bat to start all services")
        print()
        print("4. Follow GRAFANA_SETUP.md for complete configuration")
        print()
        print("5. Start trading bot: python main.py")
    else:
        print("❌ Some components are missing. Please install them.")
        return 1

    print("=" * 60)
    return 0

if __name__ == '__main__':
    sys.exit(main())
