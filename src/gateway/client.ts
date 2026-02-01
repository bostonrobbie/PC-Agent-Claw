import { randomUUID } from "node:crypto";
import { WebSocket, type ClientOptions, type CertMeta } from "ws";
import { normalizeFingerprint } from "../infra/tls/fingerprint.js";
import { rawDataToString } from "../infra/ws.js";
import { logDebug, logError, logWarn } from "../logger.js";
import type { DeviceIdentity } from "../infra/device-identity.js";
import {
  loadOrCreateDeviceIdentity,
  publicKeyRawBase64UrlFromPem,
  signDevicePayload,
} from "../infra/device-identity.js";
import {
  clearDeviceAuthToken,
  loadDeviceAuthToken,
  storeDeviceAuthToken,
} from "../infra/device-auth-store.js";
import {
  GATEWAY_CLIENT_MODES,
  GATEWAY_CLIENT_NAMES,
  type GatewayClientMode,
  type GatewayClientName,
} from "../utils/message-channel.js";
import { buildDeviceAuthPayload } from "./device-auth.js";
import {
  type ConnectParams,
  type EventFrame,
  type HelloOk,
  PROTOCOL_VERSION,
  type RequestFrame,
  validateEventFrame,
  validateRequestFrame,
  validateResponseFrame,
} from "./protocol/index.js";

// Circuit breaker states
export type CircuitState = "closed" | "open" | "half-open";

// Extended pending request with timeout tracking
type Pending = {
  resolve: (value: unknown) => void;
  reject: (err: unknown) => void;
  expectFinal: boolean;
  createdAt: number;
  timeoutTimer?: NodeJS.Timeout;
};

// Circuit breaker configuration
export type CircuitBreakerOptions = {
  failureThreshold?: number;     // Open after N consecutive failures (default: 5)
  resetTimeoutMs?: number;       // Wait before half-open attempt (default: 30000)
  successThreshold?: number;     // Successes needed to close from half-open (default: 2)
};

// Health metrics for monitoring
export type HealthMetrics = {
  circuitState: CircuitState;
  consecutiveFailures: number;
  consecutiveSuccesses: number;
  pendingRequests: number;
  staleRequests: number;
  lastSuccessAt: number | null;
  lastFailureAt: number | null;
  reconnectAttempts: number;
  isConnected: boolean;
};

export type GatewayClientOptions = {
  url?: string; // ws://127.0.0.1:18789
  token?: string;
  password?: string;
  instanceId?: string;
  clientName?: GatewayClientName;
  clientDisplayName?: string;
  clientVersion?: string;
  platform?: string;
  mode?: GatewayClientMode;
  role?: string;
  scopes?: string[];
  caps?: string[];
  commands?: string[];
  permissions?: Record<string, boolean>;
  pathEnv?: string;
  deviceIdentity?: DeviceIdentity;
  minProtocol?: number;
  maxProtocol?: number;
  tlsFingerprint?: string;
  // Existing callbacks
  onEvent?: (evt: EventFrame) => void;
  onHelloOk?: (hello: HelloOk) => void;
  onConnectError?: (err: Error) => void;
  onClose?: (code: number, reason: string) => void;
  onGap?: (info: { expected: number; received: number }) => void;
  // New auto-healing options
  requestTimeoutMs?: number;           // Per-request timeout (default: 30000)
  healthCheckIntervalMs?: number;      // Health check interval (default: 15000)
  maxReconnectAttempts?: number;       // Max reconnect attempts (0 = unlimited)
  circuitBreaker?: CircuitBreakerOptions;
  // New callbacks
  onCircuitOpen?: () => void;
  onCircuitClose?: () => void;
  onReconnecting?: (attempt: number, delayMs: number) => void;
  onHealthCheck?: (metrics: HealthMetrics) => void;
};

export const GATEWAY_CLOSE_CODE_HINTS: Readonly<Record<number, string>> = {
  1000: "normal closure",
  1006: "abnormal closure (no close frame)",
  1008: "policy violation",
  1012: "service restart",
};

export function describeGatewayCloseCode(code: number): string | undefined {
  return GATEWAY_CLOSE_CODE_HINTS[code];
}

export class GatewayClient {
  private ws: WebSocket | null = null;
  private opts: GatewayClientOptions;
  private pending = new Map<string, Pending>();
  private backoffMs = 1000;
  private closed = false;
  private lastSeq: number | null = null;
  private connectNonce: string | null = null;
  private connectSent = false;
  private connectTimer: NodeJS.Timeout | null = null;
  // Track last tick to detect silent stalls.
  private lastTick: number | null = null;
  private tickIntervalMs = 30_000;
  private tickTimer: NodeJS.Timeout | null = null;

  // Circuit breaker state
  private circuitState: CircuitState = "closed";
  private consecutiveFailures = 0;
  private consecutiveSuccesses = 0;
  private circuitResetTimer: NodeJS.Timeout | null = null;

  // Health monitoring
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private lastSuccessAt: number | null = null;
  private lastFailureAt: number | null = null;
  private reconnectAttempts = 0;

  // Configuration with defaults
  private readonly requestTimeoutMs: number;
  private readonly healthCheckIntervalMs: number;
  private readonly maxReconnectAttempts: number;
  private readonly failureThreshold: number;
  private readonly resetTimeoutMs: number;
  private readonly successThreshold: number;

  constructor(opts: GatewayClientOptions) {
    this.opts = {
      ...opts,
      deviceIdentity: opts.deviceIdentity ?? loadOrCreateDeviceIdentity(),
    };
    // Set defaults for auto-healing options
    this.requestTimeoutMs = opts.requestTimeoutMs ?? 30_000;
    this.healthCheckIntervalMs = opts.healthCheckIntervalMs ?? 15_000;
    this.maxReconnectAttempts = opts.maxReconnectAttempts ?? 0; // 0 = unlimited
    this.failureThreshold = opts.circuitBreaker?.failureThreshold ?? 5;
    this.resetTimeoutMs = opts.circuitBreaker?.resetTimeoutMs ?? 30_000;
    this.successThreshold = opts.circuitBreaker?.successThreshold ?? 2;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Public API
  // ─────────────────────────────────────────────────────────────────────────────

  /** Check if WebSocket is connected and ready */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /** Get current circuit breaker state */
  getCircuitState(): CircuitState {
    return this.circuitState;
  }

  /** Get health metrics for monitoring */
  getHealthMetrics(): HealthMetrics {
    const staleThreshold = this.requestTimeoutMs * 2;
    const now = Date.now();
    let staleRequests = 0;
    for (const [, p] of this.pending) {
      if (now - p.createdAt > staleThreshold) {
        staleRequests++;
      }
    }
    return {
      circuitState: this.circuitState,
      consecutiveFailures: this.consecutiveFailures,
      consecutiveSuccesses: this.consecutiveSuccesses,
      pendingRequests: this.pending.size,
      staleRequests,
      lastSuccessAt: this.lastSuccessAt,
      lastFailureAt: this.lastFailureAt,
      reconnectAttempts: this.reconnectAttempts,
      isConnected: this.isConnected(),
    };
  }

  /** Force reset the circuit breaker to closed state */
  resetCircuit(): void {
    const wasOpen = this.circuitState !== "closed";
    this.circuitState = "closed";
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    if (this.circuitResetTimer) {
      clearTimeout(this.circuitResetTimer);
      this.circuitResetTimer = null;
    }
    if (wasOpen) {
      this.opts.onCircuitClose?.();
    }
  }

  /** Manual reconnection trigger */
  reconnect(): void {
    if (this.closed) return;
    this.cleanupTimers();
    if (this.ws) {
      this.ws.close(1000, "manual reconnect");
      this.ws = null;
    }
    this.flushPendingErrors(new Error("manual reconnect"));
    this.reconnectAttempts = 0;
    this.backoffMs = 1000;
    this.start();
  }

  start() {
    if (this.closed) return;

    // Check circuit breaker before attempting connection
    if (this.circuitState === "open") {
      logWarn("gateway client circuit open - connection blocked");
      return;
    }

    const url = this.opts.url ?? "ws://127.0.0.1:18789";
    if (this.opts.tlsFingerprint && !url.startsWith("wss://")) {
      this.opts.onConnectError?.(new Error("gateway tls fingerprint requires wss:// gateway url"));
      return;
    }
    // Allow node screen snapshots and other large responses.
    const wsOptions: ClientOptions = {
      maxPayload: 25 * 1024 * 1024,
    };
    if (url.startsWith("wss://") && this.opts.tlsFingerprint) {
      wsOptions.rejectUnauthorized = false;
      wsOptions.checkServerIdentity = ((_host: string, cert: CertMeta) => {
        const fingerprintValue =
          typeof cert === "object" && cert && "fingerprint256" in cert
            ? ((cert as { fingerprint256?: string }).fingerprint256 ?? "")
            : "";
        const fingerprint = normalizeFingerprint(
          typeof fingerprintValue === "string" ? fingerprintValue : "",
        );
        const expected = normalizeFingerprint(this.opts.tlsFingerprint ?? "");
        if (!expected) {
          return new Error("gateway tls fingerprint missing");
        }
        if (!fingerprint) {
          return new Error("gateway tls fingerprint unavailable");
        }
        if (fingerprint !== expected) {
          return new Error("gateway tls fingerprint mismatch");
        }
        return undefined;
      }) as any;
    }
    this.ws = new WebSocket(url, wsOptions);

    this.ws.on("open", () => {
      if (url.startsWith("wss://") && this.opts.tlsFingerprint) {
        const tlsError = this.validateTlsFingerprint();
        if (tlsError) {
          this.opts.onConnectError?.(tlsError);
          this.ws?.close(1008, tlsError.message);
          return;
        }
      }
      // Reset reconnect attempts on successful open
      this.reconnectAttempts = 0;
      this.queueConnect();
      // Start health check monitoring
      this.startHealthCheck();
    });
    this.ws.on("message", (data) => this.handleMessage(rawDataToString(data)));
    this.ws.on("close", (code, reason) => {
      const reasonText = rawDataToString(reason);
      this.ws = null;
      this.flushPendingErrors(new Error(`gateway closed (${code}): ${reasonText}`));
      this.stopHealthCheck();
      this.scheduleReconnect();
      this.opts.onClose?.(code, reasonText);
    });
    this.ws.on("error", (err) => {
      logDebug(`gateway client error: ${String(err)}`);
      this.recordFailure();
      if (!this.connectSent) {
        this.opts.onConnectError?.(err instanceof Error ? err : new Error(String(err)));
      }
    });
  }

  stop() {
    this.closed = true;
    this.cleanupTimers();
    this.ws?.close();
    this.ws = null;
    this.flushPendingErrors(new Error("gateway client stopped"));
  }

  private cleanupTimers() {
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
    if (this.circuitResetTimer) {
      clearTimeout(this.circuitResetTimer);
      this.circuitResetTimer = null;
    }
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }
  }

  private sendConnect() {
    if (this.connectSent) return;
    this.connectSent = true;
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }
    const role = this.opts.role ?? "operator";
    const storedToken = this.opts.deviceIdentity
      ? loadDeviceAuthToken({ deviceId: this.opts.deviceIdentity.deviceId, role })?.token
      : null;
    const authToken = storedToken ?? this.opts.token ?? undefined;
    const canFallbackToShared = Boolean(storedToken && this.opts.token);
    const auth =
      authToken || this.opts.password
        ? {
          token: authToken,
          password: this.opts.password,
        }
        : undefined;
    const signedAtMs = Date.now();
    const nonce = this.connectNonce ?? undefined;
    const scopes = this.opts.scopes ?? ["operator.admin"];
    const device = (() => {
      if (!this.opts.deviceIdentity) return undefined;
      const payload = buildDeviceAuthPayload({
        deviceId: this.opts.deviceIdentity.deviceId,
        clientId: this.opts.clientName ?? GATEWAY_CLIENT_NAMES.GATEWAY_CLIENT,
        clientMode: this.opts.mode ?? GATEWAY_CLIENT_MODES.BACKEND,
        role,
        scopes,
        signedAtMs,
        token: authToken ?? null,
        nonce,
      });
      const signature = signDevicePayload(this.opts.deviceIdentity.privateKeyPem, payload);
      return {
        id: this.opts.deviceIdentity.deviceId,
        publicKey: publicKeyRawBase64UrlFromPem(this.opts.deviceIdentity.publicKeyPem),
        signature,
        signedAt: signedAtMs,
        nonce,
      };
    })();
    const params: ConnectParams = {
      minProtocol: this.opts.minProtocol ?? PROTOCOL_VERSION,
      maxProtocol: this.opts.maxProtocol ?? PROTOCOL_VERSION,
      client: {
        id: this.opts.clientName ?? GATEWAY_CLIENT_NAMES.GATEWAY_CLIENT,
        displayName: this.opts.clientDisplayName,
        version: this.opts.clientVersion ?? "dev",
        platform: this.opts.platform ?? process.platform,
        mode: this.opts.mode ?? GATEWAY_CLIENT_MODES.BACKEND,
        instanceId: this.opts.instanceId,
      },
      caps: Array.isArray(this.opts.caps) ? this.opts.caps : [],
      commands: Array.isArray(this.opts.commands) ? this.opts.commands : undefined,
      permissions:
        this.opts.permissions && typeof this.opts.permissions === "object"
          ? this.opts.permissions
          : undefined,
      pathEnv: this.opts.pathEnv,
      auth,
      role,
      scopes,
      device,
    };

    void this.request<HelloOk>("connect", params)
      .then((helloOk) => {
        const authInfo = helloOk?.auth;
        if (authInfo?.deviceToken && this.opts.deviceIdentity) {
          storeDeviceAuthToken({
            deviceId: this.opts.deviceIdentity.deviceId,
            role: authInfo.role ?? role,
            token: authInfo.deviceToken,
            scopes: authInfo.scopes ?? [],
          });
        }
        this.backoffMs = 1000;
        this.tickIntervalMs =
          typeof helloOk.policy?.tickIntervalMs === "number"
            ? helloOk.policy.tickIntervalMs
            : 30_000;
        this.lastTick = Date.now();
        this.startTickWatch();
        this.recordSuccess();
        this.opts.onHelloOk?.(helloOk);
      })
      .catch((err) => {
        if (canFallbackToShared && this.opts.deviceIdentity) {
          clearDeviceAuthToken({
            deviceId: this.opts.deviceIdentity.deviceId,
            role,
          });
        }
        this.recordFailure();
        this.opts.onConnectError?.(err instanceof Error ? err : new Error(String(err)));
        const msg = `gateway connect failed: ${String(err)}`;
        if (this.opts.mode === GATEWAY_CLIENT_MODES.PROBE) logDebug(msg);
        else logError(msg);
        this.ws?.close(1008, "connect failed");
      });
  }

  private handleMessage(raw: string) {
    try {
      const parsed = JSON.parse(raw);
      if (validateEventFrame(parsed)) {
        const evt = parsed as EventFrame;
        if (evt.event === "connect.challenge") {
          const payload = evt.payload as { nonce?: unknown } | undefined;
          const nonce = payload && typeof payload.nonce === "string" ? payload.nonce : null;
          if (nonce) {
            this.connectNonce = nonce;
            this.sendConnect();
          }
          return;
        }
        const seq = typeof evt.seq === "number" ? evt.seq : null;
        if (seq !== null) {
          if (this.lastSeq !== null && seq > this.lastSeq + 1) {
            this.opts.onGap?.({ expected: this.lastSeq + 1, received: seq });
          }
          this.lastSeq = seq;
        }
        if (evt.event === "tick") {
          this.lastTick = Date.now();
        }
        this.opts.onEvent?.(evt);
        return;
      }
      if (validateResponseFrame(parsed)) {
        const pending = this.pending.get(parsed.id);
        if (!pending) return;
        // If the payload is an ack with status accepted, keep waiting for final.
        const payload = parsed.payload as { status?: unknown } | undefined;
        const status = payload?.status;
        if (pending.expectFinal && status === "accepted") {
          return;
        }
        // Clear timeout timer
        if (pending.timeoutTimer) {
          clearTimeout(pending.timeoutTimer);
        }
        this.pending.delete(parsed.id);
        if (parsed.ok) {
          this.recordSuccess();
          pending.resolve(parsed.payload);
        } else {
          this.recordFailure();
          pending.reject(new Error(parsed.error?.message ?? "unknown error"));
        }
      }
    } catch (err) {
      logDebug(`gateway client parse error: ${String(err)}`);
    }
  }

  private queueConnect() {
    this.connectNonce = null;
    this.connectSent = false;
    if (this.connectTimer) clearTimeout(this.connectTimer);
    this.connectTimer = setTimeout(() => {
      this.sendConnect();
    }, 750);
  }

  private scheduleReconnect() {
    if (this.closed) return;
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }

    // Check max reconnect attempts
    if (this.maxReconnectAttempts > 0 && this.reconnectAttempts >= this.maxReconnectAttempts) {
      logError(`gateway client max reconnect attempts (${this.maxReconnectAttempts}) reached`);
      return;
    }

    this.reconnectAttempts++;

    // Calculate delay with jitter (1.8× factor, 25% jitter)
    const jitterFactor = 0.75 + Math.random() * 0.5; // 0.75 to 1.25
    const delay = Math.min(this.backoffMs * jitterFactor, 30_000);
    this.backoffMs = Math.min(this.backoffMs * 1.8, 30_000);

    this.opts.onReconnecting?.(this.reconnectAttempts, Math.round(delay));
    logDebug(`gateway client reconnecting (attempt ${this.reconnectAttempts}) in ${Math.round(delay)}ms`);

    setTimeout(() => this.start(), delay).unref();
  }

  private flushPendingErrors(err: Error) {
    for (const [, p] of this.pending) {
      if (p.timeoutTimer) {
        clearTimeout(p.timeoutTimer);
      }
      p.reject(err);
    }
    this.pending.clear();
  }

  private startTickWatch() {
    if (this.tickTimer) clearInterval(this.tickTimer);
    const interval = Math.max(this.tickIntervalMs, 1000);
    this.tickTimer = setInterval(() => {
      if (this.closed) return;
      if (!this.lastTick) return;
      const gap = Date.now() - this.lastTick;
      if (gap > this.tickIntervalMs * 2) {
        this.ws?.close(4000, "tick timeout");
      }
    }, interval);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Circuit Breaker
  // ─────────────────────────────────────────────────────────────────────────────

  private recordSuccess() {
    this.lastSuccessAt = Date.now();
    this.consecutiveFailures = 0;

    if (this.circuitState === "half-open") {
      this.consecutiveSuccesses++;
      if (this.consecutiveSuccesses >= this.successThreshold) {
        this.circuitState = "closed";
        this.consecutiveSuccesses = 0;
        logDebug("gateway client circuit closed (recovered)");
        this.opts.onCircuitClose?.();
      }
    }
  }

  private recordFailure() {
    this.lastFailureAt = Date.now();
    this.consecutiveSuccesses = 0;
    this.consecutiveFailures++;

    if (this.circuitState === "closed" && this.consecutiveFailures >= this.failureThreshold) {
      this.openCircuit();
    } else if (this.circuitState === "half-open") {
      // Failed during half-open, reopen
      this.openCircuit();
    }
  }

  private openCircuit() {
    if (this.circuitState === "open") return;

    this.circuitState = "open";
    logWarn(`gateway client circuit opened after ${this.consecutiveFailures} failures`);
    this.opts.onCircuitOpen?.();

    // Schedule transition to half-open
    if (this.circuitResetTimer) {
      clearTimeout(this.circuitResetTimer);
    }
    this.circuitResetTimer = setTimeout(() => {
      if (this.circuitState === "open") {
        this.circuitState = "half-open";
        this.consecutiveSuccesses = 0;
        logDebug("gateway client circuit half-open (attempting recovery)");
        // Attempt reconnection
        if (!this.isConnected()) {
          this.start();
        }
      }
    }, this.resetTimeoutMs);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Health Monitoring
  // ─────────────────────────────────────────────────────────────────────────────

  private startHealthCheck() {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
    }
    this.healthCheckTimer = setInterval(() => {
      this.runHealthCheck();
    }, this.healthCheckIntervalMs);
  }

  private stopHealthCheck() {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }

  private runHealthCheck() {
    const metrics = this.getHealthMetrics();
    this.opts.onHealthCheck?.(metrics);

    // Check for stale requests (older than 2× timeout)
    if (metrics.staleRequests > 0) {
      logWarn(`gateway client detected ${metrics.staleRequests} stale request(s)`);

      // If too many stale requests, force reconnection
      if (metrics.staleRequests >= 3) {
        logWarn("gateway client forcing reconnection due to stale requests");
        this.recordFailure();
        this.ws?.close(4001, "stale requests detected");
      }
    }
  }

  private validateTlsFingerprint(): Error | null {
    if (!this.opts.tlsFingerprint || !this.ws) return null;
    const expected = normalizeFingerprint(this.opts.tlsFingerprint);
    if (!expected) return new Error("gateway tls fingerprint missing");
    const socket = (
      this.ws as WebSocket & {
        _socket?: { getPeerCertificate?: () => { fingerprint256?: string } };
      }
    )._socket;
    if (!socket || typeof socket.getPeerCertificate !== "function") {
      return new Error("gateway tls fingerprint unavailable");
    }
    const cert = socket.getPeerCertificate();
    const fingerprint = normalizeFingerprint(cert?.fingerprint256 ?? "");
    if (!fingerprint) return new Error("gateway tls fingerprint unavailable");
    if (fingerprint !== expected) return new Error("gateway tls fingerprint mismatch");
    return null;
  }

  async request<T = unknown>(
    method: string,
    params?: unknown,
    opts?: { expectFinal?: boolean },
  ): Promise<T> {
    // Check circuit breaker
    if (this.circuitState === "open") {
      const err = new Error("gateway circuit breaker open");
      this.opts.onConnectError?.(err);
      throw err;
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("gateway not connected");
    }
    const id = randomUUID();
    const frame: RequestFrame = { type: "req", id, method, params };
    if (!validateRequestFrame(frame)) {
      throw new Error(
        `invalid request frame: ${JSON.stringify(validateRequestFrame.errors, null, 2)}`,
      );
    }
    const expectFinal = opts?.expectFinal === true;
    const createdAt = Date.now();

    const p = new Promise<T>((resolve, reject) => {
      // Set up timeout timer
      const timeoutTimer = setTimeout(() => {
        const pending = this.pending.get(id);
        if (pending) {
          this.pending.delete(id);
          this.recordFailure();
          reject(new Error(`request timeout after ${this.requestTimeoutMs}ms`));
        }
      }, this.requestTimeoutMs);

      this.pending.set(id, {
        resolve: (value) => resolve(value as T),
        reject,
        expectFinal,
        createdAt,
        timeoutTimer,
      });
    });
    this.ws.send(JSON.stringify(frame));
    return p;
  }
}
