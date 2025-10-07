"""
Flask API for controlling the trading bot via Grafana dashboard
"""
import sys
import os

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for Grafana requests

# Configuration
CONFIG_FILE = "live_config.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load current configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            default_config = {
                'enable_trading': True,
                'risk_multiplier': 1.0,
                'max_orders_per_side': 3,
                'max_position_pct': 50.0,
                'base_spread': 0.001,
                'order_size_pct': 5.0,
                'stop_loss_pct': 2.0,
                'profit_target_pct': 3.0
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def save_config(config_data):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        logger.info(f"Configuration saved: {list(config_data.keys())}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Control API is running"})


@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration parameters"""
    try:
        # Get JSON data from request
        updates = request.get_json()

        if not updates:
            return jsonify({"error": "No data provided"}), 400

        # Load current config
        config = load_config()

        # Update with new values
        config.update(updates)

        # Save updated config
        if save_config(config):
            logger.info(f"Configuration updated: {updates}")
            return jsonify({
                "success": True,
                "message": "Configuration updated",
                "config": config
            })
        else:
            return jsonify({"error": "Failed to save configuration"}), 500

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    """Emergency stop - disable trading immediately"""
    try:
        config = load_config()
        config['enable_trading'] = False

        if save_config(config):
            logger.warning("EMERGENCY STOP ACTIVATED")
            return jsonify({
                "success": True,
                "message": "Trading STOPPED",
                "config": config
            })
        else:
            return jsonify({"error": "Failed to stop trading"}), 500

    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/resume_trading', methods=['POST'])
def resume_trading():
    """Resume trading"""
    try:
        config = load_config()
        config['enable_trading'] = True

        if save_config(config):
            logger.info("Trading resumed")
            return jsonify({
                "success": True,
                "message": "Trading RESUMED",
                "config": config
            })
        else:
            return jsonify({"error": "Failed to resume trading"}), 500

    except Exception as e:
        logger.error(f"Error resuming trading: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/config/<key>', methods=['GET'])
def get_config_value(key):
    """Get a specific configuration value"""
    try:
        config = load_config()
        if key in config:
            return jsonify({key: config[key]})
        else:
            return jsonify({"error": f"Key '{key}' not found"}), 404
    except Exception as e:
        logger.error(f"Error getting config value: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/config/<key>', methods=['PUT'])
def set_config_value(key):
    """Set a specific configuration value"""
    try:
        data = request.get_json()

        if 'value' not in data:
            return jsonify({"error": "No 'value' provided"}), 400

        config = load_config()
        config[key] = data['value']

        if save_config(config):
            logger.info(f"Configuration updated: {key} = {data['value']}")
            return jsonify({
                "success": True,
                "message": f"Updated {key}",
                "config": config
            })
        else:
            return jsonify({"error": "Failed to save configuration"}), 500

    except Exception as e:
        logger.error(f"Error setting config value: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Trading Bot Control API Starting...")
    print("=" * 60)
    print(f"📝 Config file: {CONFIG_FILE}")
    print(f"🌐 Endpoints:")
    print(f"   GET  /health               - Health check")
    print(f"   GET  /config               - Get all configuration")
    print(f"   POST /config               - Update configuration")
    print(f"   GET  /config/<key>         - Get specific value")
    print(f"   PUT  /config/<key>         - Set specific value")
    print(f"   POST /emergency_stop       - Stop trading immediately")
    print(f"   POST /resume_trading       - Resume trading")
    print("=" * 60)
    print(f"✅ API running on http://0.0.0.0:5000")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False)
