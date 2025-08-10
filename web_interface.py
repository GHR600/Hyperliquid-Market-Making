# web_interface.py
import asyncio
import json
import logging
from typing import Dict, List, Optional
import websockets
from datetime import datetime
import threading
from pathlib import Path

class WebInterface:
    def __init__(self, config, bot_instance):
        self.config = config
        self.bot = bot_instance
        self.logger = logging.getLogger(__name__)
        
        # WebSocket server settings
        self.host = "localhost"
        self.port = 8765
        self.clients = set()
        
        # Data cache for web interface
        self.latest_data = {
            'bot_status': 'INITIALIZING',
            'account_value': 0.0,
            'position': {'symbol': config.SYMBOL, 'size': 0.0, 'entry_price': 0.0},
            'unrealized_pnl': 0.0,
            'current_price': 0.0,
            'orderbook': {'bids': [], 'asks': []},
            'open_orders': [],
            'microstructure': {},
            'analysis': {'current_assessment': '', 'risk_factors': '', 'strategy_recommendation': ''},
            'loop_count': 0,
            'last_update': datetime.now().isoformat()
        }
        
        print("🌐 Web Interface initialized")
        print(f"   Dashboard will be available at: http://localhost:8000")
        print(f"   WebSocket server will run on: ws://localhost:{self.port}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        print(f"🚀 Starting WebSocket server on {self.host}:{self.port}")
        
        async def handler(websocket, path):
            print(f"📱 New client connected from {websocket.remote_address}")
            self.clients.add(websocket)
            
            try:
                # Send initial data
                await websocket.send(json.dumps({
                    'type': 'initial_data',
                    'data': self.latest_data
                }))
                
                # Keep connection alive
                async for message in websocket:
                    # Handle client messages if needed
                    try:
                        data = json.loads(message)
                        await self.handle_client_message(websocket, data)
                    except json.JSONDecodeError:
                        pass
                        
            except websockets.exceptions.ConnectionClosed:
                print(f"📱 Client {websocket.remote_address} disconnected")
            finally:
                self.clients.discard(websocket)
        
        start_server = websockets.serve(handler, self.host, self.port)
        await start_server
        print(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
    
    async def handle_client_message(self, websocket, data):
        """Handle messages from web clients"""
        message_type = data.get('type')
        
        if message_type == 'get_status':
            await websocket.send(json.dumps({
                'type': 'status_update',
                'data': self.latest_data
            }))
        elif message_type == 'emergency_stop':
            print("🛑 Emergency stop requested from web interface")
            self.bot.running = False
    
    async def broadcast_update(self, update_type: str, data: Dict):
        """Broadcast updates to all connected clients"""
        if not self.clients:
            return
        
        message = json.dumps({
            'type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Send to all connected clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients
    
    def update_bot_status(self, status: str):
        """Update bot status"""
        self.latest_data['bot_status'] = status
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('bot_status', {
            'status': status,
            'timestamp': self.latest_data['last_update']
        }))
    
    def update_account_data(self, account_value: float, position_data: Dict, unrealized_pnl: float):
        """Update account and position data"""
        self.latest_data['account_value'] = account_value
        self.latest_data['position'] = position_data
        self.latest_data['unrealized_pnl'] = unrealized_pnl
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('account_update', {
            'account_value': account_value,
            'position': position_data,
            'unrealized_pnl': unrealized_pnl
        }))
    
    def update_market_data(self, current_price: float, orderbook: Dict):
        """Update market data"""
        self.latest_data['current_price'] = current_price
        self.latest_data['orderbook'] = orderbook
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('market_update', {
            'current_price': current_price,
            'orderbook': orderbook
        }))
    
    def update_orders(self, orders: List[Dict]):
        """Update open orders"""
        self.latest_data['open_orders'] = orders
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('orders_update', {
            'orders': orders
        }))
    
    def update_microstructure(self, signals: Dict):
        """Update microstructure analysis"""
        self.latest_data['microstructure'] = signals
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('microstructure_update', {
            'signals': signals
        }))
    
    def update_analysis(self, analysis_text: Dict):
        """Update AI analysis text"""
        self.latest_data['analysis'] = analysis_text
        self.latest_data['last_update'] = datetime.now().isoformat()
        
        # Broadcast to clients
        asyncio.create_task(self.broadcast_update('analysis_update', {
            'analysis': analysis_text
        }))
    
    def update_loop_count(self, count: int):
        """Update trading loop count"""
        self.latest_data['loop_count'] = count
    
    def generate_analysis_text(self, signals, position, orderbook, orders) -> Dict:
        """Generate human-readable analysis text"""
        try:
            # Current Market Assessment
            flow_confidence = signals.flow_confidence
            volume_imbalance = signals.volume_imbalance
            net_aggressive_buying = signals.net_aggressive_buying
            overall_momentum = signals.overall_momentum
            
            if flow_confidence > 0.7:
                confidence_desc = "high"
            elif flow_confidence > 0.4:
                confidence_desc = "moderate"
            else:
                confidence_desc = "low"
            
            if overall_momentum > 0.3:
                momentum_desc = "strong bullish"
                signal_type = "bullish"
            elif overall_momentum < -0.3:
                momentum_desc = "strong bearish"
                signal_type = "bearish"
            else:
                momentum_desc = "neutral/ranging"
                signal_type = "neutral"
            
            current_assessment = f"The market is displaying {momentum_desc} microstructure signals with {confidence_desc} flow confidence ({flow_confidence:.3f}). "
            
            if volume_imbalance > 0.2:
                current_assessment += f"There's significant buying pressure evidenced by positive volume imbalance (+{volume_imbalance:.3f}) "
            elif volume_imbalance < -0.2:
                current_assessment += f"There's significant selling pressure evidenced by negative volume imbalance ({volume_imbalance:.3f}) "
            else:
                current_assessment += f"Volume imbalance is relatively balanced ({volume_imbalance:.3f}) "
            
            if net_aggressive_buying > 0.1:
                current_assessment += f"and net aggressive buying (+{net_aggressive_buying:.3f})."
            elif net_aggressive_buying < -0.1:
                current_assessment += f"and net aggressive selling ({net_aggressive_buying:.3f})."
            else:
                current_assessment += f"with neutral aggressive flow ({net_aggressive_buying:.3f})."
            
            # Risk Factors
            adverse_risk = signals.adverse_selection_risk
            spread_volatility = signals.spread_volatility
            
            risk_factors = ""
            if adverse_risk > 0.6:
                risk_factors += f"High adverse selection risk ({adverse_risk:.3f}) suggests significant caution is warranted. "
            elif adverse_risk > 0.3:
                risk_factors += f"Moderate adverse selection risk ({adverse_risk:.3f}) suggests some caution is warranted. "
            else:
                risk_factors += f"Low adverse selection risk ({adverse_risk:.3f}) indicates favorable conditions. "
            
            if spread_volatility > 0.01:
                risk_factors += f"Elevated spread volatility ({spread_volatility:.4f}) indicates unstable market conditions."
            else:
                risk_factors += f"Low spread volatility ({spread_volatility:.4f}) indicates stable market conditions."
            
            # Strategy Recommendation
            strategy_recommendation = "The algorithm is "
            
            if len(orders) == 0:
                strategy_recommendation += "currently not placing orders due to unfavorable conditions. "
            else:
                if flow_confidence > 0.6:
                    strategy_recommendation += "maintaining active market making with tighter spreads due to high flow confidence. "
                else:
                    strategy_recommendation += "maintaining conservative market making with wider spreads due to uncertainty. "
            
            if signals.flow_confidence > 0.8 and abs(signals.overall_momentum) < 0.3:
                strategy_recommendation += "Position sizing has been increased by 20% to capitalize on favorable ranging conditions. "
            elif adverse_risk > 0.7:
                strategy_recommendation += "Position sizing has been reduced by 50% due to high adverse selection risk. "
            
            strategy_recommendation += "Next order refresh in 5-15 seconds depending on market conditions."
            
            return {
                'current_assessment': current_assessment,
                'risk_factors': risk_factors,
                'strategy_recommendation': strategy_recommendation,
                'signal_type': signal_type
            }
            
        except Exception as e:
            self.logger.error(f"Error generating analysis text: {e}")
            return {
                'current_assessment': "Analysis temporarily unavailable due to data processing.",
                'risk_factors': "Unable to assess current risk factors.",
                'strategy_recommendation': "Strategy operating in safe mode with default parameters.",
                'signal_type': 'neutral'
            }

# Static file server for the dashboard
import http.server
import socketserver
import os
from threading import Thread

class DashboardServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the HTTP server for the dashboard"""
        print(f"🌐 Starting dashboard server on port {self.port}")
        
        # Create the dashboard HTML file
        dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hyperliquid Market Maker Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        /* Copy the CSS from the artifact above */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a1f29 100%);
            color: #e8eaed;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .dashboard {
            display: grid;
            grid-template-columns: 280px 1fr;
            min-height: 100vh;
        }

        .sidebar {
            background: rgba(15, 20, 25, 0.95);
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            padding: 24px;
            position: relative;
        }

        .sidebar::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            width: 1px;
            background: linear-gradient(to bottom, transparent, #00d4ff, transparent);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
            font-size: 20px;
            font-weight: 700;
            color: #00d4ff;
        }

        .status-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            backdrop-filter: blur(10px);
        }

        .status-title {
            font-size: 14px;
            color: #8a9ba8;
            margin-bottom: 8px;
        }

        .status-value {
            font-size: 18px;
            font-weight: 600;
        }

        .status-positive { color: #00ff88; }
        .status-negative { color: #ff4757; }
        .status-neutral { color: #ffa726; }

        .main-content {
            padding: 24px;
            overflow-y: auto;
        }

        .header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .page-title {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .grid {
            display: grid;
            gap: 24px;
            margin-bottom: 24px;
        }

        .grid-2 { grid-template-columns: 1fr 1fr; }
        .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
        .grid-full { grid-template-columns: 1fr; }

        .card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #00d4ff, #0099cc);
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 16px;
        }

        .metric {
            text-align: center;
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .metric-label {
            font-size: 12px;
            color: #8a9ba8;
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 16px;
            font-weight: 600;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 16px;
        }

        .orderbook {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            height: 400px;
        }

        .orderbook-side {
            display: flex;
            flex-direction: column;
        }

        .orderbook-header {
            font-weight: 600;
            padding: 8px 12px;
            text-align: center;
            border-radius: 6px;
            margin-bottom: 8px;
        }

        .bids-header {
            background: rgba(0, 255, 136, 0.1);
            color: #00ff88;
        }

        .asks-header {
            background: rgba(255, 71, 87, 0.1);
            color: #ff4757;
        }

        .orderbook-level {
            display: grid;
            grid-template-columns: 1fr 1fr;
            padding: 4px 8px;
            font-size: 14px;
            font-family: 'JetBrains Mono', monospace;
            border-radius: 4px;
            margin-bottom: 2px;
            transition: all 0.2s ease;
        }

        .orderbook-level:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        .bid-level {
            background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.1));
        }

        .ask-level {
            background: linear-gradient(90deg, rgba(255, 71, 87, 0.1), transparent);
        }

        .orders-list {
            max-height: 300px;
            overflow-y: auto;
        }

        .order-item {
            display: grid;
            grid-template-columns: 60px 80px 100px 80px;
            gap: 12px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 14px;
            align-items: center;
        }

        .order-side-buy {
            color: #00ff88;
            font-weight: 600;
        }

        .order-side-sell {
            color: #ff4757;
            font-weight: 600;
        }

        .analysis-section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            margin-top: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .analysis-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #00d4ff;
        }

        .analysis-text {
            line-height: 1.6;
            color: #b8c5d1;
        }

        .signal-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .signal-bullish { background: #00ff88; }
        .signal-bearish { background: #ff4757; }
        .signal-neutral { background: #ffa726; }

        .live-indicator {
            position: relative;
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            margin-right: 8px;
        }

        .live-indicator::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: #00ff88;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            100% { transform: scale(2); opacity: 0; }
        }

        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #8a9ba8;
            margin-top: 16px;
        }

        .connection-status.connected {
            color: #00ff88;
        }

        .connection-status.disconnected {
            color: #ff4757;
        }

        @media (max-width: 1200px) {
            .dashboard {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                display: none;
            }
            
            .grid-2, .grid-3 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="sidebar">
            <div class="logo">
                <div class="live-indicator" id="connection-indicator"></div>
                Hyperliquid MM
            </div>
            
            <div class="status-card">
                <div class="status-title">Bot Status</div>
                <div class="status-value status-neutral" id="bot-status">CONNECTING...</div>
            </div>
            
            <div class="status-card">
                <div class="status-title">Account Value</div>
                <div class="status-value" id="account-value">$0.00</div>
            </div>
            
            <div class="status-card">
                <div class="status-title">Position</div>
                <div class="status-value status-neutral" id="position-size">No Position</div>
            </div>
            
            <div class="status-card">
                <div class="status-title">Unrealized PnL</div>
                <div class="status-value status-neutral" id="unrealized-pnl">$0.00</div>
            </div>
            
            <div class="connection-status" id="connection-status">
                <div class="live-indicator"></div>
                Connecting...
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1 class="page-title">Market Maker Dashboard</h1>
            </div>
            
            <div class="grid grid-3">
                <div class="card">
                    <div class="card-title">💰 Price Action</div>
                    <div class="price-display" id="current-price">$0.00</div>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Last Update</div>
                            <div class="metric-value" id="last-update">Never</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Loop Count</div>
                            <div class="metric-value" id="loop-count">0</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">📊 Open Orders</div>
                    <div class="orders-list" id="orders-list">
                        <div style="text-align: center; color: #8a9ba8; padding: 20px;">
                            No orders
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">🎯 Strategy Status</div>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Mode</div>
                            <div class="metric-value" id="strategy-mode">INACTIVE</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Symbol</div>
                            <div class="metric-value" id="trading-symbol">BTC</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="grid grid-2">
                <div class="card">
                    <div class="card-title">📖 Order Book</div>
                    <div class="orderbook">
                        <div class="orderbook-side">
                            <div class="orderbook-header bids-header">BIDS</div>
                            <div id="bids-container">
                                <div style="text-align: center; color: #8a9ba8; padding: 20px;">
                                    No data
                                </div>
                            </div>
                        </div>
                        
                        <div class="orderbook-side">
                            <div class="orderbook-header asks-header">ASKS</div>
                            <div id="asks-container">
                                <div style="text-align: center; color: #8a9ba8; padding: 20px;">
                                    No data
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">📈 Price Chart</div>
                    <div class="chart-container">
                        <canvas id="priceChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="grid grid-full">
                <div class="card">
                    <div class="card-title">🧠 Market Microstructure Analysis</div>
                    <div class="metric-grid" id="microstructure-metrics">
                        <div class="metric">
                            <div class="metric-label">Flow Confidence</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Volume Imbalance</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Net Aggressive Buying</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Overall Momentum</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Adverse Selection Risk</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Order Velocity</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Spread Volatility</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Trade Velocity</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Depth Pressure</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">VWAP Deviation</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Large Order Flow</div>
                            <div class="metric-value">0.000</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Accumulation Score</div>
                            <div class="metric-value">0.000</div>
                        </div>
                    </div>
                    
                    <div class="analysis-section">
                        <div class="analysis-title">🤖 AI Market Analysis</div>
                        <div class="analysis-text" id="analysis-text">
                            <p>Waiting for bot to initialize and begin analysis...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 10;
        
        // Chart setup
        const ctx = document.getElementById('priceChart').getContext('2d');
        const priceData = [];
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Price',
                    data: priceData,
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#8a9ba8'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#8a9ba8',
                            callback: function(value) {
                                return ' + value.toLocaleString();
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
        function connectWebSocket() {
            try {
                ws = new WebSocket('ws://localhost:8765');
                
                ws.onopen = function() {
                    console.log('Connected to bot WebSocket');
                    reconnectAttempts = 0;
                    updateConnectionStatus(true);
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    handleWebSocketMessage(message);
                };
                
                ws.onclose = function() {
                    console.log('WebSocket connection closed');
                    updateConnectionStatus(false);
                    
                    // Attempt to reconnect
                    if (reconnectAttempts < maxReconnectAttempts) {
                        reconnectAttempts++;
                        setTimeout(connectWebSocket, 5000);
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    updateConnectionStatus(false);
                };
                
            } catch (error) {
                console.error('Failed to connect to WebSocket:', error);
                updateConnectionStatus(false);
                
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 5000);
                }
            }
        }
        
        function updateConnectionStatus(connected) {
            const statusElement = document.getElementById('connection-status');
            const indicatorElement = document.getElementById('connection-indicator');
            
            if (connected) {
                statusElement.innerHTML = '<div class="live-indicator"></div>WebSocket Connected';
                statusElement.className = 'connection-status connected';
                indicatorElement.style.background = '#00ff88';
            } else {
                statusElement.innerHTML = '🔴 Disconnected (Retrying...)';
                statusElement.className = 'connection-status disconnected';
                indicatorElement.style.background = '#ff4757';
            }
        }
        
        function handleWebSocketMessage(message) {
            const { type, data } = message;
            
            switch (type) {
                case 'initial_data':
                    updateAllData(data);
                    break;
                case 'bot_status':
                    updateBotStatus(data.status);
                    break;
                case 'account_update':
                    updateAccountData(data);
                    break;
                case 'market_update':
                    updateMarketData(data);
                    break;
                case 'orders_update':
                    updateOrders(data.orders);
                    break;
                case 'microstructure_update':
                    updateMicrostructure(data.signals);
                    break;
                case 'analysis_update':
                    updateAnalysis(data.analysis);
                    break;
            }
        }
        
        function updateAllData(data) {
            updateBotStatus(data.bot_status);
            updateAccountData({
                account_value: data.account_value,
                position: data.position,
                unrealized_pnl: data.unrealized_pnl
            });
            updateMarketData({
                current_price: data.current_price,
                orderbook: data.orderbook
            });
            updateOrders(data.open_orders);
            updateMicrostructure(data.microstructure);
            updateAnalysis(data.analysis);
            
            document.getElementById('loop-count').textContent = data.loop_count;
            document.getElementById('trading-symbol').textContent = data.position.symbol || 'BTC';
            
            if (data.last_update) {
                const updateTime = new Date(data.last_update);
                document.getElementById('last-update').textContent = updateTime.toLocaleTimeString();
            }
        }
        
        function updateBotStatus(status) {
            const element = document.getElementById('bot-status');
            element.textContent = status;
            
            // Update status color
            element.className = 'status-value';
            if (status === 'ACTIVE' || status === 'RUNNING') {
                element.classList.add('status-positive');
            } else if (status === 'ERROR' || status === 'STOPPED') {
                element.classList.add('status-negative');
            } else {
                element.classList.add('status-neutral');
            }
            
            document.getElementById('strategy-mode').textContent = status;
        }
        
        function updateAccountData(data) {
            document.getElementById('account-value').textContent = ' + data.account_value.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            
            // Update position
            const positionElement = document.getElementById('position-size');
            if (data.position && data.position.size !== 0) {
                const sign = data.position.size > 0 ? '+' : '';
                positionElement.textContent = `${sign}${data.position.size.toFixed(4)} ${data.position.symbol || 'BTC'}`;
                positionElement.className = 'status-value ' + (data.position.size > 0 ? 'status-positive' : 'status-negative');
            } else {
                positionElement.textContent = 'No Position';
                positionElement.className = 'status-value status-neutral';
            }
            
            // Update PnL
            const pnlElement = document.getElementById('unrealized-pnl');
            const sign = data.unrealized_pnl > 0 ? '+' : '';
            pnlElement.textContent = `${sign}${data.unrealized_pnl.toFixed(2)}`;
            pnlElement.className = 'status-value ' + (data.unrealized_pnl > 0 ? 'status-positive' : 'status-negative');
        }
        
        function updateMarketData(data) {
            // Update current price
            document.getElementById('current-price').textContent = ' + data.current_price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            
            // Add to chart
            const newDataPoint = {
                x: Date.now(),
                y: data.current_price
            };
            chart.data.datasets[0].data.push(newDataPoint);
            
            // Keep only last 60 points
            if (chart.data.datasets[0].data.length > 60) {
                chart.data.datasets[0].data.shift();
            }
            
            chart.update('none');
            
            // Update orderbook
            updateOrderbook(data.orderbook);
        }
        
        function updateOrderbook(orderbook) {
            const bidsContainer = document.getElementById('bids-container');
            const asksContainer = document.getElementById('asks-container');
            
            // Clear existing
            bidsContainer.innerHTML = '';
            asksContainer.innerHTML = '';
            
            // Update bids
            if (orderbook.bids && orderbook.bids.length > 0) {
                orderbook.bids.slice(0, 10).forEach(([price, size]) => {
                    const bidElement = document.createElement('div');
                    bidElement.className = 'orderbook-level bid-level';
                    bidElement.innerHTML = `
                        <span>${price.toLocaleString()}</span>
                        <span>${size.toFixed(3)}</span>
                    `;
                    bidsContainer.appendChild(bidElement);
                });
            } else {
                bidsContainer.innerHTML = '<div style="text-align: center; color: #8a9ba8; padding: 20px;">No bids</div>';
            }
            
            // Update asks
            if (orderbook.asks && orderbook.asks.length > 0) {
                orderbook.asks.slice(0, 10).forEach(([price, size]) => {
                    const askElement = document.createElement('div');
                    askElement.className = 'orderbook-level ask-level';
                    askElement.innerHTML = `
                        <span>${price.toLocaleString()}</span>
                        <span>${size.toFixed(3)}</span>
                    `;
                    asksContainer.appendChild(askElement);
                });
            } else {
                asksContainer.innerHTML = '<div style="text-align: center; color: #8a9ba8; padding: 20px;">No asks</div>';
            }
        }
        
        function updateOrders(orders) {
            const ordersContainer = document.getElementById('orders-list');
            ordersContainer.innerHTML = '';
            
            if (orders && orders.length > 0) {
                orders.forEach(order => {
                    const orderElement = document.createElement('div');
                    orderElement.className = 'order-item';
                    
                    const side = order.side === 'B' ? 'BUY' : 'SELL';
                    const sideClass = order.side === 'B' ? 'order-side-buy' : 'order-side-sell';
                    
                    orderElement.innerHTML = `
                        <span class="${sideClass}">${side}</span>
                        <span>${parseFloat(order.sz).toFixed(4)}</span>
                        <span>${parseFloat(order.limitPx).toLocaleString()}</span>
                        <span>Active</span>
                    `;
                    ordersContainer.appendChild(orderElement);
                });
            } else {
                ordersContainer.innerHTML = '<div style="text-align: center; color: #8a9ba8; padding: 20px;">No orders</div>';
            }
        }
        
        function updateMicrostructure(signals) {
            if (!signals || Object.keys(signals).length === 0) return;
            
            const metrics = [
                { key: 'flow_confidence', label: 'Flow Confidence' },
                { key: 'volume_imbalance', label: 'Volume Imbalance' },
                { key: 'net_aggressive_buying', label: 'Net Aggressive Buying' },
                { key: 'overall_momentum', label: 'Overall Momentum' },
                { key: 'adverse_selection_risk', label: 'Adverse Selection Risk' },
                { key: 'order_velocity', label: 'Order Velocity' },
                { key: 'spread_volatility', label: 'Spread Volatility' },
                { key: 'trade_velocity', label: 'Trade Velocity' },
                { key: 'depth_pressure', label: 'Depth Pressure' },
                { key: 'vwap_deviation', label: 'VWAP Deviation' },
                { key: 'large_order_flow', label: 'Large Order Flow' },
                { key: 'accumulation_score', label: 'Accumulation Score' }
            ];
            
            const container = document.getElementById('microstructure-metrics');
            const metricElements = container.querySelectorAll('.metric');
            
            metrics.forEach((metric, index) => {
                if (metricElements[index] && signals[metric.key] !== undefined) {
                    const valueElement = metricElements[index].querySelector('.metric-value');
                    const value = signals[metric.key];
                    
                    // Format value
                    let formattedValue;
                    if (typeof value === 'number') {
                        if (metric.key === 'trade_velocity') {
                            formattedValue = value.toFixed(2) + '/s';
                        } else {
                            formattedValue = value.toFixed(3);
                        }
                    } else {
                        formattedValue = String(value);
                    }
                    
                    valueElement.textContent = formattedValue;
                    
                    // Color coding for certain metrics
                    valueElement.className = 'metric-value';
                    if (typeof value === 'number') {
                        if (['volume_imbalance', 'net_aggressive_buying', 'overall_momentum', 'depth_pressure', 'large_order_flow', 'accumulation_score'].includes(metric.key)) {
                            if (value > 0.1) {
                                valueElement.classList.add('status-positive');
                            } else if (value < -0.1) {
                                valueElement.classList.add('status-negative');
                            }
                        } else if (metric.key === 'adverse_selection_risk') {
                            if (value > 0.6) {
                                valueElement.classList.add('status-negative');
                            } else if (value < 0.3) {
                                valueElement.classList.add('status-positive');
                            } else {
                                valueElement.classList.add('status-neutral');
                            }
                        } else if (metric.key === 'flow_confidence') {
                            if (value > 0.7) {
                                valueElement.classList.add('status-positive');
                            } else if (value < 0.4) {
                                valueElement.classList.add('status-negative');
                            } else {
                                valueElement.classList.add('status-neutral');
                            }
                        }
                    }
                }
            });
        }
        
        function updateAnalysis(analysis) {
            if (!analysis) return;
            
            const analysisElement = document.getElementById('analysis-text');
            
            let html = '';
            
            if (analysis.current_assessment) {
                const signalClass = analysis.signal_type === 'bullish' ? 'signal-bullish' : 
                                  analysis.signal_type === 'bearish' ? 'signal-bearish' : 'signal-neutral';
                
                html += `<p><span class="signal-indicator ${signalClass}"></span><strong>Current Market Assessment:</strong> ${analysis.current_assessment}</p><br>`;
            }
            
            if (analysis.risk_factors) {
                html += `<p><span class="signal-indicator signal-neutral"></span><strong>Risk Factors:</strong> ${analysis.risk_factors}</p><br>`;
            }
            
            if (analysis.strategy_recommendation) {
                const recSignalClass = analysis.signal_type === 'bullish' ? 'signal-bullish' : 'signal-neutral';
                html += `<p><span class="signal-indicator ${recSignalClass}"></span><strong>Strategy Recommendation:</strong> ${analysis.strategy_recommendation}</p>`;
            }
            
            if (html) {
                analysisElement.innerHTML = html;
            }
        }
        
        // Initialize connection
        connectWebSocket();
        
        console.log('Dashboard initialized - connecting to bot...');
    </script>
</body>
</html>
        """
        
        # Write dashboard file
        with open('dashboard.html', 'w') as f:
            f.write(dashboard_html)
        
        # Start HTTP server
        def run_server():
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", self.port), handler) as httpd:
                self.server = httpd
                print(f"✅ Dashboard server running at http://localhost:{self.port}/dashboard.html")
                httpd.serve_forever()
        
        self.thread = Thread(target=run_server, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the dashboard server"""
        if self.server:
            self.server.shutdown()
            print("🛑 Dashboard server stopped")

# Integration helpers for main.py
def integrate_web_interface(bot_instance):
    """Add web interface to existing bot"""
    web_interface = WebInterface(bot_instance.config, bot_instance)
    dashboard_server = DashboardServer()
    
    # Add web interface to bot
    bot_instance.web_interface = web_interface
    bot_instance.dashboard_server = dashboard_server
    
    return web_interface, dashboard_server

async def start_web_services(bot_instance):
    """Start web interface services"""
    print("🌐 Starting web services...")
    
    # Start dashboard server
    bot_instance.dashboard_server.start()
    
    # Start WebSocket server
    await bot_instance.web_interface.start_server()

def update_web_interface(bot_instance, **kwargs):
    """Helper function to update web interface from bot"""
    if not hasattr(bot_instance, 'web_interface'):
        return
    
    web = bot_instance.web_interface
    
    # Update various data types based on provided kwargs
    if 'bot_status' in kwargs:
        web.update_bot_status(kwargs['bot_status'])
    
    if 'account_data' in kwargs:
        data = kwargs['account_data']
        web.update_account_data(
            data.get('account_value', 0),
            data.get('position', {}),
            data.get('unrealized_pnl', 0)
        )
    
    if 'market_data' in kwargs:
        data = kwargs['market_data']
        web.update_market_data(
            data.get('current_price', 0),
            data.get('orderbook', {})
        )
    
    if 'orders' in kwargs:
        web.update_orders(kwargs['orders'])
    
    if 'microstructure' in kwargs:
        signals = kwargs['microstructure']
        # Convert signals object to dict if needed
        if hasattr(signals, '__dict__'):
            signals_dict = {
                'flow_confidence': signals.flow_confidence,
                'volume_imbalance': signals.volume_imbalance,
                'net_aggressive_buying': signals.net_aggressive_buying,
                'overall_momentum': signals.overall_momentum,
                'adverse_selection_risk': signals.adverse_selection_risk,
                'order_velocity': signals.order_velocity,
                'spread_volatility': signals.spread_volatility,
                'trade_velocity': signals.trade_velocity,
                'depth_pressure': signals.depth_pressure,
                'vwap_deviation': signals.vwap_deviation,
                'large_order_flow': signals.large_order_flow,
                'accumulation_score': signals.accumulation_score
            }
        else:
            signals_dict = signals
        
        web.update_microstructure(signals_dict)
    
    if 'analysis' in kwargs:
        web.update_analysis(kwargs['analysis'])
    
    if 'loop_count' in kwargs:
        web.update_loop_count(kwargs['loop_count'])