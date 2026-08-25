// broken/toolserver.mjs — the incident, reconstructed. Five tools, three of
// them stubs that return success-shaped payloads without doing anything. The
// status report aggregates all five results into a green summary. Nothing in
// this file is wrong arithmetically; the report is internally consistent and
// three-fifths theater. Run: node broken/toolserver.mjs

import { createHash } from "node:crypto";

// --- two real tools ---------------------------------------------------------

function hashText({ text }) {
  const digest = createHash("sha256").update(text).digest("hex");
  return { success: true, tool: "hash_text", digest };
}

function countWords({ text }) {
  const words = text.split(/\s+/).filter(Boolean).length;
  return { success: true, tool: "count_words", words };
}

// --- three stubs standing in for unbuilt tools ------------------------------
// Each returns a plausible payload: an id, a status, a message. No worker is
// spawned, no task runs, nothing is stored.

function spawnWorker() {
  return { success: true, tool: "spawn_worker", workerId: "worker-1", status: "ready" };
}

function orchestrateTasks() {
  return { success: true, tool: "orchestrate_tasks", taskId: "task-1", status: "scheduled" };
}

function storeMemory() {
  return { success: true, tool: "store_memory", key: "session", status: "persisted" };
}

// --- the status report ------------------------------------------------------

const TOOLS = [hashText, countWords, spawnWorker, orchestrateTasks, storeMemory];

const results = TOOLS.map((tool) =>
  tool({ text: "the report is only as honest as its inputs" })
);

console.log("tool results:");
for (const r of results) {
  console.log(`  ${r.tool.padEnd(18)} ${r.success ? "success" : "FAILED"}`);
}

const succeeded = results.filter((r) => r.success).length;
const health = succeeded === results.length ? "operational" : "degraded";
console.log(`system health: ${health} (${succeeded}/${results.length} tools succeeded)`);
