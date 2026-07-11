import test from 'node:test';
import assert from 'node:assert/strict';

import { compactSummary, inferSentiment } from '../src/utils/article-summary.mjs';

test('compactSummary removes markdown and limits a long market note', () => {
  const summary = compactSummary('最新结论：**通威股份** 收于 11.36 元；主力净流入，但仍低于关键位，等待确认。后续长篇说明不应出现在列表卡片。', 32);

  assert.equal(summary, '通威股份 收于 11.36 元；主力净流入，但仍低于关键位，等…');
});

test('compactSummary keeps a concise conclusion unchanged', () => {
  assert.equal(compactSummary('等待放量站稳关键位后再观察。', 40), '等待放量站稳关键位后再观察。');
});

test('inferSentiment prioritizes a structured status over conflicting legacy text', () => {
  assert.equal(inferSentiment({ status: '偏空，破位确认' }, '短线看多，等待修复'), '偏空');
});

test('inferSentiment identifies defensive legacy conclusions', () => {
  assert.equal(inferSentiment(undefined, '最新结论：仍低于防守线，维持清仓观望。'), '观望/防守');
});
