"""Dựng báo cáo CSV từ dữ liệu đã lưu của một lượt đánh giá. Hàm thuần: chỉ định dạng, không tính lại điểm.

Báo cáo gồm hai phần: thông tin lượt chạy (dạng khóa, giá trị) rồi bảng kết quả từng câu. Mọi con số lấy nguyên từ
database; ô trống nghĩa là không tính được hoặc không áp dụng (không phải 0).
"""

import csv
import io
from collections.abc import Mapping, Sequence


def build_csv(metadata: Sequence[tuple[str, object]], columns: Sequence[str], rows: Sequence[Mapping[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Thông tin", "Giá trị"])
    for key, value in metadata:
        writer.writerow([key, _cell(value)])
    writer.writerow([])
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row.get(column)) for column in columns])
    # BOM để Excel đọc đúng chữ tiếng Việt.
    return "﻿" + buffer.getvalue()


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
