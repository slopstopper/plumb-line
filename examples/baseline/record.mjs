// Record the worked baseline. Run from the repo root:
//     node examples/baseline/record.mjs
// Re-run only with a new `because`; the history is the point.
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { mark, derive } from "../../primitives/js/marked.mjs";
import { check, update, reportText } from "../../primitives/js/baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const dir = join(here, "baselines");

const rate = mark(0.04, { source: "real", confidence: "high", confidenceScore: 0.9 });
const fx = mark(1.03, { source: "real", confidence: "high", confidenceScore: 0.9 });
const priced = derive([rate, fx], (a, b) => a * b, { basis: "pricing.applyFx@v3" });

const because = process.argv[2];
if (because) {
  update("fx-rate", priced, { because, dir });
}
console.log(reportText(check("fx-rate", priced, { dir })));
