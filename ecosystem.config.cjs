module.exports = {
    apps: [
        {
            name: 'openclaw-gateway',
            script: 'openclaw.mjs',
            args: 'gateway',
            cwd: 'C:\\Users\\User\\Documents\\AI\\OpenClaw',

            // Restart settings for resilience
            autorestart: true,
            max_restarts: 50,
            min_uptime: '10s',
            restart_delay: 5000,

            // Exponential backoff on repeated crashes
            exp_backoff_restart_delay: 1000,

            // Memory limit (restart if exceeded)
            max_memory_restart: '1G',

            // Environment
            env: {
                NODE_ENV: 'production',
                // Force Node to keep timers alive after disconnect
                UV_THREADPOOL_SIZE: 4,
            },

            // Logging
            error_file: 'C:\\Users\\User\\.openclaw\\logs\\pm2-error.log',
            out_file: 'C:\\Users\\User\\.openclaw\\logs\\pm2-out.log',
            merge_logs: true,
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

            // Watch for config changes (optional - disable if causing issues)
            watch: false,

            // Kill timeout (give graceful shutdown time)
            kill_timeout: 10000,

            // Wait for process to be ready
            wait_ready: false,
        }
    ]
};
