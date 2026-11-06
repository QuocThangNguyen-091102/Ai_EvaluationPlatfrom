"""Tra lỗ hổng đã công bố cho mọi gói Python (kể cả phụ thuộc gián tiếp) qua API công khai của OSV.dev.

Không cần cài thêm công cụ; chỉ gửi tên và phiên bản gói (thông tin công khai).

    python scripts/audit_dependencies.py backend/.venv/Scripts/python.exe        # venv trên máy host
    docker compose exec -T backend python -m pip freeze --all > freeze.txt
    python scripts/audit_dependencies.py freeze.txt                              # image backend
"""

import json
import os
import subprocess
import sys
import urllib.request

source = os.path.abspath(sys.argv[1])
if source.endswith(".txt"):
    frozen = open(source, encoding="utf-8").read()  # kết quả pip freeze lấy từ nơi khác (ví dụ container)
else:
    frozen = subprocess.run([source, "-m", "pip", "freeze", "--all"], capture_output=True, text=True, check=True).stdout
packages = []
for line in frozen.splitlines():
    if "==" in line:
        name, version = line.split("==", 1)
        packages.append((name.strip(), version.strip().split("+")[0]))

queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in packages]
request = urllib.request.Request(
    "https://api.osv.dev/v1/querybatch",
    data=json.dumps({"queries": queries}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=60) as response:
    results = json.load(response)["results"]

found = [(pkg, r["vulns"]) for pkg, r in zip(packages, results) if r.get("vulns")]
print(f"Đã kiểm tra {len(packages)} gói.")
for (name, version), vulns in found:
    ids = []
    for vuln in vulns:
        detail = json.load(urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vuln['id']}", timeout=30))
        fixed = sorted(
            {e["fixed"] for a in detail.get("affected", []) for r in a.get("ranges", []) for e in r.get("events", []) if "fixed" in e}
        )
        ids.append(f"{vuln['id']} (sửa ở: {', '.join(fixed) or 'chưa có'}) — {detail.get('summary', '')[:90]}")
    print(f"- {name}=={version}:")
    for item in ids:
        print(f"    {item}")
if not found:
    print("Không có lỗ hổng đã biết.")
