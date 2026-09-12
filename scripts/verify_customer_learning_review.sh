#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python -m py_compile backend/app/routes_persistent/learning.py
grep -q 'row.tenant_id != tenant_id' backend/app/routes_persistent/learning.py
grep -q 'global_learning_contribution: bool = False' backend/app/routes_persistent/learning.py
echo "Kaiwora customer learning review verification: PASS"
