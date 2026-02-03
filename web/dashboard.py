#!/usr/bin/env python3
"""
Web Dashboard - Real-time System Monitoring
FastAPI-based dashboard with WebSocket live updates
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
import json
import time
from datetime import datetime
from collections import deque

sys.path.append(str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
except ImportError:
    print("FastAPI not installed. Run: pip install fastapi uvicorn websockets")
    sys.exit(1)

from autonomous.background_tasks import BackgroundTaskManager
from core.persistent_memory import PersistentMemory


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


class DashboardServer:
    """
    Web Dashboard Server

    Features:
    - Real-time system monitoring
    - Task queue visualization
    - Worker scaling metrics
    - Performance graphs
    - WebSocket live updates
    - REST API endpoints
    """

    def __init__(self, port: int = 8080):
        self.port = port
        self.app = FastAPI(title="OpenClaw Dashboard", version="1.0.0")
        self.connection_manager = ConnectionManager()

        # Initialize systems
        workspace = Path(__file__).parent.parent
        self.task_manager = BackgroundTaskManager(
            str(workspace / "background_tasks.db"),
            min_workers=1,
            max_workers=8,
            enable_auto_scaling=True
        )
        self.memory = PersistentMemory(str(workspace / "persistent_memory.db"))

        # Metrics history (last 100 data points)
        self.metrics_history = deque(maxlen=100)
        self.last_update = time.time()

        # Setup routes
        self._setup_routes()

        # Start background task manager
        self.task_manager.start_workers()

        # Start metrics collector
        self.metrics_task = None

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Dashboard home page"""
            return self._generate_dashboard_html()

        @self.app.get("/api/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - self.last_update
            }

        @self.app.get("/api/system/stats")
        async def system_stats():
            """Get system statistics"""
            stats = self._get_system_stats()
            return JSONResponse(stats)

        @self.app.get("/api/workers/stats")
        async def worker_stats():
            """Get worker statistics"""
            return JSONResponse(self.task_manager.get_worker_stats())

        @self.app.get("/api/tasks/queued")
        async def queued_tasks():
            """Get queued tasks"""
            tasks = self.task_manager.get_queued_tasks()
            return JSONResponse(tasks)

        @self.app.get("/api/tasks/running")
        async def running_tasks():
            """Get running tasks"""
            tasks = self.task_manager.get_running_tasks()
            return JSONResponse(tasks)

        @self.app.get("/api/tasks/status/{task_id}")
        async def task_status(task_id: int):
            """Get task status by ID"""
            status = self.task_manager.get_task_status(task_id)
            if status:
                return JSONResponse(status)
            return JSONResponse({"error": "Task not found"}, status_code=404)

        @self.app.get("/api/metrics/history")
        async def metrics_history():
            """Get metrics history"""
            return JSONResponse(list(self.metrics_history))

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for live updates"""
            await self.connection_manager.connect(websocket)
            try:
                while True:
                    # Wait for client messages (ping)
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)

    def _get_system_stats(self) -> Dict:
        """Collect comprehensive system statistics"""
        try:
            import psutil

            # System resources
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            system_stats = {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': round(disk.percent, 1),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
            }
        except:
            system_stats = {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_used_gb': 0,
                'memory_total_gb': 0,
                'disk_percent': 0,
                'disk_used_gb': 0,
                'disk_total_gb': 0,
            }

        # Worker stats
        worker_stats = self.task_manager.get_worker_stats()

        # Task stats
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
        task_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Combine all stats
        return {
            'timestamp': datetime.now().isoformat(),
            'system': system_stats,
            'workers': worker_stats,
            'tasks': {
                'pending': task_counts.get('pending', 0),
                'in_progress': task_counts.get('in_progress', 0),
                'completed': task_counts.get('completed', 0),
                'failed': task_counts.get('failed', 0)
            }
        }

    async def _metrics_broadcaster(self):
        """Periodically broadcast metrics to all connected clients"""
        while True:
            try:
                await asyncio.sleep(2)  # Update every 2 seconds

                if self.connection_manager.active_connections:
                    stats = self._get_system_stats()

                    # Add to history
                    self.metrics_history.append(stats)

                    # Broadcast to all clients
                    await self.connection_manager.broadcast({
                        'type': 'metrics_update',
                        'data': stats
                    })

            except Exception as e:
                print(f"[METRICS] Error broadcasting: {e}")
                await asyncio.sleep(5)

    def _generate_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>OpenClaw Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419;
            color: #e6edf3;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header .subtitle { opacity: 0.9; font-size: 1.1em; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .card h2 {
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #58a6ff;
            border-bottom: 2px solid #30363d;
            padding-bottom: 10px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px;
            background: #0d1117;
            border-radius: 5px;
        }
        .metric-label { font-weight: 500; }
        .metric-value {
            font-weight: 700;
            color: #58a6ff;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status.healthy { background: #238636; color: white; }
        .status.warning { background: #9e6a03; color: white; }
        .status.error { background: #da3633; color: white; }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #0d1117;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #58a6ff, #1f6feb);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75em;
            font-weight: 700;
        }
        .worker-box {
            display: inline-block;
            width: 40px;
            height: 40px;
            margin: 5px;
            border-radius: 5px;
            text-align: center;
            line-height: 40px;
            font-weight: 700;
            font-size: 0.9em;
        }
        .worker-active {
            background: #238636;
            box-shadow: 0 0 10px #238636;
        }
        .worker-idle {
            background: #484f58;
        }
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 600;
            z-index: 1000;
        }
        .connected { background: #238636; }
        .disconnected { background: #da3633; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .updating { animation: pulse 1s infinite; }
    </style>
</head>
<body>
    <div class="connection-status disconnected" id="connectionStatus">
        Disconnected
    </div>

    <div class="header">
        <h1>OpenClaw Dashboard</h1>
        <div class="subtitle">Real-time System Monitoring & Task Management</div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>System Resources</h2>
            <div class="metric">
                <span class="metric-label">CPU Usage</span>
                <span class="metric-value" id="cpuPercent">--%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="cpuBar" style="width: 0%">0%</div>
            </div>

            <div class="metric">
                <span class="metric-label">Memory Usage</span>
                <span class="metric-value" id="memoryPercent">--%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="memoryBar" style="width: 0%">0%</div>
            </div>

            <div class="metric">
                <span class="metric-label">Disk Usage</span>
                <span class="metric-value" id="diskPercent">--%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="diskBar" style="width: 0%">0%</div>
            </div>
        </div>

        <div class="card">
            <h2>Worker Pool</h2>
            <div class="metric">
                <span class="metric-label">Current Workers</span>
                <span class="metric-value" id="currentWorkers">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Active Workers</span>
                <span class="metric-value" id="activeWorkers">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Auto-Scaling</span>
                <span class="metric-value" id="autoScaling">-</span>
            </div>
            <div id="workerBoxes" style="margin-top: 15px;"></div>
        </div>

        <div class="card">
            <h2>Task Queue</h2>
            <div class="metric">
                <span class="metric-label">Queue Depth</span>
                <span class="metric-value" id="queueDepth">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Pending</span>
                <span class="metric-value" id="tasksPending">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">In Progress</span>
                <span class="metric-value" id="tasksInProgress">-</span>
            </div>
            <div class="metric">
                <span class="metric-label">Completed</span>
                <span class="metric-value" id="tasksCompleted">-</span>
            </div>
        </div>

        <div class="card">
            <h2>System Health</h2>
            <div class="metric">
                <span class="metric-label">Status</span>
                <span class="status healthy" id="healthStatus">Healthy</span>
            </div>
            <div class="metric">
                <span class="metric-label">Last Update</span>
                <span class="metric-value" id="lastUpdate">Never</span>
            </div>
            <div class="metric">
                <span class="metric-label">Update Frequency</span>
                <span class="metric-value">2s</span>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let reconnectInterval = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('connectionStatus').textContent = 'Connected';
                document.getElementById('connectionStatus').className = 'connection-status connected';

                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }

                // Send periodic pings
                setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send('ping');
                    }
                }, 30000);
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);

                if (message.type === 'metrics_update') {
                    updateDashboard(message.data);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('connectionStatus').textContent = 'Disconnected';
                document.getElementById('connectionStatus').className = 'connection-status disconnected';

                // Try to reconnect
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(() => {
                        console.log('Attempting to reconnect...');
                        connectWebSocket();
                    }, 5000);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function updateDashboard(data) {
            // System resources
            document.getElementById('cpuPercent').textContent = data.system.cpu_percent + '%';
            document.getElementById('cpuBar').style.width = data.system.cpu_percent + '%';
            document.getElementById('cpuBar').textContent = data.system.cpu_percent + '%';

            document.getElementById('memoryPercent').textContent = data.system.memory_percent + '%';
            document.getElementById('memoryBar').style.width = data.system.memory_percent + '%';
            document.getElementById('memoryBar').textContent = data.system.memory_percent + '%';

            document.getElementById('diskPercent').textContent = data.system.disk_percent + '%';
            document.getElementById('diskBar').style.width = data.system.disk_percent + '%';
            document.getElementById('diskBar').textContent = data.system.disk_percent + '%';

            // Workers
            document.getElementById('currentWorkers').textContent =
                `${data.workers.current_workers} / ${data.workers.max_workers}`;
            document.getElementById('activeWorkers').textContent = data.workers.active_workers;
            document.getElementById('autoScaling').textContent =
                data.workers.auto_scaling_enabled ? 'Enabled' : 'Disabled';

            // Worker boxes
            const workerBoxes = document.getElementById('workerBoxes');
            workerBoxes.innerHTML = '';
            for (let i = 0; i < data.workers.max_workers; i++) {
                const box = document.createElement('div');
                box.className = i < data.workers.current_workers ?
                    'worker-box worker-active' : 'worker-box worker-idle';
                box.textContent = i + 1;
                workerBoxes.appendChild(box);
            }

            // Tasks
            document.getElementById('queueDepth').textContent = data.workers.queue_depth;
            document.getElementById('tasksPending').textContent = data.tasks.pending;
            document.getElementById('tasksInProgress').textContent = data.tasks.in_progress;
            document.getElementById('tasksCompleted').textContent = data.tasks.completed;

            // Last update
            const now = new Date();
            document.getElementById('lastUpdate').textContent =
                now.toLocaleTimeString();
        }

        // Connect on load
        connectWebSocket();

        // Also poll REST API as fallback
        setInterval(async () => {
            if (ws && ws.readyState === WebSocket.OPEN) return;

            try {
                const response = await fetch('/api/system/stats');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Failed to fetch stats:', error);
            }
        }, 5000);
    </script>
</body>
</html>
"""

    async def start_async(self):
        """Start the dashboard server asynchronously"""
        # Start metrics broadcaster
        self.metrics_task = asyncio.create_task(self._metrics_broadcaster())

        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    def start(self):
        """Start the dashboard server"""
        print("=" * 70)
        print("OpenClaw Dashboard Server")
        print("=" * 70)
        print(f"\nDashboard URL: http://localhost:{self.port}")
        print("WebSocket URL: ws://localhost:{self.port}/ws")
        print("\nPress Ctrl+C to stop")
        print("=" * 70)

        asyncio.run(self.start_async())

    def stop(self):
        """Stop the dashboard server"""
        if self.metrics_task:
            self.metrics_task.cancel()
        self.task_manager.close()
        self.memory.close()


def main():
    """Run dashboard server"""
    server = DashboardServer(port=8080)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.stop()


if __name__ == "__main__":
    main()
