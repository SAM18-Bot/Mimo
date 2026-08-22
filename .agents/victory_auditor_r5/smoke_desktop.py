import subprocess
import sys
import time

print("Launching dist/Mimo/Mimo.exe...")
proc = subprocess.Popen(['dist/Mimo/Mimo.exe'])
print(f"Process spawned with PID {proc.pid}")

time.sleep(3)
poll = proc.poll()

if poll is None:
    print(f"PASS: Mimo.exe is running steadily (PID {proc.pid}). Terminating now.")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    sys.exit(0)
else:
    print(f"FAIL: Mimo.exe terminated prematurely with exit code {poll}")
    sys.exit(1)
