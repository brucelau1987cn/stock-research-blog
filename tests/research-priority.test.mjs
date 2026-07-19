import test from 'node:test';
import assert from 'node:assert/strict';

import { buildResearchPriority, sortByResearchPriority } from '../src/utils/research-priority.mjs';

const baseDecision = {
  status: '区间观察',
  action: '等待关键位确认',
  currentPrice: 10,
  changePct: 0.5,
  resistance: { label: '压力位', value: 12 },
  support: { label: '支撑位', value: 9 },
  invalidation: { label: '失效位', value: 8 },
};

const now = new Date('2026-07-20T00:00:00+08:00');

test('risk language is promoted to the highest action tier', () => {
  const result = buildResearchPriority(
    { ...baseDecision, status: '跌破生命线，清仓观望' },
    '2026-07-19T16:00:00+08:00',
    now,
  );

  assert.equal(result.rank, 5);
  assert.equal(result.key, 'risk');
  assert.equal(result.label, '风险处置');
  assert.match(result.reason, /跌破生命线/);
});

test('explicitly losing or closing below a defense line is treated as a risk fact', () => {
  for (const status of ['修复转弱，已失守 5.65', '防守线下弱势收盘']) {
    const result = buildResearchPriority({ ...baseDecision, status }, '2026-07-19T16:00:00+08:00', now);
    assert.equal(result.key, 'risk');
  }
});

test('a stock near a key level becomes an explainable trigger candidate', () => {
  const result = buildResearchPriority(
    { ...baseDecision, resistance: { label: '收复线', value: 10.2 } },
    '2026-07-19T16:00:00+08:00',
    now,
  );

  assert.equal(result.rank, 4);
  assert.equal(result.key, 'near');
  assert.equal(result.reason, '距收复线 2.0%');
});

test('an old snapshot is marked for review when no stronger evidence exists', () => {
  const result = buildResearchPriority(baseDecision, '2026-07-10T16:00:00+08:00', now);

  assert.equal(result.rank, 2);
  assert.equal(result.key, 'stale');
  assert.equal(result.label, '待复核');
  assert.match(result.reason, /9 天/);
});

test('Friday market data stays fresh through the weekend', () => {
  const result = buildResearchPriority(
    { ...baseDecision, sessionDate: '2026-07-17', dataAsOf: '2026-07-17T16:00:00-04:00' },
    '2026-07-19T20:00:00+08:00',
    new Date('2026-07-19T20:00:00+08:00'),
  );
  assert.equal(result.tradingAgeDays, 0);
  assert.equal(result.freshness, 'fresh');
});

test('market freshness uses data timestamp instead of article update timestamp', () => {
  const result = buildResearchPriority(
    { ...baseDecision, sessionDate: '2026-07-10', dataAsOf: '2026-07-10T15:00:00+08:00' },
    '2026-07-19T20:00:00+08:00',
    new Date('2026-07-19T20:00:00+08:00'),
  );
  assert.equal(result.tradingAgeDays, 5);
  assert.equal(result.freshness, 'stale');
  assert.match(result.reason, /5 个交易日/);
});

test('missing optional evidence does not reduce a routine item below baseline', () => {
  const result = buildResearchPriority(
    { status: '持续跟踪', action: '等待后续数据', currentPrice: 10 },
    '2026-07-19T16:00:00+08:00',
    now,
  );

  assert.equal(result.rank, 1);
  assert.equal(result.key, 'routine');
  assert.equal(result.nearestDistancePct, null);
});

test('priority sorting puts risk before near-trigger and routine research', () => {
  const makePost = (id, decision, updatedDate) => ({ id, data: { decision, updatedDate: new Date(updatedDate), pubDate: new Date(updatedDate) } });
  const posts = [
    makePost('routine', baseDecision, '2026-07-19T16:00:00+08:00'),
    makePost('near', { ...baseDecision, support: { label: '防守位', value: 9.8 } }, '2026-07-19T15:00:00+08:00'),
    makePost('risk', { ...baseDecision, status: '破位，降低仓位' }, '2026-07-18T15:00:00+08:00'),
  ];

  assert.deepEqual(sortByResearchPriority(posts, now).map((post) => post.id), ['risk', 'near', 'routine']);
});
