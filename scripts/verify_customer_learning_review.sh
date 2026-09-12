#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
python -m py_compile app/routes_persistent/learning.py app/services/learning_service.py app/services/knowledge_resolver.py
PYTHONPATH=. pytest -q tests/test_cloud_tenant_scope.py tests/test_knowledge_resolver.py tests/test_global_learning_v43.py
cd ../frontend
npm ci
npm run build
