// instrumented/toolserver.mjs — the same server, same tools, same report, with
// one change: every tool result is marked with its honest source at the moment
// it is produced. The stubs still return success-shaped payloads — quarantine
// does not mean deleting them — but the report derived from them can no longer
// forget what it was built from. Run: node instrumented/toolserver.mjs

import { createHash } from "node:crypto";
import { mark, derive, metaOf, auditMeta } from "../../../primitives/js/index.mjs";

// --- two real tools, results marked as real ---------------------------------

function hashText({ text }) {
  const digest = createHash("sha256").update(text).digest("hex");
  return mark(
    { success: true, tool: "hash_text", digest },
    { source: "real", confidence: "high" },
  );
}

function countWords({ text }) {
  const words = text.split(/\s+/).filter(Boolean).length;
  return mark(
    { success: true, tool: "count_words", words },
    { source: "real", confidence: "high" },
  );
}

// --- three stubs, results marked as what they are ---------------------------

function spawnWorker() {
  return mark(
    { success: true, tool: "spawn_worker", workerId: "worker-1", status: "ready" },
    { source: "mock", confidence: "none" },
  );
}

function orchestrateTasks() {
  return mark(
    { success: true, tool: "orchestrate_tasks", taskId: "task-1", status: "scheduled" },
    { source: "mock", confidence: "none" },
  );
}

function storeMemory() {
  return mark(
    { success: true, tool: "store_memory", key: "session", status: "persisted" },
    { source: "mock", confidence: "none" },
  );
}

// --- the status report, derived under the combination law -------------------

const TOOLS = [hashText, countWords, spawnWorker, orchestrateTasks, storeMemory];

const results = TOOLS.map((tool) =>
  tool({ text: "the report is only as honest as its inputs" })
);

const report = derive(
  results,
  (...payloads) => {
    const succeeded = payloads.filter((p) => p.success).length;
    return {
      succeeded,
      total: payloads.length,
      health: succeeded === payloads.length ? "operational" : "degraded",
    };
  },
  { basis: "toolserver.statusReport@v1" },
);

console.log("tool results:");
for (const r of results) {
  console.log(`  ${r.value.tool.padEnd(18)} ${r.value.success ? "success" : "FAILED"}  [source: ${r.source}]`);
}

const { health, succeeded, total } = report.value;
console.log(`system health: ${health} (${succeeded}/${total} tools succeeded)`);

// The report's envelope answers the question the incident's hand-audits fought
// over: how much of this is fake? Computed from lineage, not estimated.
const steps = report.lineage;
const mockSteps = steps.filter((s) => s.source === "mock").length;
console.log("");
console.log("report provenance:");
console.log(`  derivedFromMock: ${report.derivedFromMock}`);
console.log(`  confidence: ${report.confidence}`);
console.log(`  weakestSource: ${report.weakestSource}`);
console.log(`  mock inputs: ${mockSteps}/${steps.length} (computed from lineage, not estimated)`);

// And the escape hatch does not exist: claiming the report is real anyway is
// flagged by the runtime audit, because the taint cannot be overridden away.
const laundered = derive(results, () => report.value, { source: "real" });
console.log("");
console.log('attempted launder (derive with source: "real"):');
for (const issue of auditMeta(metaOf(laundered))) {
  console.log(`  ${issue}`);
}
