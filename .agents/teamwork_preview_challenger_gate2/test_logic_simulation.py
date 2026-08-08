import subprocess
import os

print("=== EMPIRICAL CHALLENGER SIMULATION & AUDIT TEST ===")

# Check 1: Git Status check from root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
res_git = subprocess.run(["git", "status", "--short"], cwd=root_dir, capture_output=True, text=True)
print("\n--- GIT STATUS CHECK ---")
print("Output:\n" + res_git.stdout.strip())
python_changes = [line for line in res_git.stdout.strip().splitlines() if line.endswith('.py') or 'requirements.txt' in line]
print(f"Backend Python changes detected: {len(python_changes)}")
assert len(python_changes) == 0, f"Integrity error: found Python changes: {python_changes}"

# Check 2: Pytest check from root
res_pytest = subprocess.run(["pytest"], cwd=root_dir, capture_output=True, text=True)
print("\n--- PYTEST CHECK ---")
print(f"Pytest exit code: {res_pytest.returncode}")
print(res_pytest.stdout[:500] if res_pytest.stdout else res_pytest.stderr[:500])
assert res_pytest.returncode == 0, "Pytest suite failed!"

print("\n========================================")
print("ALL EMPIRICAL VERIFICATION TESTS PASSED!")
print("========================================")
