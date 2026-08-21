import os
import re

suspicious_patterns = [
    (r'return\s+True\s*#\s*bypass', 'Test bypass comment'),
    (r'return\s+\{"ok":\s*True\}\s*#\s*dummy', 'Dummy response'),
    (r'raise\s+NotImplementedError', 'NotImplementedError facade'),
]

findings = []
for root, dirs, files in os.walk('.'):
    if any(p in root.replace('\\', '/') for p in ['.git', '.agents', '.venv', '__pycache__', 'build', 'dist', '.gradle']):
        continue
    for f in files:
        if f.endswith(('.py', '.kt', '.java')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                for line_no, line in enumerate(fh, 1):
                    for pat, desc in suspicious_patterns:
                        if re.search(pat, line, re.IGNORECASE):
                            findings.append((p, line_no, desc, line.strip()))

print(f"Total suspicious matches found: {len(findings)}")
for p, line_no, desc, l in findings:
    print(f"  {p}:{line_no} [{desc}] -> {l}")
