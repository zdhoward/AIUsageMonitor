import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aimon.sources.claude_resets import parse_inventory  # noqa: E402

NOW = 1_800_000_000  # 2027-01-15T08:00:00Z
FUTURE_A = "2027-01-16T08:00:00Z"  # NOW + 86400
FUTURE_B = "2027-01-17T09:00:00+01:00"  # NOW + 2*86400 (08:00Z)
PAST = "2027-01-14T08:00:00Z"
UNKNOWN = {"rc": -1, "rx": 0}


def g(left=1, usable=True, **kw):
    d = {"resets_left": left, "usable_now": usable}
    d.update(kw)
    return d


def inv(*grants, eligible=True):
    return {"eligible": eligible, "grants": list(grants)}


class ParseInventoryTests(unittest.TestCase):
    def test_valid_sum_and_soonest_expiry(self):
        r = parse_inventory(inv(g(2, ends_at=FUTURE_B), g(1, ends_at=FUTURE_A)), NOW)
        self.assertEqual(r, {"rc": 3, "rx": NOW + 86400})

    def test_offset_timezone(self):
        r = parse_inventory(inv(g(1, ends_at=FUTURE_B)), NOW)
        self.assertEqual(r, {"rc": 1, "rx": NOW + 2 * 86400})

    def test_known_zero(self):
        self.assertEqual(parse_inventory(inv(eligible=False), NOW), {"rc": 0, "rx": 0})
        self.assertEqual(parse_inventory(inv(), NOW), {"rc": 0, "rx": 0})

    def test_ignored_grants(self):
        r = parse_inventory(
            inv(
                g(1, ends_at=PAST),
                g(1, paused=True),
                g(0),
                g(1, usable=False),
                g(4, paused=False, ends_at=FUTURE_A),
            ),
            NOW,
        )
        self.assertEqual(r, {"rc": 4, "rx": NOW + 86400})

    def test_all_ignored_is_known_zero(self):
        self.assertEqual(parse_inventory(inv(g(1, ends_at=PAST)), NOW), {"rc": 0, "rx": 0})

    def test_unknown_expiry_does_not_hide_a_known_expiry(self):
        r = parse_inventory(inv(g(1), g(1, ends_at=FUTURE_A), g(1, ends_at=None)), NOW)
        self.assertEqual(r, {"rc": 3, "rx": NOW + 86400})
        self.assertEqual(parse_inventory(inv(g(1)), NOW), {"rc": 1, "rx": 0})

    def test_missing_or_malformed_block(self):
        for bad in (None, [], "x", 5, {}, {"eligible": True}, {"grants": []},
                    {"eligible": "true", "grants": []},
                    {"eligible": 1, "grants": []},
                    {"eligible": True, "grants": None},
                    {"eligible": False, "grants": {}}):
            self.assertEqual(parse_inventory(bad, NOW), UNKNOWN, bad)

    def test_ineligible_with_grants_is_unknown(self):
        self.assertEqual(parse_inventory(inv(g(1), eligible=False), NOW), UNKNOWN)

    def test_invalid_grants_make_inventory_unknown(self):
        bad_grants = [
            "x",
            {"usable_now": True},
            g(True),
            g(-1),
            g(1.5),
            g("1"),
            {"resets_left": 1},
            {"resets_left": 1, "usable_now": "yes"},
            g(1, paused="no"),
            g(1, ends_at="2027-01-16"),
            g(1, ends_at="2027-01-16T08:00:00"),
            g(1, ends_at="nan"),
            g(1, ends_at=12345),
            g(1, ends_at="garbage"),
            g(1, ends_at="2027-13-16T08:00:00Z"),
        ]
        for bad in bad_grants:
            self.assertEqual(parse_inventory(inv(g(1), bad), NOW), UNKNOWN, bad)

    def test_no_identifiers_returned(self):
        r = parse_inventory(inv(g(1, id="secret", ends_at=FUTURE_A), ) | {"next_grant_id": "x"}, NOW)
        self.assertEqual(set(r), {"rc", "rx"})

    def test_fractional_seconds_and_invalid_timezone(self):
        for fraction in ('.1', '.123', '.123456', '.123456789'):
            result = parse_inventory(inv(g(1, ends_at='2027-01-16T08:00:00'+fraction+'Z')), NOW)
            self.assertEqual(result, {'rc': 1, 'rx': NOW+86400})
        self.assertEqual(parse_inventory(inv(g(1, ends_at='2027-01-16T08:00:00+00:99')), NOW), UNKNOWN)


if __name__ == "__main__":
    unittest.main()
