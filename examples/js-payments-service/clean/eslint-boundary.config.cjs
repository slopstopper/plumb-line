const importX = require("eslint-plugin-import-x");
const boundary = require("./eslint-boundary.cjs");
module.exports = [{
  files: ["**/*.js"],
  plugins: { import: importX },
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
  ...boundary,
}];
