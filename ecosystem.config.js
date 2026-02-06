module.exports = {
    apps: [
        {
            name: "openclaw-gateway",
            script: "C:\\Users\\User\\Documents\\AI\\OpenClaw\\dist\\index.js",
            args: "gateway --port 18789",
            cwd: "C:\\Users\\User\\Documents\\AI\\OpenClaw",
            interpreter: "node",

            // Auto-restart configuration
            autorestart: true,
            max_restarts: 50,
            min_uptime: "10s",
            restart_delay: 5000, // 5 seconds between restarts

            // Memory watchdog - restart if memory exceeds limit
            max_memory_restart: "500M",

            // Graceful shutdown
            kill_timeout: 5000,

            // Wait for process to signal readiness
            wait_ready: false, // Set to true if OpenClaw implements process.send('ready')

            // Environment
            env: {
                NODE_ENV: "production",
            },

            // Logging
            error_file: "C:\\tmp\\openclaw\\pm2-error.log",
            out_file: "C:\\tmp\\openclaw\\pm2-out.log",
            merge_logs: true,
            log_date_format: "YYYY-MM-DD HH:mm:ss",
        },
    ],
};
