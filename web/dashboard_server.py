#!/usr/bin/env python3
"""Web Dashboard Server - Real-time monitoring dashboard"""
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory
from monitoring.performance_monitor import PerformanceMonitor
from monitoring.keep_alive import KeepAliveMonitor
from monitoring.error_dashboard import ErrorDashboard

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize systems
workspace = Path(__file__).parent.parent
memory = PersistentMemory(str(workspace / "memory.db"))
perf_monitor = PerformanceMonitor()
keep_alive = KeepAliveMonitor(check_interval=60)
error_dashboard = ErrorDashboard()

# Track connected clients
connected_clients = 0

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/system/stats')
def get_system_stats():
    """Get system statistics"""
    stats = perf_monitor.get_system_stats()

    # Add memory stats
    cursor = memory.conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    task_stats = dict(cursor.fetchall())

    stats['tasks'] = {
        'pending': task_stats.get('pending', 0),
        'in_progress': task_stats.get('in_progress', 0),
        'completed': task_stats.get('completed', 0)
    }

    # Add uptime
    cursor.execute("SELECT MIN(created_at) FROM decisions")
    first_decision = cursor.fetchone()[0]
    if first_decision:
        start_time = datetime.fromisoformat(first_decision)
        uptime = (datetime.now() - start_time).total_seconds()
        stats['uptime_hours'] = round(uptime / 3600, 1)
    else:
        stats['uptime_hours'] = 0

    return jsonify(stats)

@app.route('/api/errors/summary')
def get_error_summary():
    """Get error summary"""
    report = error_dashboard.generate_report(hours=24)
    return jsonify(report['summary'])

@app.route('/api/errors/report')
def get_error_report():
    """Get full error report"""
    hours = request.args.get('hours', 24, type=int)
    report = error_dashboard.generate_report(hours=hours)
    return jsonify(report)

@app.route('/api/tasks/recent')
def get_recent_tasks():
    """Get recent tasks"""
    limit = request.args.get('limit', 10, type=int)

    cursor = memory.conn.cursor()
    cursor.execute("""
        SELECT task_id, description, status, created_at, updated_at
        FROM tasks
        ORDER BY updated_at DESC
        LIMIT ?
    """, (limit,))

    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            'task_id': row['task_id'],
            'description': row['description'],
            'status': row['status'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })

    return jsonify(tasks)

@app.route('/api/decisions/recent')
def get_recent_decisions():
    """Get recent decisions"""
    limit = request.args.get('limit', 20, type=int)

    cursor = memory.conn.cursor()
    cursor.execute("""
        SELECT decision, rationale, created_at, tags
        FROM decisions
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    decisions = []
    for row in cursor.fetchall():
        decisions.append({
            'decision': row['decision'],
            'rationale': row['rationale'],
            'created_at': row['created_at'],
            'tags': row['tags']
        })

    return jsonify(decisions)

@app.route('/api/health')
def get_health():
    """Get system health"""
    health = keep_alive.run_health_checks()

    all_healthy = all(check['healthy'] for check in health.values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': health
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    global connected_clients
    connected_clients += 1
    emit('connection_response', {'status': 'connected', 'clients': connected_clients})
    print(f"Client connected. Total clients: {connected_clients}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    global connected_clients
    connected_clients -= 1
    print(f"Client disconnected. Total clients: {connected_clients}")

@socketio.on('request_update')
def handle_update_request():
    """Handle update request from client"""
    stats = perf_monitor.get_system_stats()
    emit('system_update', stats)

# Background task to push updates
def background_updates():
    """Send periodic updates to all connected clients"""
    while True:
        if connected_clients > 0:
            stats = perf_monitor.get_system_stats()

            # Add timestamp
            stats['timestamp'] = datetime.now().isoformat()

            socketio.emit('system_update', stats)

        time.sleep(2)  # Update every 2 seconds

# Start background thread
update_thread = threading.Thread(target=background_updates, daemon=True)
update_thread.start()

if __name__ == '__main__':
    print("=" * 60)
    print("WEB DASHBOARD SERVER")
    print("=" * 60)
    print("\nStarting server...")
    print("Dashboard URL: http://localhost:5000")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
