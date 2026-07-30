#!/usr/bin/env python3
"""
US stock market trading day checker for 2026.
Exits with code 0 if today is a trading day, 1 if not.
Silent output - just the exit code matters.
"""
import sys
from datetime import date

# 2026 US Market Holidays (NYSE / NASDAQ)
# Note: For holidays falling on Saturday, the market closes on the preceding Friday.
# For holidays falling on Sunday, the market closes on the following Monday.
HOLIDAYS = [
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Washington's Birthday
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth National Independence Day
    date(2026, 7, 3),   # Independence Day (Observed - July 4 is Saturday)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving Day
    date(2026, 12, 25), # Christmas Day
]

def is_us_trading_day(check_date=None):
    if check_date is None:
        check_date = date.today()
    
    # Weekends -> non-trading day
    if check_date.weekday() >= 5:
        return False
        
    # Public holidays -> non-trading day
    if check_date in HOLIDAYS:
        return False
        
    return True

if __name__ == '__main__':
    result = is_us_trading_day()
    sys.exit(0 if result else 1)
