#!/bin/bash
set -e

echo "Waiting for HR Agent..."
until curl -sf http://localhost:8000/health > /dev/null; do sleep 2; done

echo "Initializing knowledge base..."
curl -sf -X POST http://localhost:8000/admin/reload-kb

echo "Done. Agent available at http://localhost:8000"
