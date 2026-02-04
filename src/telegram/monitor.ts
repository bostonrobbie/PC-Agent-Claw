import { type RunOptions, run } from "@grammyjs/runner";
import type { OpenClawConfig } from "../config/config.js";
import { loadConfig } from "../config/config.js";
import { resolveAgentMaxConcurrent } from "../config/agent-limits.js";
import { computeBackoff, sleepWithAbort } from "../infra/backoff.js";
import { formatErrorMessage } from "../infra/errors.js";
import { formatDurationMs } from "../infra/format-duration.js";
import type { RuntimeEnv } from "../runtime.js";
import { resolveTelegramAccount } from "./accounts.js";
import { resolveTelegramAllowedUpdates } from "./allowed-updates.js";
import { createTelegramBot } from "./bot.js";
import { isRecoverableTelegramNetworkError } from "./network-errors.js";
import { makeProxyFetch } from "./proxy.js";
import { sendMessageTelegram } from "./send.js";
import { readTelegramUpdateOffset, writeTelegramUpdateOffset } from "./update-offset-store.js";
import { startTelegramWebhook } from "./webhook.js";

export type MonitorTelegramOpts = {
  token?: string;
  accountId?: string;
  config?: OpenClawConfig;
  runtime?: RuntimeEnv;
  abortSignal?: AbortSignal;
  useWebhook?: boolean;
  webhookPath?: string;
  webhookPort?: number;
  webhookSecret?: string;
  proxyFetch?: typeof fetch;
  webhookUrl?: string;
};

export function createTelegramRunnerOptions(cfg: OpenClawConfig): RunOptions<unknown> {
  return {
    sink: {
      concurrency: resolveAgentMaxConcurrent(cfg),
    },
    runner: {
      fetch: {
        // Match grammY defaults
        timeout: 30,
        // Request reactions without dropping default update types.
        allowed_updates: resolveTelegramAllowedUpdates(),
      },
      // Suppress grammY getUpdates stack traces; we log concise errors ourselves.
      silent: true,
      // Retry transient failures for an extended window to maximize resilience.
      // 30 minutes allows recovery from longer network outages (e.g., PC sleep/wake).
      maxRetryTime: 30 * 60 * 1000,
      retryInterval: "exponential",
    },
  };
}

const TELEGRAM_POLL_RESTART_POLICY = {
  // Start with faster retries (1s) for quick recovery from transient failures
  initialMs: 1000,
  // Cap at 15s max delay for faster recovery from longer outages
  maxMs: 15_000,
  factor: 1.5,
  jitter: 0.25,
};

// Reset restart attempts after this many ms of successful operation
const RESTART_ATTEMPTS_RESET_MS = 5 * 60 * 1000; // 5 minutes

// ─────────────────────────────────────────────────────────────────────────────
// Health Alert Configuration
// ─────────────────────────────────────────────────────────────────────────────

// Send an alert after this many consecutive failures
const ALERT_AFTER_FAILURES = 3;

// Minimum time between alerts (30 minutes)
const ALERT_COOLDOWN_MS = 30 * 60 * 1000;

// ─────────────────────────────────────────────────────────────────────────────
// Internal Watchdog: Self-terminate if no activity for this duration
// This allows PM2 or another process manager to restart us on freeze
// NOTE: Set high enough to allow long-running CLI tasks (10+ min) to complete
// ─────────────────────────────────────────────────────────────────────────────
const WATCHDOG_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

/**
 * Attempt to send a direct Telegram alert message.
 * This uses sendMessage API which is independent of polling.
 * Silently fails if the network is completely down.
 */
async function sendConnectionAlert(params: {
  token: string;
  alertChatId: string | number;
  message: string;
  accountId?: string;
  logError: (msg: string) => void;
}): Promise<boolean> {
  try {
    await sendMessageTelegram(String(params.alertChatId), params.message, {
      token: params.token,
      accountId: params.accountId,
      silent: false, // We want notification for alerts
    });
    return true;
  } catch (err) {
    // Alert sending failed - network is likely completely down
    params.logError(`Failed to send connection alert: ${formatErrorMessage(err)}`);
    return false;
  }
}

/**
 * Resolve the chat ID to send alerts to.
 * Priority: config.alertChatId > first allowFrom entry > undefined
 */
function resolveAlertChatId(cfg: OpenClawConfig, accountId?: string): string | number | undefined {
  const telegramConfig = cfg.channels?.telegram as {
    alertChatId?: string | number;
    allowFrom?: Array<string | number>;
    accounts?: Record<string, { alertChatId?: string | number; allowFrom?: Array<string | number> }>;
  } | undefined;

  // Check account-specific config first
  if (accountId && telegramConfig?.accounts?.[accountId]?.alertChatId) {
    return telegramConfig.accounts[accountId].alertChatId;
  }

  // Check global telegram config
  if (telegramConfig?.alertChatId) {
    return telegramConfig.alertChatId;
  }

  // Fall back to first allowFrom entry (likely the owner)
  if (accountId && telegramConfig?.accounts?.[accountId]?.allowFrom?.[0]) {
    return telegramConfig.accounts[accountId].allowFrom[0];
  }
  if (telegramConfig?.allowFrom?.[0]) {
    return telegramConfig.allowFrom[0];
  }

  return undefined;
}

const isGetUpdatesConflict = (err: unknown) => {
  if (!err || typeof err !== "object") return false;
  const typed = err as {
    error_code?: number;
    errorCode?: number;
    description?: string;
    method?: string;
    message?: string;
  };
  const errorCode = typed.error_code ?? typed.errorCode;
  if (errorCode !== 409) return false;
  const haystack = [typed.method, typed.description, typed.message]
    .filter((value): value is string => typeof value === "string")
    .join(" ")
    .toLowerCase();
  return haystack.includes("getupdates");
};

const NETWORK_ERROR_SNIPPETS = [
  "fetch failed",
  "network",
  "timeout",
  "socket",
  "econnreset",
  "econnrefused",
  "undici",
];

const isNetworkRelatedError = (err: unknown) => {
  if (!err) return false;
  const message = formatErrorMessage(err).toLowerCase();
  if (!message) return false;
  return NETWORK_ERROR_SNIPPETS.some((snippet) => message.includes(snippet));
};

export async function monitorTelegramProvider(opts: MonitorTelegramOpts = {}) {
  const cfg = opts.config ?? loadConfig();
  const account = resolveTelegramAccount({
    cfg,
    accountId: opts.accountId,
  });
  const token = opts.token?.trim() || account.token;
  if (!token) {
    throw new Error(
      `Telegram bot token missing for account "${account.accountId}" (set channels.telegram.accounts.${account.accountId}.botToken/tokenFile or TELEGRAM_BOT_TOKEN for default).`,
    );
  }

  const proxyFetch =
    opts.proxyFetch ??
    (account.config.proxy ? makeProxyFetch(account.config.proxy as string) : undefined);

  let lastUpdateId = await readTelegramUpdateOffset({
    accountId: account.accountId,
  });
  const persistUpdateId = async (updateId: number) => {
    if (lastUpdateId !== null && updateId <= lastUpdateId) return;
    lastUpdateId = updateId;
    try {
      await writeTelegramUpdateOffset({
        accountId: account.accountId,
        updateId,
      });
    } catch (err) {
      (opts.runtime?.error ?? console.error)(
        `telegram: failed to persist update offset: ${String(err)}`,
      );
    }
  };

  const bot = createTelegramBot({
    token,
    runtime: opts.runtime,
    proxyFetch,
    config: cfg,
    accountId: account.accountId,
    updateOffset: {
      lastUpdateId,
      onUpdateId: persistUpdateId,
    },
  });

  if (opts.useWebhook) {
    await startTelegramWebhook({
      token,
      accountId: account.accountId,
      config: cfg,
      path: opts.webhookPath,
      port: opts.webhookPort,
      secret: opts.webhookSecret,
      runtime: opts.runtime as RuntimeEnv,
      fetch: proxyFetch,
      abortSignal: opts.abortSignal,
      publicUrl: opts.webhookUrl,
    });
    return;
  }

  // Use grammyjs/runner for concurrent update processing
  let restartAttempts = 0;
  let lastSuccessfulStart = Date.now();

  // Alert state tracking
  let lastAlertSentAt = 0;
  let alertSentForCurrentOutage = false;
  let outageStartTime = 0;

  const log = opts.runtime?.log ?? console.log;
  const logError = opts.runtime?.error ?? console.error;

  // Resolve where to send alerts
  const alertChatId = resolveAlertChatId(cfg, account.accountId);
  /* eslint-disable-next-line no-console */
  if (alertChatId) {
    log(`Telegram monitor started. Network alerts will be sent to: ${alertChatId}`);
  } else {
    log("Telegram monitor started. No alert target configured (network errors will not be notified).");
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Internal Watchdog: DISABLED for all-day agent operation
  // The watchdog can't distinguish "frozen" from "busy working on long tasks"
  // We rely on external auto-restart script (gateway-autostart.cmd) for crash recovery
  // If gateway crashes completely, port 18789 stops listening and script restarts it
  // ─────────────────────────────────────────────────────────────────────────────
  // let lastActivityTime = Date.now();
  // const touchActivity = () => { lastActivityTime = Date.now(); };
  // const watchdogInterval = setInterval(() => { ... }, 60_000);

  while (!opts.abortSignal?.aborted) {
    const runnerStartTime = Date.now();
    // touchActivity(); // Disabled - no internal watchdog
    const runner = run(bot, createTelegramRunnerOptions(cfg));
    const stopOnAbort = () => {
      if (opts.abortSignal?.aborted) {
        void runner.stop();
      }
    };
    opts.abortSignal?.addEventListener("abort", stopOnAbort, { once: true });
    try {
      // runner.task() returns a promise that resolves when the runner stops
      await runner.task();
      return;
    } catch (err) {
      if (opts.abortSignal?.aborted) {
        throw err;
      }
      const isConflict = isGetUpdatesConflict(err);
      const isRecoverable = isRecoverableTelegramNetworkError(err, { context: "polling" });
      const isNetworkError = isNetworkRelatedError(err);
      if (!isConflict && !isRecoverable && !isNetworkError) {
        throw err;
      }

      // Reset restart attempts if we've been running stably for a while
      const runDuration = Date.now() - runnerStartTime;
      if (runDuration >= RESTART_ATTEMPTS_RESET_MS) {
        // Connection was stable - send recovery notification if we had sent an alert
        if (alertSentForCurrentOutage && alertChatId) {
          const outageDuration = Date.now() - outageStartTime;
          const recoveryMessage = [
            "✅ *OpenClaw Bot Recovered*\n",
            `Connection restored after ${formatDurationMs(outageDuration)}.`,
            "I'm back online and ready!",
          ].join("\n");
          void sendConnectionAlert({
            token,
            alertChatId,
            message: recoveryMessage,
            accountId: account.accountId,
            logError,
          }).then((sent) => {
            if (sent) log("Sent recovery notification to Telegram.");
          });
        }

        if (restartAttempts > 0) {
          log(`Telegram connection was stable for ${formatDurationMs(runDuration)}; resetting retry counter.`);
        }
        restartAttempts = 0;
        lastSuccessfulStart = runnerStartTime;
        alertSentForCurrentOutage = false;
        outageStartTime = 0;
      }

      // Track outage start time
      if (restartAttempts === 0) {
        outageStartTime = Date.now();
      }

      restartAttempts += 1;
      const delayMs = computeBackoff(TELEGRAM_POLL_RESTART_POLICY, restartAttempts);
      const reason = isConflict ? "getUpdates conflict" : "network error";
      const errMsg = formatErrorMessage(err);
      logError(
        `Telegram ${reason} (attempt ${restartAttempts}): ${errMsg}; retrying in ${formatDurationMs(delayMs)}.`,
      );

      // Send alert after threshold failures (with cooldown)
      const shouldSendAlert =
        alertChatId &&
        restartAttempts >= ALERT_AFTER_FAILURES &&
        !alertSentForCurrentOutage &&
        Date.now() - lastAlertSentAt >= ALERT_COOLDOWN_MS;

      if (shouldSendAlert) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
        const alertMessage = [
          "⚠️ *OpenClaw Bot Alert*\n",
          `Connection issues detected at ${timeStr}.`,
          `Error: ${errMsg.slice(0, 100)}`,
          `Attempts: ${restartAttempts}\n`,
          "The bot is still trying to reconnect automatically.",
          "If issues persist, check your PC.",
        ].join("\n");

        void sendConnectionAlert({
          token,
          alertChatId,
          message: alertMessage,
          accountId: account.accountId,
          logError,
        }).then((sent) => {
          if (sent) {
            log("Sent connection alert to Telegram.");
            lastAlertSentAt = Date.now();
            alertSentForCurrentOutage = true;
          }
        });
      }

      try {
        await sleepWithAbort(delayMs, opts.abortSignal);
      } catch (sleepErr) {
        if (opts.abortSignal?.aborted) return;
        throw sleepErr;
      }
    } finally {
      opts.abortSignal?.removeEventListener("abort", stopOnAbort);
    }
  }
}
