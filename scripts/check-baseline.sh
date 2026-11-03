#!/usr/bin/env bash
# Run from any directory; stop before producing an image if any check fails.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
uv sync --locked --extra api
uv pip check
uv run --locked --extra api ruff check .
uv run --locked --extra api python -m pytest tests/ -v
uv export --locked --format requirements.txt --extra api --no-default-groups --group dev --no-emit-project --output-file "$tmp/requirements.txt" >/dev/null
# Ignore only the generated command header, whose output path differs.
cmp <(tail -n +3 requirements.txt) <(tail -n +3 "$tmp/requirements.txt")
uv build --out-dir "$tmp/dist"
# Exercise both published distributions outside the checkout, without PYTHONPATH.
for package in "$tmp"/dist/*; do
  uv venv --python 3.13 --clear "$tmp/installed"
  uv pip sync --python "$tmp/installed/bin/python" "$tmp/requirements.txt"
  uv pip install --python "$tmp/installed/bin/python" --no-deps "$package"
  uv pip check --python "$tmp/installed/bin/python"
  (cd "$tmp"; env -u PYTHONPATH "$tmp/installed/bin/python" "$root/scripts/check-installed.py" "$root")
done
bash scripts/check-containers.sh
