"""Render real public GitHub calendar activity. No credentials or dependencies."""
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import re
import urllib.request

USERNAME = os.environ.get('PROFILE_USERNAME', 'NithinVChincholi')
ROOT = Path(__file__).resolve().parents[1]

class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.counts = {}, {}
        self.tooltip, self.text = None, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and attrs.get('data-date'):
            self.cells[attrs['id']] = attrs['data-date']
        if tag == 'tool-tip' and attrs.get('for', '').startswith('contribution-day-component-'):
            self.tooltip, self.text = attrs['for'], []

    def handle_data(self, data):
        if self.tooltip:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.tooltip:
            text = ''.join(self.text).strip()
            match = re.search(r'([\d,]+) contributions?', text)
            if match:
                self.counts[self.tooltip] = int(match.group(1).replace(',', ''))
            elif text.startswith('No contributions'):
                self.counts[self.tooltip] = 0
            else:
                raise ValueError('Unrecognized calendar tooltip; refusing to publish incorrect counts')
            self.tooltip = None

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Nithin-Public-Profile', 'Accept': 'application/json' if 'api.github.com' in url else 'text/html'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8')

def metrics(days, today):
    active = sorted(d for d, count in days.items() if count > 0)
    longest = run = 0
    previous = None
    for day in active:
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    cursor = today if days.get(today, 0) else today - timedelta(days=1)
    current = 0
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return sum(days.values()), len(active), longest, current

def render(days, today):
    total, active, longest, current = metrics(days, today)
    start = min(days)
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    colors = ['#243c45', '#215d58', '#258778', '#38b39a', '#64dfc5']
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="405" viewBox="0 0 1100 405" role="img" aria-labelledby="title desc">',
        '<title id="title">Public GitHub contribution activity</title>',
        f'<desc id="desc">{total} visible contributions over {active} active days. Longest streak {longest} days; current streak {current} days. Calendar through {today}.</desc>',
        '<rect width="1100" height="405" rx="20" fill="#101e2b"/>',
        '<text x="36" y="41" fill="#64dfc5" font-family="Segoe UI,Arial,sans-serif" font-size="13" letter-spacing="2">THE BUILDING LOG</text>',
        f'<text x="36" y="68" fill="#9bb6bd" font-family="Segoe UI,Arial,sans-serif" font-size="12">PUBLIC CONTRIBUTIONS · {start:%d %b %Y} — {today:%d %b %Y}</text>']
    for index, (label, value) in enumerate([('Contributions', total), ('Active days', active), ('Longest streak', longest), ('Current streak', current)]):
        x = 36 + index * 261
        parts += [f'<rect x="{x}" y="88" width="245" height="91" rx="12" fill="#192f3b"/>',
                  f'<text x="{x+18}" y="128" fill="#f3f5ee" font-family="Segoe UI,Arial,sans-serif" font-size="32" font-weight="700">{value}</text>',
                  f'<text x="{x+18}" y="155" fill="#a6bfc4" font-family="Segoe UI,Arial,sans-serif" font-size="13">{label}</text>']
    seen_months = set()
    for day, count in sorted(days.items()):
        col = (day - first_sunday).days // 7
        row = (day.weekday() + 1) % 7
        x, y = 37 + col * 19, 224 + row * 18
        month = (day.year, day.month)
        if month not in seen_months:
            seen_months.add(month)
            if col < 52:
                parts.append(f'<text x="{x}" y="210" fill="#91adb4" font-family="Segoe UI,Arial,sans-serif" font-size="10">{day:%b}</text>')
        level = 0 if count == 0 else min(4, 1 + (count >= 3) + (count >= 6) + (count >= 10))
        parts.append(f'<rect x="{x}" y="{y}" width="14" height="14" rx="3" fill="{colors[level]}"><title>{day}: {count} contributions</title></rect>')
    parts += [f'<text x="37" y="375" fill="#91adb4" font-family="Segoe UI,Arial,sans-serif" font-size="11">Updated {datetime.now(timezone.utc):%d %b %Y} · Active days reflect GitHub activity, not hours worked.</text>', '</svg>']
    return '\n'.join(parts)

def main():
    parser = Calendar()
    parser.feed(fetch(f'https://github.com/users/{USERNAME}/contributions'))
    if len(parser.cells) < 350 or any(key not in parser.counts for key in parser.cells):
        raise ValueError('Incomplete public calendar; existing artwork was preserved')
    today = datetime.now(timezone.utc).date()
    days = {date.fromisoformat(day): parser.counts[key] for key, day in parser.cells.items() if date.fromisoformat(day) <= today}
    output = ROOT / 'assets' / 'activity.svg'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(days, today), encoding='utf-8')
    print(json.dumps(dict(zip(['contributions', 'active_days', 'longest_streak', 'current_streak'], metrics(days, today)))))

if __name__ == '__main__':
    main()
