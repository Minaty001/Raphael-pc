import ts from "./node_modules/typescript/lib/typescript.js";
import { readFileSync } from "fs";

const configPath = "./tsconfig.json";
const configFile = ts.readConfigFile(configPath, (p) => readFileSync(p, "utf8"));
const { options, fileNames } = ts.parseJsonConfigFileContent(
  configFile.config,
  ts.sys,
  "."
);

const program = ts.createProgram(fileNames, options);
const diagnostics = ts.getPreEmitDiagnostics(program);

let errorCount = 0;
for (const d of diagnostics) {
  const msg = ts.flattenDiagnosticMessageText(d.messageText, "\n");
  const loc = d.file && d.start != null ? d.file.getLineAndCharacterOfPosition(d.start) : null;
  const where = loc ? `${d.file.fileName}:${loc.line + 1}:${loc.character + 1}` : "(global)";
  const kind = d.category === ts.DiagnosticCategory.Error ? "ERROR" : d.category === ts.DiagnosticCategory.Warning ? "WARN" : "INFO";
  if (d.category === ts.DiagnosticCategory.Error) errorCount++;
  console.log(`${kind} ${where}: ${msg}`);
}
console.log(`\nType-check complete: ${errorCount} error(s).`);
process.exit(errorCount > 0 ? 1 : 0);
