const NOT_CLEARED = /未突破|未收复|暂未收复|未站稳/;
const SUPPORT_HELD = /已站稳|已收复|守稳|支撑有效/;

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
