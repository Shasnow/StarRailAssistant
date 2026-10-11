"""Strict, optional opening rules must not silently unlock spending or sales."""

import copy
import unittest

from test_currency_wars_round_policy import policy


class OpeningConfigTests(unittest.TestCase):
    def test_omission_and_empty_policy_preserve_unconfigured_actions(self):
        self.assertIsNone(policy.parse_opening_policy_config(None))
        self.assertEqual(policy.parse_opening_policy_config({}), policy.OpeningPolicyConfig())

    def test_explicit_rounds_are_inclusive_independent_and_nonmutating(self):
        raw = {"sell_from_round": "1-4", "refresh_from_round": "2-1"}
        before = copy.deepcopy(raw)
        self.assertEqual(policy.parse_opening_policy_config(raw),
                         policy.OpeningPolicyConfig((1, 4), (2, 1)))
        self.assertEqual(raw, before)
        self.assertEqual(policy.parse_opening_policy_config({"sell_from_round": "1-4"}),
                         policy.OpeningPolicyConfig((1, 4), None))

    def test_typo_and_nonobject_policy_never_disable_a_guard_silently(self):
        for raw in (True, [], "1-4", {"sell_from": "1-4"}, {"enabled": True}):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "opening_policy"):
                policy.parse_opening_policy_config(raw)

    def test_only_complete_canonical_config_rounds_are_accepted(self):
        for key in ("sell_from_round", "refresh_from_round"):
            for value in (None, True, 14, (1, 4), "0-4", "1-0", "10-4", "1-10",
                          "01-4", "1/4", "1—4", " 1-4 ", "备战阶段1-4"):
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                    policy.parse_opening_policy_config({key: value})


if __name__ == "__main__":
    unittest.main()
