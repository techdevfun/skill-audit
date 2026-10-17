#!/bin/sh
# Fail CI when the skills pack has errors.
set -e
PYTHONPATH=src python -m skill_audit check --path skills --format text
