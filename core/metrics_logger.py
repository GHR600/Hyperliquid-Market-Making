import logging
from datetime import datetime
from typing import Dict, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxMetricsLogger:
    """Logs trading metrics to InfluxDB for Grafana visualization"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # InfluxDB configuration
        self.url = "http://localhost:8086"
        self.token = None  # Will be loaded from config or environment
        self.org = "trading"
        self.bucket = "metrics"

        self.client = None
        self.write_api = None
        self.enabled = False

        self._initialize_influxdb()

    def _initialize_influxdb(self):
        """Initialize connection to InfluxDB"""
        try:
            # Try to get token from environment variable or config
            import os
            self.token = os.environ.get('INFLUXDB_TOKEN')

            if not self.token:
                print("⚠️ No INFLUXDB_TOKEN found in environment variables")
                print("   Set INFLUXDB_TOKEN environment variable or dashboard will be disabled")
                return

            # Initialize InfluxDB client
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )

            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

            # Test connection
            health = self.client.health()
            if health.status == "pass":
                self.enabled = True
                print(f"✅ Connected to InfluxDB at {self.url}")
                self.logger.info("InfluxDB metrics logging enabled")
            else:
                print(f"⚠️ InfluxDB health check failed: {health.message}")

        except Exception as e:
            print(f"⚠️ Failed to initialize InfluxDB: {e}")
            print("   Dashboard metrics will be disabled")
            self.logger.warning(f"InfluxDB initialization failed: {e}")

    def log_trading_metrics(self, metrics: Dict):
        """Log general trading metrics"""
        if not self.enabled:
            return

        try:
            point = Point("trading_metrics") \
                .tag("symbol", self.config.SYMBOL) \
                .field("fair_price", float(metrics.get('fair_price', 0))) \
                .field("account_value", float(metrics.get('account_value', 0))) \
                .field("position_size", float(metrics.get('position_size', 0))) \
                .field("unrealized_pnl", float(metrics.get('unrealized_pnl', 0))) \
                .field("spread_pct", float(metrics.get('spread_pct', 0))) \
                .field("open_orders", int(metrics.get('open_orders', 0))) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            self.logger.error(f"Failed to log trading metrics: {e}")

    def log_signals(self, signals):
        """Log microstructure signals"""
        if not self.enabled or not signals:
            return

        try:
            point = Point("signals") \
                .tag("symbol", self.config.SYMBOL) \
                .field("flow_confidence", float(signals.flow_confidence)) \
                .field("net_buying", float(signals.net_buying)) \
                .field("volume_imbalance", float(signals.volume_imbalance)) \
                .field("momentum", float(signals.momentum)) \
                .field("adverse_risk", float(signals.adverse_risk)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            self.logger.error(f"Failed to log signals: {e}")

    def log_order_event(self, event_type: str, side: str, price: float, size: float, order_id: str = ""):
        """Log order placement, cancellation, or fill events"""
        if not self.enabled:
            return

        try:
            point = Point("order_events") \
                .tag("symbol", self.config.SYMBOL) \
                .tag("event_type", event_type) \
                .tag("side", side) \
                .field("price", float(price)) \
                .field("size", float(size)) \
                .field("order_id", str(order_id)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            self.logger.error(f"Failed to log order event: {e}")

    def log_risk_metrics(self, risk_status: Dict):
        """Log risk management metrics"""
        if not self.enabled:
            return

        try:
            point = Point("risk_metrics") \
                .tag("symbol", self.config.SYMBOL) \
                .field("stop_loss_price", float(risk_status.get('stop_loss_price', 0))) \
                .field("profit_target_price", float(risk_status.get('profit_target_price', 0))) \
                .field("stop_loss_distance_pct", float(risk_status.get('stop_loss_distance_pct', 0))) \
                .field("profit_target_distance_pct", float(risk_status.get('profit_target_distance_pct', 0))) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            self.logger.error(f"Failed to log risk metrics: {e}")

    def cleanup(self):
        """Close InfluxDB connection"""
        if self.client:
            try:
                self.client.close()
                print("✅ InfluxDB connection closed")
            except Exception as e:
                self.logger.error(f"Error closing InfluxDB connection: {e}")
