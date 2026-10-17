# Contributing

Small, focused PRs are welcome.

1. Fork, create a branch, make your change.
2. Add or update a test in `tests/` when you change audit logic.
3. Run `PYTHONPATH=src python -m pytest -q` — it must pass.
4. Keep the tool dependency-free (stdlib only). No new dependencies without discussion.
