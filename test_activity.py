from datetime import date
import unittest
from scripts.update_activity import metrics, Calendar

class ActivityTests(unittest.TestCase):
    def test_streak_continues_from_yesterday(self):
        days = {date(2026,10,23):2, date(2026,10,24):1, date(2026,10,25):3, date(2026,10,26):0}
        self.assertEqual(metrics(days, date(2026,10,26)), (6,3,3,3))

    def test_gap_breaks_current_streak(self):
        self.assertEqual(metrics({date(2026,10,22):4}, date(2026,10,26)), (4,1,1,0))

    def test_calendar_counts_are_parsed(self):
        parser = Calendar()
        parser.feed('<td id="contribution-day-component-0-0" data-date="2026-10-26"></td><tool-tip for="contribution-day-component-0-0">12 contributions on October 26th.</tool-tip>')
        self.assertEqual(parser.counts['contribution-day-component-0-0'], 12)

if __name__ == '__main__':
    unittest.main()
