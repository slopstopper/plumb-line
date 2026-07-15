import { describe, it, expect } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

describe("provenance-lint plugin entry point", () => {
  it("registers the no-provenance-bypass rule under the plumb-line plugin", () => {
    const plugin = require("../index.cjs");
    expect(plugin.meta?.name).toBe("eslint-plugin-plumb-line-provenance");
    expect(plugin.rules?.["no-provenance-bypass"]).toBeDefined();
    // the registered rule is the actual rule module, with a create() function.
    const rule = require("../no-provenance-bypass.cjs");
    expect(plugin.rules["no-provenance-bypass"]).toBe(rule);
    expect(typeof rule.create).toBe("function");
  });

  it("exposes both provenance-lint rules", () => {
    const plugin = require("../index.cjs");
    expect(Object.keys(plugin.rules).sort()).toEqual(
      ["no-provenance-bypass", "require-provenance-output"]
    );
  });
});
