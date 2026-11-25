// Test-only instrumentation: count synchronous file reads made by the HUD server.
const fs = require("node:fs");

const readFileSync = fs.readFileSync;
const statSync = fs.statSync;

fs.readFileSync = function (...args) {
  process.stdout.write(`READ ${String(args[0])}\n`);
  return readFileSync.apply(this, args);
};

fs.statSync = function (...args) {
  const result = statSync.apply(this, args);
  process.stdout.write(`STAT ${String(args[0])}\n`);
  return result;
};
