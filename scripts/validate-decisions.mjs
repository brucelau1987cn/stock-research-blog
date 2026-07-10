import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import YAML from 'yaml';

import { validateDecision } from './lib/decision-validation.mjs';

const contentDir = path.resolve('src/content/blog');
const files = (await readdir(contentDir)).filter((file) => /\.mdx?$/.test(file));
const failures = [];
let checked = 0;

for (const file of files) {
  const source = await readFile(path.join(contentDir, file), 'utf8');
  const match = source.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!match) continue;

  let data;
  try {
    data = YAML.parse(match[1]);
  } catch (error) {
    failures.push(`${file}: frontmatter YAML 解析失败: ${error.message}`);
    continue;
  }

  if (!data?.decision) continue;
  checked += 1;
  failures.push(...validateDecision(data.decision, file));
}

if (failures.length) {
  console.error('Decision validation failed:\n');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Decision validation passed for ${checked} structured stock article(s).`);
