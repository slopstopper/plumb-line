// fit-map-snippets.test.mjs — executes the ```js snippets in
// reference/fit-map.md against this package, so the canonical examples cannot
// rot as the API moves (GH #265; the JS half of the guard GH #262 built for
// Python — that suite marked ```js "knowingly unguarded" and points here).
//
// Mechanism: each snippet is composed into a real ESM module (prelude
// supplying the free names a doc snippet elides + the snippet verbatim + an
// export of the names the postcondition inspects), written to a temp dir
// inside the package, and dynamically imported. Inside the package dir the
// snippet's `import ... from "plumb-line-provenance"` resolves by Node
// self-reference through package.json "exports" — the snippets run exactly
// as written for a consumer. Unlike the Python twin (a repo-infrastructure
// suite outside any package, per the test_bundle_conformance precedent),
// this file lives INSIDE the published package: self-reference resolution
// requires it, a recorded deviation rather than an accident.
import { describe, it, expect, afterAll } from "vitest";
import { readFileSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { metaOf } from "plumb-line-provenance";

const here = dirname(fileURLToPath(import.meta.url));
const FIT_MAP = join(here, "..", "..", "reference", "fit-map.md");
const TMP = join(here, `.fitmap-snippets-tmp-${process.pid}`);

// The Python twin asserts the loaded copy is the repo's, never assumes it;
// same discipline here (#307 review): a published plumb-line-provenance
// landing in node_modules would silently shadow self-reference and this
// suite would verify a stale release while staying green.
const resolved = await import.meta.resolve("plumb-line-provenance");
if (resolved !== pathToFileURL(join(here, "index.mjs")).href) {
  throw new Error(
    `plumb-line-provenance resolved outside this package: ${resolved}`,
  );
}

const text = readFileSync(FIT_MAP, "utf8");
const ALL_BLOCKS = [...text.matchAll(/```([^\n]*)\n([\s\S]*?)```/g)].map(
  (m) => [m[1].trim(), m[2]],
);
const JS_BLOCKS = ALL_BLOCKS.filter(([tag]) => tag === "js").map(([, b]) => b);

// marker (unique structural substring) -> { prelude, exports, check }.
// The prelude text is prepended (ESM hoists the snippet's imports above it),
// the exports line is appended, and check() receives the exported namespace.
const SNIPPETS = {
  FALLBACK_TEXT: {
    prelude: (ok) => `
      const ok = ${ok};
      const completion = "real completion";
      const FALLBACK_TEXT = "canned";
      const template = { format: (r) => \`[\${r}]\` };
    `,
    exports: "export const __ns = { rendered };",
    // Fallback path: taint carried, as the snippet's comment claims.
    check: (ns) => expect(metaOf(ns.rendered).derivedFromMock).toBe(true),
    // Real path exercised separately below, so a defect in the branch the
    // parametrized run skips cannot hide behind lazy evaluation (the
    // pre-#261 defect class).
    checkReal: (ns) => expect(metaOf(ns.rendered).derivedFromMock).toBe(false),
  },
  taggedFetch: {
    // Offline: the snippet awaits taggedFetch(url) at module top level, so
    // the stub must exist before the import body runs — prelude text
    // executes first, and only the import statements hoist above it.
    prelude: () => `
      globalThis.fetch = async () =>
        new Response('{"a": 1}', { status: 200 });
      const url = "https://example.test";
    `,
    exports: "export const __ns = { value, meta };",
    check: (ns) => {
      expect(ns.meta.source).toBe("real");
      expect(ns.meta.confidence).toBe("high");
    },
  },
};

let counter = 0;
async function runSnippet(block, prelude, exportsLine) {
  mkdirSync(TMP, { recursive: true });
  const path = join(TMP, `snippet-${counter++}.mjs`);
  writeFileSync(path, `${prelude}\n${block}\n${exportsLine}\n`);
  const mod = await import(pathToFileURL(path).href);
  return mod.__ns;
}

afterAll(() => rmSync(TMP, { recursive: true, force: true }));

describe("fit-map js snippets", () => {
  it("extraction found the snippets (zero-found must not read as verified)", () => {
    // The #249 lesson, same as the Python twin: every marker matches exactly
    // one block, and no js block escapes without a matching entry here.
    expect(JS_BLOCKS.length).toBeGreaterThanOrEqual(Object.keys(SNIPPETS).length);
    for (const marker of Object.keys(SNIPPETS)) {
      const hits = JS_BLOCKS.filter((b) => b.includes(marker));
      expect(hits, `marker ${marker} must match exactly one snippet`).toHaveLength(1);
    }
    for (const block of JS_BLOCKS) {
      expect(
        Object.keys(SNIPPETS).some((m) => block.includes(m)),
        `js snippet without a matching entry here:\n${block}`,
      ).toBe(true);
    }
  });

  for (const [marker, spec] of Object.entries(SNIPPETS)) {
    it(`snippet [${marker}] executes and behaves as its prose claims`, async () => {
      const block = JS_BLOCKS.find((b) => b.includes(marker));
      expect(block, `marker ${marker} matches no snippet`).toBeDefined();
      const ns = await runSnippet(block, spec.prelude(false), spec.exports);
      spec.check(ns);
    });
  }

  it("profile-1 real branch (the path the fallback run skips)", async () => {
    const spec = SNIPPETS.FALLBACK_TEXT;
    const block = JS_BLOCKS.find((b) => b.includes("FALLBACK_TEXT"));
    const ns = await runSnippet(block, spec.prelude(true), spec.exports);
    spec.checkReal(ns);
  });

  it("harness catches a broken snippet (self-test through the same pipeline)", async () => {
    // The pre-#261 defect class: a snippet calling something that is not
    // there must fail loudly out of the exact composition path the real
    // snippets use. Honest limit, discovered writing this: vitest's module
    // transform turns a MISSING NAMED IMPORT into `undefined` rather than
    // the ESM link-time error plain Node throws, so import-name drift
    // surfaces here only at the call site (TypeError), not at link time.
    const broken =
      'import { metaOf } from "plumb-line-provenance";\n' +
      "const rendered = metaOf.unwrapp();\n";
    await expect(
      runSnippet(broken, "", "export const __ns = { rendered };"),
    ).rejects.toThrow(TypeError);
  });
});
