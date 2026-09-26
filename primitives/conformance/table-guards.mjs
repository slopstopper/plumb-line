// table-guards.mjs — the three case-table guards for the conformance tables
// read by the ordinary test runners (#441): http-cases.json and
// baseline-cases.json. They are the checks run-cases.mjs applies to cases.json
// (#369, #433): a field, a case kind or a table version the runner does not
// interpret is reported, never ignored. Python twin:
// primitives/python/tests/case_table_guards.py.

/**
 * What a runner interprets in its case table.
 * @typedef {object} TableModel
 * @property {number[]} versions  table versions the runner models
 * @property {string[]} meta      top-level keys that are metadata, not case kinds
 * @property {Record<string, string[]>} fields  per case kind, every field the runner reads
 */

/**
 * @param {object} table  the parsed case table
 * @param {TableModel} model
 * @returns {string[]} one message per problem; [] when the runner interprets everything
 */
export function tableProblems(table, { versions, meta, fields }) {
  const problems = [];
  if (!versions.includes(table.version)) {
    problems.push(`unknown case-table version ${JSON.stringify(table.version)}: this runner models ${versions.join(", ")}`);
  }
  for (const kind of Object.keys(table)) {
    if (meta.includes(kind)) continue;
    if (!Object.hasOwn(fields, kind)) {
      problems.push(`unknown case kind ${kind}: teach this runner to interpret it`);
      continue;
    }
    for (const c of table[kind]) {
      const extra = Object.keys(c).filter((k) => !fields[kind].includes(k));
      if (extra.length) {
        problems.push(`${kind} case ${JSON.stringify(c.name)}: unknown field(s) ${extra.join(", ")}: teach this runner to interpret them`);
      }
    }
  }
  return problems;
}
