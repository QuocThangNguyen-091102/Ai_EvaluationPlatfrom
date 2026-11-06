"""Ước tính chi phí từ số token và bảng giá trong `configs/models.yaml`.

Nguyên tắc: không đoán giá. Model không có trong bảng giá, hoặc provider không báo số token, thì trả None
("không biết"), không trả 0. Bảng giá phải ghi ngày lấy giá (`as_of`) vì giá đổi theo thời gian.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

_MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class ModelPrice:
    provider: str
    model: str
    input_per_million: Decimal
    output_per_million: Decimal
    currency: str
    as_of: str


class PriceTable:
    def __init__(self, prices: list[ModelPrice]) -> None:
        self._prices = {(p.provider, p.model): p for p in prices}

    def get(self, provider: str, model: str) -> ModelPrice | None:
        return self._prices.get((provider, model))

    def estimate(self, provider: str, model: str, prompt_tokens: int | None, completion_tokens: int | None) -> Decimal | None:
        price = self.get(provider, model)
        if price is None or prompt_tokens is None or completion_tokens is None:
            return None
        cost = (Decimal(prompt_tokens) * price.input_per_million + Decimal(completion_tokens) * price.output_per_million) / _MILLION
        return cost.quantize(Decimal("0.000001"))


def load_price_table(path: str | Path) -> PriceTable:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    prices = []
    for index, entry in enumerate(data.get("prices") or []):
        try:
            price = ModelPrice(
                provider=str(entry["provider"]),
                model=str(entry["model"]),
                input_per_million=Decimal(str(entry["input_per_million"])),
                output_per_million=Decimal(str(entry["output_per_million"])),
                currency=str(entry["currency"]),
                as_of=str(entry["as_of"]),
            )
        except (KeyError, TypeError, ArithmeticError) as error:
            raise ValueError(f"Dòng giá thứ {index + 1} trong bảng giá thiếu hoặc sai trường") from error
        if price.input_per_million < 0 or price.output_per_million < 0:
            raise ValueError(f"Dòng giá thứ {index + 1} có giá âm")
        prices.append(price)
    return PriceTable(prices)
