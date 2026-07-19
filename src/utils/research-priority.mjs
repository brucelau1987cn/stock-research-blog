const RISK_PATTERN = /偏空|清仓|退出|失效|破位|跌破|失守|防守线下|止损|降低仓位|减仓/;

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
  const changePct = Number(decision?.changePct);
  const updated = toDate(updatedAt);
  const current = toDate(now);
  const ageDays = updated && current ? Math.max(0, (current.valueOf() - updated.valueOf()) / 86_400_000) : null;

  let rank = 1;
  let key = 'routine';
  let label = '常规跟踪';
  let reason = '按既定条件继续观察';

  if (RISK_PATTERN.test(statusText)) {
    rank = 5;
    key = 'risk';
    label = '风险处置';
    reason = decision?.status || decision?.action || '风险条件已出现';
    evidence.push('风险语义命中');
  }

  if (nearest && Math.abs(nearest.distance) <= 3) {
    const distanceText = `${Math.abs(nearest.distance).toFixed(1)}%`;
    const isInvalidation = nearest.kind === 'invalidation';
    const candidateRank = isInvalidation ? 5 : 4;
    const candidateKey = isInvalidation ? 'risk' : 'near';
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

  if (ageDays != null && ageDays > 4) {
    const staleReason = `距最后同步 ${Math.floor(ageDays)} 天`;
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
  };
}

export function sortByResearchPriority(posts, now = new Date()) {
  return [...posts].sort((a, b) => {
    const aDate = a.data.updatedDate ?? a.data.pubDate;
    const bDate = b.data.updatedDate ?? b.data.pubDate;
    const aPriority = buildResearchPriority(a.data.decision, aDate, now);
    const bPriority = buildResearchPriority(b.data.decision, bDate, now);
    return bPriority.rank - aPriority.rank || bDate.valueOf() - aDate.valueOf();
  });
}
