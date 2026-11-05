"""Cấu hình log của ứng dụng.

Quy tắc: không ghi mật khẩu, token, API key, nội dung tài liệu hay nội dung câu hỏi vào log.
Chỉ ghi định danh (id), trạng thái và thông tin kỹ thuật.
"""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format=LOG_FORMAT, force=True)
