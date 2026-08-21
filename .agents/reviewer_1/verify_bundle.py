import os
import hashlib
from datetime import datetime

def hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def check_bundle():
    print("=== MIMO DESKTOP BUNDLE VERIFICATION ===")
    
    # Check Mimo.exe
    exe_path = os.path.join("dist", "Mimo", "Mimo.exe")
    if not os.path.exists(exe_path):
        print(f"FAIL: {exe_path} does not exist")
        return False
    
    stat = os.stat(exe_path)
    size_mb = stat.st_size / (1024 * 1024)
    mtime = datetime.fromtimestamp(stat.st_mtime)
    print(f"Mimo.exe size: {stat.st_size:,} bytes ({size_mb:.2f} MB)")
    print(f"Mimo.exe modified: {mtime}")
    print(f"Mimo.exe SHA256: {hash_file(exe_path)}")
    
    if stat.st_size <= 40 * 1024 * 1024:
        print("FAIL: Mimo.exe is not > 40MB")
        return False
    else:
        print("PASS: Mimo.exe > 40MB")
        
    # Check static directory
    static_dirs = [
        ("static", os.path.join("dist", "Mimo", "_internal", "static")),
        ("assets", os.path.join("dist", "Mimo", "_internal", "assets")),
        (os.path.join("desktop", "assets"), os.path.join("dist", "Mimo", "_internal", "desktop", "assets"))
    ]
    
    all_match = True
    for src_dir, dst_dir in static_dirs:
        print(f"\nComparing {src_dir} -> {dst_dir}:")
        if not os.path.exists(dst_dir):
            print(f"FAIL: Destination dir {dst_dir} missing!")
            all_match = False
            continue
            
        src_files = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        for fname in src_files:
            src_f = os.path.join(src_dir, fname)
            dst_f = os.path.join(dst_dir, fname)
            if not os.path.exists(dst_f):
                print(f"  MISSING: {dst_f}")
                all_match = False
            else:
                s_hash = hash_file(src_f)
                d_hash = hash_file(dst_f)
                match = (s_hash == d_hash)
                print(f"  {'MATCH' if match else 'MISMATCH'}: {fname} ({os.path.getsize(src_f)} bytes)")
                if not match:
                    all_match = False
                    
    # Check specific required static files
    required_static = ["dashboard.html", "settings.html", "file_tree.html", "parent_portal.html", "schedule.html"]
    print("\nVerifying required static HTML templates in dist/Mimo/_internal/static/:")
    for req in required_static:
        req_path = os.path.join("dist", "Mimo", "_internal", "static", req)
        if os.path.exists(req_path):
            print(f"  PASS: {req} present ({os.path.getsize(req_path)} bytes)")
        else:
            print(f"  FAIL: {req} missing")
            all_match = False
            
    print(f"\nOverall Bundle Asset Integrity: {'PASS' if all_match else 'FAIL'}")
    return all_match

if __name__ == "__main__":
    check_bundle()
