const RISK_PATTERN = /偏空|清仓|退出|失效|破位|跌破|失守|防守线下|止损|降低仓位|减仓/;
const LEVEL_RISK_PATTERN = /已跌破|持续失守|收盘失守|已经失守|已失守/;

const toDate = (value) => {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.valueOf()) ? null : date;
};

const distancePct = (current, level) => {
  const price = Number(current);
  const target = Number(level);
  if (!Number.isFinite(price) || price <= 0 || !Number.isFinite(target) || target <= 0) return null;
  return ((target - price) / price) * 100;
};

const MARKET_TIME_ZONES = {
  CN: 'Asia/Shanghai',
  HK: 'Asia/Hong_Kong',
  US: 'America/New_York',
};

const MARKET_CLOSE_MINUTES = {
  CN: 15 * 60,
  HK: 16 * 60,
  US: 16 * 60,
};

const marketDateParts = (date, market) => {
  const timeZone = MARKET_TIME_ZONES[market] ?? 'UTC';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date);
  const get = (type) => Number(parts.find((part) => part.type === type)?.value);
  return {
    year: get('year'),
    month: get('month'),
    day: get('day'),
    minutes: get('hour') * 60 + get('minute'),
  };
};

const tradingDaysSince = (sessionDate, now, market) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate ?? ''))) return null;
  const [year, month, day] = sessionDate.split('-').map(Number);
  const start = new Date(Date.UTC(year, month - 1, day));
  const current = toDate(now);
  if (!current) return null;
  const marketNow = marketDateParts(current, market);
  let end = new Date(Date.UTC(marketNow.year, marketNow.month - 1, marketNow.day));
  if (marketNow.minutes < (MARKET_CLOSE_MINUTES[market] ?? 24 * 60)) {
    end = new Date(end.valueOf() - 86_400_000);
  }
  if (end <= start) return 0;
  let count = 0;
  for (const cursor = new Date(start.valueOf() + 86_400_000); cursor <= end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    const weekday = cursor.getUTCDay();
    if (weekday !== 0 && weekday !== 6) count += 1;
  }
  return count;
};

const levelEvidence = (decision) => {
  const levels = [
    { kind: 'resistance', label: decision?.resistance?.label ?? '压力位', value: decision?.resistance?.value },
    { kind: 'support', label: decision?.support?.label ?? '支撑位', value: decision?.support?.value },
    { kind: 'invalidation', label: decision?.invalidation?.label ?? '失效位', value: decision?.invalidation?.value },
  ];
  return levels
    .map((level) => ({ ...level, distance: distancePct(decision?.currentPrice, level.value) }))
    .filter((level) => level.distance != null)
    .sort((a, b) => Math.abs(a.distance) - Math.abs(b.distance));
};

export function buildResearchPriority(decision, updatedAt, now = new Date()) {
  const evidence = [];
  const levels = levelEvidence(decision);
  const nearest = levels[0] ?? null;
  const statusText = `${decision?.status ?? ''}`;
  const levelRisk = [decision?.support, decision?.resistance]
    .find((level) => LEVEL_RISK_PATTERN.test(String(level?.state ?? '')));
  const changePct = Number(decision?.changePct);
  const updated = toDate(decision?.dataAsOf ?? updatedAt);
  const current = toDate(now);
  const calendarAgeDays = updated && current ? Math.max(0, (current.valueOf() - updated.valueOf()) / 86_400_000) : null;
  const tradingAgeDays = tradingDaysSince(decision?.sessionDate, current, decision?.market);
  const ageDays = tradingAgeDays ?? calendarAgeDays;
  const freshness = ageDays == null ? 'unknown' : ageDays > 3 ? 'stale' : ageDays > 1 ? 'aging' : 'fresh';

  let rank = 1;
  let key = 'routine';
  let label = '常规跟踪';
  let reason = '按既定条件继续观察';

  if (decision?.invalidation?.state === 'triggered') {
    rank = 5;
    key = 'risk';
    label = '失效已触发';
    reason = `${decision.invalidation.label}已触发`;
    evidence.push('失效状态命中');
  } else if (decision?.invalidation?.state === 'near') {
    rank = 4;
    key = 'near';
    label = '接近失效';
    reason = `接近${decision.invalidation.label}`;
    evidence.push('接近失效状态命中');
  }

  if (!['triggered', 'near'].includes(decision?.invalidation?.state) && rank < 5 && (RISK_PATTERN.test(statusText) || levelRisk)) {
    rank = 5;
    key = 'risk';
    label = '风险处置';
    reason = RISK_PATTERN.test(statusText)
      ? decision?.status
      : `${levelRisk.label}${levelRisk.state}`;
    evidence.push(RISK_PATTERN.test(statusText) ? '风险语义命中' : '关键位状态命中');
  }

  if (nearest && Math.abs(nearest.distance) <= 3 && decision?.invalidation?.state !== 'triggered') {
    const distanceText = `${Math.abs(nearest.distance).toFixed(1)}%`;
    const isInvalidation = nearest.kind === 'invalidation';
    const candidateRank = 4;
    const candidateKey = 'near';
    const candidateLabel = isInvalidation ? '接近失效' : '接近触发';
    const candidateReason = `距${nearest.label} ${distanceText}`;
    evidence.push(candidateReason);
    if (candidateRank > rank) {
      rank = candidateRank;
      key = candidateKey;
      label = candidateLabel;
      reason = candidateReason;
    } else if (candidateRank === rank && !reason.includes('距')) {
      reason = `${reason}；${candidateReason}`;
    }
  }

  if (Number.isFinite(changePct) && Math.abs(changePct) >= 3) {
    const changeReason = `单日${changePct >= 0 ? '上涨' : '下跌'} ${Math.abs(changePct).toFixed(2)}%`;
    evidence.push(changeReason);
    if (rank < 3) {
      rank = 3;
      key = 'volatile';
      label = '异常波动';
      reason = changeReason;
    }
  }

  if (ageDays != null && ageDays > 3) {
    const staleReason = decision?.sessionDate
      ? `距行情交易日 ${Math.floor(ageDays)} 个交易日`
      : `距最后同步 ${Math.floor(ageDays)} 天`;
    evidence.push(staleReason);
    if (rank < 2) {
      rank = 2;
      key = 'stale';
      label = '待复核';
      reason = staleReason;
    }
  }

  return {
    rank,
    key,
    label,
    reason,
    evidence,
    nearestDistancePct: nearest?.distance ?? null,
    ageDays,
    calendarAgeDays,
    tradingAgeDays,
    freshness,
  };
}

export function sortByResearchPriority(posts, now = new Date()) {
  return [...posts].sort((a, b) => {
    const aDate = a.data.updatedDate ?? a.data.pubDate;
    const bDate = b.data.updatedDate ?? b.data.pubDate;
    const aPriority = buildResearchPriority(a.data.decision, aDate, now);
    const bPriority = buildResearchPriority(b.data.decision, bDate, now);
    const freshnessWeight = { unknown: 3, stale: 3, aging: 2, fresh: 1 };
    return bPriority.rank - aPriority.rank
      || freshnessWeight[bPriority.freshness] - freshnessWeight[aPriority.freshness]
      || bDate.valueOf() - aDate.valueOf();
  });
}

export function sortByMarketDataTime(posts) {
  return [...posts].sort((a, b) => {
    const aTime = toDate(a.data.decision?.dataAsOf)?.valueOf() ?? 0;
    const bTime = toDate(b.data.decision?.dataAsOf)?.valueOf() ?? 0;
    return bTime - aTime;
  });
}
