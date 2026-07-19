const NOT_CLEARED = /未突破|未收复|暂未收复|未站稳/;
const SUPPORT_HELD = /已站稳|已收复|暂时收复|守稳|支撑有效/;

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function validateDecision(decision, source = 'unknown') {
  const errors = [];
  if (!decision || typeof decision !== 'object') return errors;

  const current = number(decision.currentPrice);
  const resistance = number(decision.resistance?.value);
  const support = number(decision.support?.value);
  const previous = number(decision.previousClose);
  const changePct = number(decision.changePct);
  const sessionDate = String(decision.sessionDate ?? '');
  const dataAsOf = String(decision.dataAsOf ?? '');

  if (!['CN', 'US', 'HK'].includes(decision.market)) {
    errors.push(`${source}: decision.market 必须是 CN、US 或 HK`);
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) {
    errors.push(`${source}: decision.sessionDate 必须使用 YYYY-MM-DD`);
  }
  const parsedDataAsOf = new Date(dataAsOf);
  if (!dataAsOf || Number.isNaN(parsedDataAsOf.valueOf()) || !/(Z|[+-]\d{2}:\d{2})$/.test(dataAsOf)) {
    errors.push(`${source}: decision.dataAsOf 必须是带时区偏移的 ISO 时间`);
  } else if (sessionDate && dataAsOf.slice(0, 10) !== sessionDate) {
    errors.push(`${source}: decision.dataAsOf 日期必须与 sessionDate 一致`);
  }

  if (current === null || current <= 0) {
    errors.push(`${source}: decision.currentPrice 必须是正数`);
    return errors;
  }

  if (
    resistance !== null &&
    current > resistance &&
    NOT_CLEARED.test(String(decision.resistance?.state ?? ''))
  ) {
    errors.push(
      `${source}: 现价 ${current} 高于阻力/恢复位 ${resistance}，状态不能是“${decision.resistance.state}”`,
    );
  }

  if (
    support !== null &&
    current < support &&
    SUPPORT_HELD.test(String(decision.support?.state ?? ''))
  ) {
    errors.push(
      `${source}: 现价 ${current} 低于支撑/防守位 ${support}，状态不能是“${decision.support.state}”`,
    );
  }

  if (previous !== null && previous > 0 && changePct !== null) {
    const calculated = ((current - previous) / previous) * 100;
    if (Math.abs(calculated - changePct) > 0.08) {
      errors.push(
        `${source}: 涨跌幅 ${changePct}% 与现价/前收计算值 ${calculated.toFixed(2)}% 不一致`,
      );
    }
  }

  return errors;
}
