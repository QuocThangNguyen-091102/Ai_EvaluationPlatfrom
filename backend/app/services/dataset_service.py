"""Use case dataset đánh giá: dataset, version, test case, import, duyệt và đóng băng version (M5).

Quy tắc: version đã duyệt (reviewed) là bất biến; mọi thao tác sửa nội dung đều bị từ chối với 409. Muốn sửa thì tạo
version mới (có thể sao chép từ version cũ). Mọi reference context được kiểm chứng: câu trích phải tìm thấy đúng một
lần trong một tài liệu "ready" của chính user.
"""

import uuid
from datetime import datetime, timezone

from app.core.exceptions import AppError
from app.models.dataset import DatasetVersion, EvaluationDataset, EvaluationTestCase
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository, DuplicateDatasetNameError
from app.schemas.dataset import TestCaseInput
from evaluation.datasets.dataset_loader import ReferenceSpec, TestCaseSpec, load_test_cases, validate_spec
from evaluation.datasets.reference_locator import ChunkSpan, locate_quote

MAX_IMPORT_BYTES = 2 * 1024 * 1024


class _ReferenceError(ValueError):
    pass


class DatasetService:
    def __init__(self, datasets: DatasetRepository) -> None:
        self._datasets = datasets

    # ----------------------------------------------------------------------------- dataset
    def create_dataset(self, user: User, name: str, description: str | None) -> EvaluationDataset:
        dataset = EvaluationDataset(user_id=user.id, name=name.strip(), description=description)
        try:
            self._datasets.add_dataset(dataset)
        except DuplicateDatasetNameError:
            raise AppError(409, "conflict", "Bạn đã có dataset cùng tên") from None
        self._datasets.add_version(DatasetVersion(dataset_id=dataset.id, version_number=1, status="draft"))
        self._datasets.commit()
        return dataset

    def list_datasets(self, user: User, *, limit: int, offset: int):
        return self._datasets.list_datasets(user.id, limit=limit, offset=offset)

    def get_dataset(self, user: User, dataset_id: uuid.UUID) -> EvaluationDataset:
        dataset = self._datasets.get_dataset(user.id, dataset_id)
        if dataset is None:
            raise AppError(404, "not_found", "Không tìm thấy dataset")
        return dataset

    # ----------------------------------------------------------------------------- version
    def list_versions(self, user: User, dataset_id: uuid.UUID) -> list[tuple[DatasetVersion, int]]:
        self.get_dataset(user, dataset_id)
        return self._datasets.list_versions(dataset_id)

    def create_version(self, user: User, dataset_id: uuid.UUID, copy_from: uuid.UUID | None, notes: str | None) -> tuple[DatasetVersion, int]:
        dataset = self.get_dataset(user, dataset_id)
        source = None
        if copy_from is not None:
            source = self._datasets.get_version(user.id, copy_from)
            if source is None or source.dataset_id != dataset.id:
                raise AppError(404, "not_found", "Không tìm thấy version nguồn trong dataset này")
        version = self._datasets.add_version(
            DatasetVersion(dataset_id=dataset.id, version_number=self._datasets.next_version_number(dataset.id), status="draft", notes=notes)
        )
        copied = 0
        if source is not None:
            cases, _ = self._datasets.list_cases(source.id, question_type=None, difficulty=None, limit=None, offset=0)
            self._datasets.add_cases([_copy_case(case, version.id) for case in cases])
            copied = len(cases)
        self._datasets.commit()
        return version, copied

    def get_version(self, user: User, version_id: uuid.UUID) -> DatasetVersion:
        version = self._datasets.get_version(user.id, version_id)
        if version is None:
            raise AppError(404, "not_found", "Không tìm thấy version")
        return version

    def review_version(self, user: User, version_id: uuid.UUID) -> tuple[DatasetVersion, int]:
        version = self.get_version(user, version_id)
        if version.status == "reviewed":
            raise AppError(409, "conflict", "Version này đã được duyệt")
        count = self._datasets.count_cases(version.id)
        if count == 0:
            raise AppError(422, "validation_error", "Version chưa có test case nào, không thể duyệt")
        version.status = "reviewed"
        version.reviewed_at = datetime.now(timezone.utc)
        self._datasets.commit()
        return version, count

    # ----------------------------------------------------------------------------- test case
    def list_cases(self, user: User, version_id: uuid.UUID, *, question_type, difficulty, limit, offset):
        version = self.get_version(user, version_id)
        return self._datasets.list_cases(version.id, question_type=question_type, difficulty=difficulty, limit=limit, offset=offset)

    def add_case(self, user: User, version_id: uuid.UUID, payload: TestCaseInput) -> EvaluationTestCase:
        version = self._editable_version(user, version_id)
        case = self._build_case(user, version.id, _spec_from_input(payload))
        self._datasets.add_cases([case])
        self._datasets.commit()
        return case

    def update_case(self, user: User, case_id: uuid.UUID, payload: TestCaseInput) -> EvaluationTestCase:
        case, version = self._require_case(user, case_id)
        self._ensure_editable(version)
        fresh = self._build_case(user, version.id, _spec_from_input(payload))
        for field in ("question", "ground_truth_answer", "reference_contexts", "source_note", "question_type", "difficulty", "expected_behavior"):
            setattr(case, field, getattr(fresh, field))
        self._datasets.commit()
        return case

    def delete_case(self, user: User, case_id: uuid.UUID) -> None:
        case, version = self._require_case(user, case_id)
        self._ensure_editable(version)
        self._datasets.delete_case(case)
        self._datasets.commit()

    def import_cases(self, user: User, version_id: uuid.UUID, filename: str | None, content: bytes) -> int:
        """Tất cả hoặc không gì: có bất kỳ dòng lỗi nào thì không ghi gì cả và trả lỗi theo dòng."""
        version = self._editable_version(user, version_id)
        if len(content) > MAX_IMPORT_BYTES:
            raise AppError(413, "file_too_large", "File import tối đa 2 MB")
        try:
            specs, row_errors = load_test_cases(filename or "", content)
        except ValueError as error:
            raise AppError(422, "validation_error", str(error)) from None

        errors = [{"row": e.row, "issue": e.issue} for e in row_errors]
        cases = []
        for spec in specs:
            try:
                cases.append(self._build_case(user, version.id, spec))
            except AppError as error:
                errors.append({"row": spec.row, "issue": error.message})
        if errors:
            raise AppError(422, "validation_error", "File import có lỗi; không test case nào được ghi", sorted(errors, key=lambda e: e["row"]))
        self._datasets.add_cases(cases)
        self._datasets.commit()
        return len(cases)

    # ----------------------------------------------------------------------------- nội bộ
    def _editable_version(self, user: User, version_id: uuid.UUID) -> DatasetVersion:
        version = self.get_version(user, version_id)
        self._ensure_editable(version)
        return version

    @staticmethod
    def _ensure_editable(version: DatasetVersion) -> None:
        if version.status == "reviewed":
            raise AppError(409, "conflict", "Version đã duyệt thì không sửa được; hãy tạo version mới")

    def _require_case(self, user: User, case_id: uuid.UUID):
        found = self._datasets.get_case(user.id, case_id)
        if found is None:
            raise AppError(404, "not_found", "Không tìm thấy test case")
        return found

    def _build_case(self, user: User, version_id: uuid.UUID, spec: TestCaseSpec) -> EvaluationTestCase:
        issues = validate_spec(spec)
        if issues:
            raise AppError(422, "validation_error", "; ".join(issues))
        resolved = []
        for reference in spec.references:
            try:
                resolved.append(self._resolve_reference(user, reference))
            except _ReferenceError as error:
                raise AppError(422, "validation_error", str(error)) from None
        return EvaluationTestCase(
            dataset_version_id=version_id,
            question=spec.question,
            ground_truth_answer=spec.ground_truth_answer,
            reference_contexts=resolved,
            source_note=spec.source_note,
            question_type=spec.question_type,
            difficulty=spec.difficulty,
            expected_behavior=spec.expected_behavior,
        )

    def _resolve_reference(self, user: User, reference: ReferenceSpec) -> dict:
        if reference.document_id:
            try:
                document = self._datasets.ready_document(user.id, uuid.UUID(reference.document_id))
            except ValueError:
                raise _ReferenceError("document_id không hợp lệ") from None
            if document is None:
                raise _ReferenceError("Không tìm thấy tài liệu đã xử lý xong với document_id này")
        else:
            matches = self._datasets.ready_documents_by_filename(user.id, reference.filename or "")
            if not matches:
                raise _ReferenceError(f"Không có tài liệu đã xử lý xong tên {reference.filename}")
            if len(matches) > 1:
                raise _ReferenceError(f"Có nhiều tài liệu tên {reference.filename}; hãy dùng document_id")
            document = matches[0]
        spans = [ChunkSpan(start, end, content) for start, end, content in self._datasets.chunk_spans(user.id, document.id)]
        try:
            start, end, text = locate_quote(spans, reference.quote)
        except ValueError as error:
            raise _ReferenceError(f"{document.filename}: {error}") from None
        return {
            "document_content_hash": document.content_hash,
            "filename": document.filename,
            "char_start": start,
            "char_end": end,
            "text": text,
        }


def _spec_from_input(payload: TestCaseInput) -> TestCaseSpec:
    return TestCaseSpec(
        row=1,
        question=payload.question.strip(),
        ground_truth_answer=(payload.ground_truth_answer or "").strip() or None,
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        expected_behavior=payload.expected_behavior,
        source_note=(payload.source_note or "").strip() or None,
        references=[
            ReferenceSpec(quote=r.quote, filename=r.filename, document_id=str(r.document_id) if r.document_id else None)
            for r in payload.reference_contexts
        ],
    )


def _copy_case(case: EvaluationTestCase, version_id: uuid.UUID) -> EvaluationTestCase:
    return EvaluationTestCase(
        dataset_version_id=version_id,
        question=case.question,
        ground_truth_answer=case.ground_truth_answer,
        reference_contexts=list(case.reference_contexts),
        source_note=case.source_note,
        question_type=case.question_type,
        difficulty=case.difficulty,
        expected_behavior=case.expected_behavior,
    )
