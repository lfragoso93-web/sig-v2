#!/usr/bin/env python
import subprocess
import sys
import json

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "--co", "-q"],
    capture_output=True,
    text=True,
    cwd="/app"
)

test_count = len([line for line in result.stdout.split('\n') if line.strip() and 'test_' in line])
print(f"SUCCESS: Found {test_count} tests", flush=True)

if result.returncode != 0:
    sys.exit(1)
