import fs from "node:fs";
import path from "node:path";
import { DEFAULT_LOG_DIR } from "./logger.js";

export type ChatLogEntry = {
    ts: string;
    sessionKey?: string;
    sessionId?: string;
    provider: string;
    model: string;
    input: string;
    output: string;
    usage?: {
        input?: number;
        output?: number;
        total?: number;
        cacheRead?: number;
        cacheWrite?: number;
    };
    durationMs?: number;
    costUsd?: number;
};

function getDailyChatLogPath(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    // Ensure directory exists
    fs.mkdirSync(DEFAULT_LOG_DIR, { recursive: true });
    return path.join(DEFAULT_LOG_DIR, `chat-exchanges-${year}-${month}-${day}.jsonl`);
}

export function logChatInteraction(entry: ChatLogEntry): void {
    try {
        const file = getDailyChatLogPath();
        const line = JSON.stringify(entry);
        fs.appendFileSync(file, line + "\n", "utf8");
    } catch (err) {
        // Fail silently to avoid interrupting the main flow
        /* eslint-disable-next-line no-console */
        console.error("Failed to write chat log:", err);
    }
}
