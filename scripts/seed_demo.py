"""Tạo dữ liệu demo qua API (không ghi thẳng vào DB): tài khoản, PDF mẫu, dataset MẪU đã duyệt.

Dataset là bản MẪU do AI soạn để minh họa luồng, không dùng làm số đo chất lượng (xem docs/demo_script.md).

    docker compose up -d
    python scripts/seed_demo.py --email demo@example.com --password "mat-khau-dai-it-nhat-8"
    python scripts/seed_demo.py --api https://api.ten-cua-ban.example ...      # máy chủ thật
"""

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "backend" / "tests" / "fixtures" / "vi_two_pages.pdf"
SAMPLE = ROOT / "evaluation" / "datasets" / "sample_cases_vi_two_pages.json"


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def call(self, method: str, path: str, *, json_body=None, files=None, expected=(200, 201, 202)):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        data = None
        if json_body is not None:
            data, headers["Content-Type"] = json.dumps(json_body).encode(), "application/json"
        elif files is not None:
            boundary = uuid.uuid4().hex
            field, filename, content, content_type = files
            data = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        payload = json.loads(body) if body else None
        if status not in expected:
            message = (payload or {}).get("error", {}).get("message", body[:200])
            raise SystemExit(f"{method} {path} thất bại ({status}): {message}")
        return status, payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    api = ApiClient(args.api)

    status, _ = api.call("POST", "/api/v1/auth/register", json_body={"email": args.email, "password": args.password}, expected=(201, 409))
    print("Tài khoản:", "đã tạo" if status == 201 else "đã có, dùng lại")
    _, token = api.call("POST", "/api/v1/auth/login", json_body={"email": args.email, "password": args.password})
    api.token = token["access_token"]

    status, document = api.call("POST", "/api/v1/documents", files=("file", PDF.name, PDF.read_bytes(), "application/pdf"), expected=(202, 409))
    if status == 409:
        print("Tài liệu mẫu: đã có")
    else:
        print("Tài liệu mẫu: đang xử lý (lần đầu có thể mất khoảng 1 phút để tải model embedding)")
        for _ in range(90):
            _, detail = api.call("GET", f"/api/v1/documents/{document['id']}")
            if detail["status"] in ("ready", "failed"):
                break
            time.sleep(2)
        if detail["status"] != "ready":
            raise SystemExit(f"Tài liệu không xử lý được: {detail.get('error_message') or detail['status']}")
        print("Tài liệu mẫu: sẵn sàng")

    name = "Dataset MẪU (chưa được người duyệt nội dung)"
    _, existing = api.call("GET", "/api/v1/datasets?limit=100")
    if any(item["name"] == name for item in existing["items"]):
        print("Dataset mẫu: đã có, bỏ qua")
        return
    _, dataset = api.call("POST", "/api/v1/datasets", json_body={"name": name, "description": "Chỉ để demo luồng đánh giá."})
    _, versions = api.call("GET", f"/api/v1/datasets/{dataset['id']}/versions")
    version_id = versions["items"][0]["id"]
    api.call("POST", f"/api/v1/dataset-versions/{version_id}/test-cases/import", files=("file", SAMPLE.name, SAMPLE.read_bytes(), "application/json"))
    api.call("POST", f"/api/v1/dataset-versions/{version_id}/review")
    print("Dataset mẫu: đã nhập và đóng băng phiên bản 1 (để chạy được Đánh giá và Benchmark)")
    print("Xong. Mở giao diện, đăng nhập bằng tài khoản trên và làm theo docs/demo_script.md")


if __name__ == "__main__":
    main()
