"""Fixed three-test measurement plus explicit fixture-order observations."""
import io
import json
import sys
import unittest
import test_empirical_settlement as t

NAMES = [
    'test_an_unsettled_fixture_does_not_mask_a_settled_mismatch',
    'test_both_suspended_on_the_same_term_is_not_a_pass',
    'test_both_suspended_on_different_terms_is_not_a_fail',
]
suite = unittest.TestSuite(t.EmpiricalSettlementTest(name) for name in NAMES)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
case = t.EmpiricalSettlementTest()
case.setUp()
orders = []
for fixtures in ([t.OMEGA, t.K], [t.K, t.OMEGA]):
    verdict = case.audit(t.I, f'{t.K} {t.I}', fixtures)
    orders.append({'fixtures': fixtures, 'verdict': verdict.status.value, 'reason': verdict.reason})
print(json.dumps({'tests_run': result.testsRun, 'failures': [test.id() for test, _ in result.failures],
                  'errors': [test.id() for test, _ in result.errors], 'test_output': stream.getvalue(),
                  'fixture_orders': orders, 'budget': t.BUDGET}, ensure_ascii=False))
sys.exit(0 if result.wasSuccessful() else 1)
