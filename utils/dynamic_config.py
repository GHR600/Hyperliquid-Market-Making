import json
import os
import time
import logging
from typing import Any, Dict

class DynamicConfig:
    """Dynamic configuration system that reloads from live_config.json"""

    def __init__(self, config_file: str = "live_config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.config_data: Dict[str, Any] = {}
        self.last_load_time = 0
        self.refresh_interval = 5  # seconds

        # Default configuration values
        self.defaults = {
            'enable_trading': True,
            'risk_multiplier': 1.0,
            'max_orders_per_side': 3,
            'max_position_pct': 50.0,
            'base_spread': 0.001,
            'order_size_pct': 5.0,
            'stop_loss_pct': 2.0,
            'profit_target_pct': 3.0
        }

        # Initialize config file if it doesn't exist
        self._initialize_config_file()

        # Load initial configuration
        self._load_config()

        print(f"✅ Dynamic configuration initialized from {self.config_file}")

    def _initialize_config_file(self):
        """Create config file with defaults if it doesn't exist"""
        if not os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.defaults, f, indent=2)
                print(f"📝 Created {self.config_file} with default values")
            except Exception as e:
                print(f"⚠️ Failed to create config file: {e}")
                self.logger.warning(f"Failed to create config file: {e}")

    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config_data = json.load(f)
                self.last_load_time = time.time()
            else:
                self.config_data = self.defaults.copy()
                self.last_load_time = time.time()
        except Exception as e:
            print(f"⚠️ Error loading config file: {e}")
            self.logger.error(f"Error loading config file: {e}")
            self.config_data = self.defaults.copy()

    def refresh_if_needed(self):
        """Reload configuration if refresh interval has passed"""
        current_time = time.time()
        if current_time - self.last_load_time >= self.refresh_interval:
            old_config = self.config_data.copy()
            self._load_config()

            # Log any changes
            for key, value in self.config_data.items():
                if key in old_config and old_config[key] != value:
                    print(f"🔄 Config updated: {key} = {value} (was {old_config[key]})")
                    self.logger.info(f"Config updated: {key} = {value}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value, refreshing if needed"""
        self.refresh_if_needed()
        return self.config_data.get(key, default if default is not None else self.defaults.get(key))

    def set(self, key: str, value: Any):
        """Set configuration value and save to file"""
        try:
            self.config_data[key] = value

            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)

            self.last_load_time = time.time()
            print(f"✅ Config saved: {key} = {value}")
            self.logger.info(f"Config saved: {key} = {value}")

        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            self.logger.error(f"Failed to save config: {e}")

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        self.refresh_if_needed()
        return self.config_data.copy()

    def update_multiple(self, updates: Dict[str, Any]):
        """Update multiple configuration values at once"""
        try:
            self.config_data.update(updates)

            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)

            self.last_load_time = time.time()
            print(f"✅ Config updated with {len(updates)} changes")
            self.logger.info(f"Config updated: {list(updates.keys())}")

        except Exception as e:
            print(f"❌ Failed to update config: {e}")
            self.logger.error(f"Failed to update config: {e}")
