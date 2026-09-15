# CONTRACT — divergence records in `mycelium.py`

A `DivergenceRecord` asserts an exact counterexample: for the recorded input,
the target expression and the candidate expression reduce to **two different
normal forms**.

- `DivergenceRecord.verify(replay_counterexample=True)` returns `True` only when
  that assertion is re-established by replay within the record's replay budget,
  and `False` otherwise.
- `EpistemicRegistry` neither accepts nor reports a record whose assertion has
  not been established.
- The mechanism that creates divergence records does not create a record whose
  assertion it has not itself established.

This contract says nothing about how the reducer reports its state, about
budget values, or about where in `mycelium.py` the handling lives.
