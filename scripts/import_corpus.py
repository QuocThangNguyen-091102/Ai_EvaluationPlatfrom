"""Nạp một bộ tài liệu và một file dataset vào hệ thống qua API. Dataset được để ở trạng thái NHÁP để người duyệt.

    python scripts/import_corpus.py --email ban@example.com --password "..." \\
        --documents evaluation/datasets/corpus/solar-system \\
        --dataset evaluation/datasets/solar_system_cases.json --name "Hệ Mặt Trời"

Lỗi câu trích (không tìm thấy, xuất hiện nhiều lần) được in theo từng dòng; khi đó không câu nào được nhập.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_demo import ApiClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--documents", required=True, type=Path, help="thư mục chứa các file .txt, .pdf, .docx")
    parser.add_argument("--dataset", required=True, type=Path, help="file JSON hoặc CSV theo định dạng import của trang Dataset")
    parser.add_argument("--name", required=True, help="tên dataset")
    args = parser.parse_args()
    api = ApiClient(args.api)

    status, _ = api.call("POST", "/api/v1/auth/register", json_body={"email": args.email, "password": args.password}, expected=(201, 409))
    print("Tài khoản:", "đã tạo" if status == 201 else "đã có, dùng lại")
    _, token = api.call("POST", "/api/v1/auth/login", json_body={"email": args.email, "password": args.password})
    api.token = token["access_token"]

    types = {".txt": "text/plain", ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    pending = []
    for path in sorted(p for p in args.documents.iterdir() if p.suffix.lower() in types):
        status, document = api.call("POST", "/api/v1/documents", files=("file", path.name, path.read_bytes(), types[path.suffix.lower()]), expected=(202, 409))
        print(f"  {path.name}: {'đang xử lý' if status == 202 else 'đã có'}")
        if status == 202:
            pending.append(document["id"])
    deadline = time.monotonic() + 900
    while pending and time.monotonic() < deadline:
        time.sleep(3)
        for document_id in list(pending):
            _, detail = api.call("GET", f"/api/v1/documents/{document_id}")
            if detail["status"] == "failed":
                raise SystemExit(f"Xử lý tài liệu thất bại: {detail['filename']}: {detail.get('error_message')}")
            if detail["status"] == "ready":
                pending.remove(document_id)
    if pending:
        raise SystemExit("Quá thời gian chờ xử lý tài liệu")
    print("Tài liệu: tất cả đã sẵn sàng")

    _, dataset = api.call("POST", "/api/v1/datasets", json_body={"name": args.name, "description": f"Nhập từ {args.dataset.name}"}, expected=(201, 409))
    if dataset is None or "id" not in dataset:
        raise SystemExit(f"Dataset tên '{args.name}' đã tồn tại; chọn tên khác")
    _, versions = api.call("GET", f"/api/v1/datasets/{dataset['id']}/versions")
    version_id = versions["items"][0]["id"]
    content_type = "application/json" if args.dataset.suffix.lower() == ".json" else "text/csv"
    status, result = api.call(
        "POST", f"/api/v1/dataset-versions/{version_id}/test-cases/import",
        files=("file", args.dataset.name, args.dataset.read_bytes(), content_type), expected=(200, 201, 422),
    )
    if status == 422:
        details = (result or {}).get("error", {}).get("details") or []
        print(f"Nhập thất bại, {len(details)} lỗi (không câu nào được nhập):")
        for item in details:
            print(f"  dòng {item.get('row')}: {item.get('field', '')} {item.get('issue')}")
        raise SystemExit(1)
    print(f"Đã nhập {result.get('imported', result)} câu vào phiên bản 1 (trạng thái NHÁP, chờ người duyệt)")


if __name__ == "__main__":
    main()
