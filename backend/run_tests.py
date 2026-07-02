import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "pytest", "pytest-asyncio"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Failed to install pytest")
    print(result.stderr)
    sys.exit(1)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "--cov=app.services", "--cov-report=term", "-v"],
    capture_output=True,
    text=True
)

print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
