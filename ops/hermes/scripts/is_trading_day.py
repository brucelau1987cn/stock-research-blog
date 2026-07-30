#!/usr/bin/env python3
"""
A-share trading day checker for 2026.
Exits with code 0 if today is a trading day, 1 if not.
Silent output - just the exit code matters.
"""
import sys
from datetime import date, timedelta

# 2026年A股法定节假日休市（来源：沪深北交易所公告）
HOLIDAYS = [
    (date(2026, 1, 1),  date(2026, 1, 3)),   # 元旦
    (date(2026, 2, 15), date(2026, 2, 23)),  # 春节（含除夕）
    (date(2026, 4, 4),  date(2026, 4, 6)),   # 清明节
    (date(2026, 5, 1),  date(2026, 5, 5)),   # 劳动节
    (date(2026, 6, 19), date(2026, 6, 21)),  # 端午节
    (date(2026, 9, 25), date(2026, 9, 27)),  # 中秋节
    (date(2026, 10, 1), date(2026, 10, 7)),  # 国庆节
]

# 特殊调休工作日（周末补班，见上交所公告）
SPECIAL_WORKDAYS = [
    # 2026年公告中若有调休上班的周末，加在此处
    # date(2026, X, X),
]

def is_trading_day(check_date=None):
    if check_date is None:
        check_date = date.today()
    
    # 周末 → 非交易日
    if check_date.weekday() >= 5:
        return False
    
    # 法定节假日 → 非交易日
    for start, end in HOLIDAYS:
        if start <= check_date <= end:
            return False
    
    # 特殊调休 → 交易日（覆盖上面的周末判断）
    if check_date in SPECIAL_WORKDAYS:
        return True
    
    return True

if __name__ == '__main__':
    result = is_trading_day()
    sys.exit(0 if result else 1)
