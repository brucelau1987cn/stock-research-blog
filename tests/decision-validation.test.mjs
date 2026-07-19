import test from 'node:test';
import assert from 'node:assert/strict';

import { validateDecision } from '../scripts/lib/decision-validation.mjs';

const base = {
  ticker: 'TEST',
  name: '测试公司',
  status: '偏多',
  currentPrice: 10,
  currency: '元',
  market: 'CN',
  sessionDate: '2026-07-17',
  dataAsOf: '2026-07-17T15:00:00+08:00',
  resistance: { label: '第一压力', value: 12, state: '未突破' },
  support: { label: '第一支撑', value: 9, state: '已站稳' },
  invalidation: { label: '失效位', value: 8, action: '退出' },
  action: '等待触发',
};

test('accepts a coherent decision summary', () => {
  assert.deepEqual(validateDecision(base, 'test.md'), []);
});

test('rejects an unbroken resistance below the current price', () => {
  const decision = {
    ...base,
    resistance: { label: '恢复位', value: 7.5, state: '暂未收复' },
  };
  assert.match(validateDecision(decision, 'test.md').join('\n'), /现价.*高于.*暂未收复/);
});

test('rejects a support marked recovered above the current price', () => {
  const decision = {
    ...base,
    support: { label: '防守线', value: 10.5, state: '已站稳' },
  };
  assert.match(validateDecision(decision, 'test.md').join('\n'), /现价.*低于.*已站稳/);
});

test('rejects a support marked temporarily recovered above the current price', () => {
  const decision = {
    ...base,
    support: { label: '防守线', value: 10.5, state: '暂时收复' },
  };
  assert.match(validateDecision(decision, 'test.md').join('\n'), /现价.*低于.*暂时收复/);
});

test('rejects a change percentage inconsistent with current and previous close', () => {
  const decision = { ...base, previousClose: 9, changePct: 0 };
  assert.match(validateDecision(decision, 'test.md').join('\n'), /涨跌幅.*计算值/);
});

test('rejects missing or inconsistent market timestamps', () => {
  const missing = { ...base, market: undefined, sessionDate: undefined, dataAsOf: undefined };
  const missingErrors = validateDecision(missing, 'test.md').join('\n');
  assert.match(missingErrors, /market/);
  assert.match(missingErrors, /sessionDate/);
  assert.match(missingErrors, /dataAsOf/);

  const mismatched = { ...base, dataAsOf: '2026-07-18T15:00:00+08:00' };
  assert.match(validateDecision(mismatched, 'test.md').join('\n'), /日期必须与 sessionDate 一致/);
});
