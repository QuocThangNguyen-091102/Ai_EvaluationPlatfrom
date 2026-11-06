# Import mọi model để Base.metadata biết đầy đủ các bảng (Alembic dựa vào đó).
from app.models.chat import ChatMessage, ChatSession
from app.models.dataset import DatasetVersion, EvaluationDataset, EvaluationTestCase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.evaluation import EvaluationResult, EvaluationRun, MetricResult
from app.models.model_config import ModelConfiguration
from app.models.retrieved_context import RetrievedContext
from app.models.security_test import SecurityTestCase, SecurityTestResult, SecurityTestRun
from app.models.user import User

__all__ = [
    "ChatMessage",
    "ChatSession",
    "DatasetVersion",
    "Document",
    "DocumentChunk",
    "EvaluationDataset",
    "EvaluationResult",
    "EvaluationRun",
    "EvaluationTestCase",
    "MetricResult",
    "ModelConfiguration",
    "RetrievedContext",
    "SecurityTestCase",
    "SecurityTestResult",
    "SecurityTestRun",
    "User",
]
