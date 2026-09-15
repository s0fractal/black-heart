"""Executable counterpart of the PLAN.md decision rule. Three slots, no early stop, no re-run.

Adapted from experiments/transfer-1/harness/decision.py: the schedule is one
condition (S1, S2, S3); rows carry a four-way classification instead of
pass/valid. classify() adds INVALID in front of the grader's PASS/FAIL/PARTIAL
(plan order INVALID > PASS > FAIL > PARTIAL; the grader already applies the
last three exclusively). An INVALID slot ends the block as INCOMPLETE: the plan
repeats no slot without a new package review, and fewer than three valid
sessions is an incomplete result either way.
"""
SCHEDULE = ('S1', 'S2', 'S3')
CLASSES = ('INVALID', 'PASS', 'FAIL', 'PARTIAL')
OUTCOMES = ('PASS', 'FAIL', 'PARTIAL')
NEXT_STEP = {3: 'TASK_UNSUITABLE_FOR_COMPARISON; find another task, do not change this one',
             2: 'AMBIGUOUS; no automatic re-run; decide in result review',
             1: 'CANDIDATE_FOR_COMPARISON_PLAN; separate plan needs review',
             0: 'CANDIDATE_FOR_COMPARISON_PLAN; analyse the failures first (false fix, hint read, time)'}


def classify(infrastructure_valid, outcome):
    if type(infrastructure_valid) is not bool:
        raise ValueError('INVALID_VALIDITY')
    if not infrastructure_valid:
        return 'INVALID'
    if outcome not in OUTCOMES:
        raise ValueError('INVALID_GRADER_OUTCOME')
    return outcome


def decide(rows):
    if len(rows) > len(SCHEDULE):
        raise ValueError('TOO_MANY_SLOTS')
    for i, row in enumerate(rows):
        if row['slot'] != i + 1 or row['classification'] not in CLASSES:
            raise ValueError('INVALID_SCHEDULE_OR_OUTCOME')
    counts = {c: sum(r['classification'] == c for r in rows) for c in CLASSES}
    if counts['INVALID']:
        status, next_step = 'INCOMPLETE', 'INVALID slot present; re-run only under a new package review'
    elif len(rows) < len(SCHEDULE):
        status, next_step = 'CONTINUE', None
    else:
        status, next_step = 'COMPLETE', NEXT_STEP[counts['PASS']]
    return {'status': status, 'counts': counts, 'valid': len(rows) - counts['INVALID'],
            'next_step': next_step,
            'remaining': [{'slot': i + 1, 'status': 'PENDING' if status == 'CONTINUE' else 'NOT_RUN'}
                          for i in range(len(rows), len(SCHEDULE))]}
