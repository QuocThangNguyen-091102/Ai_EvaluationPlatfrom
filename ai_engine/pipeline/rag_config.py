from dataclasses import dataclass


@dataclass(frozen=True)
class RAGConfig:
    """Cấu hình cho một lần chạy pipeline. Khớp các trường của bảng model_configurations."""

    top_k: int
    temperature: float
    prompt_version: str
    # "extractive" nghĩa là không gọi LLM: trả các đoạn liên quan nhất kèm nguồn.
    llm_provider: str
    llm_model: str
    max_answer_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k phải ít nhất là 1")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature phải trong khoảng 0 đến 2")

    @property
    def uses_llm(self) -> bool:
        return self.llm_provider != EXTRACTIVE_PROVIDER


EXTRACTIVE_PROVIDER = "extractive"
EXTRACTIVE_MODEL = "top-passages"
