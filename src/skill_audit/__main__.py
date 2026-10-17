"""Allow `python -m skill_audit check ...`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
