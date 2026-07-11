const STATUS_PATTERNS = [
  ['偏多', /偏多|看多|修复确认|多头/],
  ['观望/防守', /观望|防守|清仓|弱势|等待确认|未收复|风险/],
  ['偏空', /偏空|看空|破位|失效/],
];

export function buildSearchIndex(code, name, title) {
  return [code, name, title]
    .map((value) => String(value ?? '').trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ');
}

export function compactSummary(value, maxLength = 72) {
  const text = String(value ?? '')
    .replace(/^最新结论[：:]/, '')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

const classifySentiment = (source) => {
  for (const [label, pattern] of STATUS_PATTERNS) {
    if (pattern.test(source)) return label;
  }
  return null;
};

export function inferSentiment(decision, description = '') {
  return classifySentiment(decision?.status ?? '')
    ?? classifySentiment(description)
    ?? '跟踪中';
}
