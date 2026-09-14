"""Executable counterpart of frozen scoring/decision.json. Prefixes only, no retries."""
SCHEDULE = ('N', 'T', 'P', 'T', 'P', 'N', 'P', 'N', 'T')

def decide(rows):
    if len(rows) > 9:
        raise ValueError('TOO_MANY_SLOTS')
    for i, row in enumerate(rows):
        if row['arm'] != SCHEDULE[i] or type(row['pass']) is not bool or type(row['valid']) is not bool:
            raise ValueError('INVALID_SCHEDULE_OR_OUTCOME')
    counts = {arm: sum(r['pass'] for r in rows if r['arm'] == arm) for arm in 'NTP'}
    observed = {arm: sum(r['arm'] == arm for r in rows) for arm in 'NTP'}
    if any(not r['valid'] for r in rows):
        status = 'ENVIRONMENT_INDETERMINATE'
    elif len(rows) >= 3 and len({r['pass'] for r in rows[:3]}) == 1:
        if len(rows) != 3:
            raise ValueError('SLOTS_AFTER_EARLY_STOP')
        status = 'EARLY_UNIFORM_SUCCESS' if rows[0]['pass'] else 'EARLY_UNIFORM_FAILURE'
    elif len(rows) < 9:
        status = 'CONTINUE'
    else:
        delta = counts['P'] - counts['T']
        status = ('FOLLOWUP_CANDIDATE' if delta >= 2 else
                  'NEGATIVE_PILOT_SIGNAL' if delta < 0 else 'INDETERMINATE')
    return {'status': status, 'successes': counts, 'observed': observed,
            'remaining': [{'slot': i + 1, 'arm': SCHEDULE[i],
                           'status': 'PENDING' if status == 'CONTINUE' else 'NOT_RUN'}
                          for i in range(len(rows), 9)]}
