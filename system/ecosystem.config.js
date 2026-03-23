// AUROS AI — PM2 Process Manager Configuration
// Manages 5 always-on processes: Telegram bot, task worker, scheduler, API, dashboard
//
// Usage:
//   pm2 start system/ecosystem.config.js
//   pm2 status
//   pm2 logs
//   pm2 restart all
//   pm2 save && pm2 startup  (to persist across reboots)

module.exports = {
  apps: [
    {
      name: "auros-telegram",
      script: "system/telegram_bot.py",
      interpreter: "./venv/bin/python3",
      cwd: __dirname + "/..",
      watch: false,
      max_restarts: 20,
      restart_delay: 5000,
      autorestart: true,
      log_file: "logs/pm2-telegram.log",
      error_file: "logs/pm2-telegram-error.log",
      out_file: "logs/pm2-telegram-out.log",
      env: {
        PYTHONPATH: __dirname + "/..",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "auros-worker",
      script: "system/task_worker.py",
      interpreter: "./venv/bin/python3",
      cwd: __dirname + "/..",
      watch: false,
      max_restarts: 20,
      restart_delay: 5000,
      autorestart: true,
      log_file: "logs/pm2-worker.log",
      error_file: "logs/pm2-worker-error.log",
      out_file: "logs/pm2-worker-out.log",
      env: {
        PYTHONPATH: __dirname + "/..",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "auros-scheduler",
      script: "system/scheduler.py",
      interpreter: "./venv/bin/python3",
      cwd: __dirname + "/..",
      watch: false,
      max_restarts: 20,
      restart_delay: 10000,
      autorestart: true,
      log_file: "logs/pm2-scheduler.log",
      error_file: "logs/pm2-scheduler-error.log",
      out_file: "logs/pm2-scheduler-out.log",
      env: {
        PYTHONPATH: __dirname + "/..",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "auros-api",
      script: "system/api.py",
      interpreter: "./venv/bin/python3",
      cwd: __dirname + "/..",
      watch: false,
      max_restarts: 20,
      restart_delay: 5000,
      autorestart: true,
      log_file: "logs/pm2-api.log",
      error_file: "logs/pm2-api-error.log",
      out_file: "logs/pm2-api-out.log",
      env: {
        PYTHONPATH: __dirname + "/..",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "auros-dashboard",
      script: "npx",
      args: "vite --port 3200 --host",
      cwd: __dirname + "/dashboard",
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      autorestart: true,
      log_file: __dirname + "/../logs/pm2-dashboard.log",
      error_file: __dirname + "/../logs/pm2-dashboard-error.log",
      out_file: __dirname + "/../logs/pm2-dashboard-out.log",
    },
  ],
};
