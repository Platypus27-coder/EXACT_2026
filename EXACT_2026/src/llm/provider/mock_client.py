"""
EXACT 2026 — Mock LLM Client (Offline Testing)
Dùng để test pipeline mà không cần tải model thật.
"""
from typing import Any, Type

from pydantic import BaseModel

from src.llm.base import BaseLLM
from src.utils.logger import logger


class _MockResponse:
    """Giả lập response từ LLM."""
    def __init__(self, content: str):
        self.content = content


class _MockLLM:
    """Giả lập ChatLlamaCpp cho testing."""

    def invoke(self, messages, **kwargs) -> _MockResponse:
        """Trả về mock response dựa trên nội dung câu hỏi."""
        if isinstance(messages, str):
            prompt = messages
        elif isinstance(messages, list):
            # Lấy nội dung message cuối cùng
            last = messages[-1]
            prompt = last.content if hasattr(last, "content") else str(last)
        else:
            prompt = str(messages)

        # Mock response cho logic
        if "z3" in prompt.lower() or "logic" in prompt.lower():
            return _MockResponse(
                "```python\nfrom z3 import *\ns = Solver()\n"
                "x = Bool('x')\ns.add(x == True)\n"
                "if s.check() == sat:\n    print('ANSWER: Yes')\n"
                "else:\n    print('ANSWER: Unknown')\n```"
            )
        # Mock response cho physics
        elif "sympy" in prompt.lower() or "physics" in prompt.lower():
            return _MockResponse(
                "```python\nimport sympy as sp\n"
                "result = 0.5 * 100e-6 * 30**2\n"
                "print(f'FINAL_ANSWER: {result} J')\n```"
            )
        # Mock response cho explanation
        else:
            return _MockResponse(
                "ANSWER: Yes\n\n"
                "EXPLANATION: Based on the given premises and solver output, "
                "the answer is Yes."
            )


class _MockStructuredLLM:
    """Giả lập structured output LLM."""
    def __init__(self, schema: Type[BaseModel]):
        self.schema = schema

    def invoke(self, prompt, **kwargs):
        fields = self.schema.model_fields
        mock_data = {}
        for name, field in fields.items():
            if field.annotation == str:
                mock_data[name] = f"Mock {name}"
            elif field.annotation == float:
                mock_data[name] = 0.85
            elif hasattr(field.annotation, "__origin__"):  # List, Optional etc
                mock_data[name] = []
            else:
                mock_data[name] = None
        mock_data["answer"] = "Yes"
        mock_data["explanation"] = "Mock explanation for testing."
        return self.schema(**mock_data)


class MockLLMClient(BaseLLM):
    """Mock client cho offline testing — không cần GPU hay model file."""

    def __init__(self, **kwargs):
        logger.warning("[WARN] MOCK LLM CLIENT — Chế độ offline, không dùng model thật")

    def get_llm(self, **kwargs) -> _MockLLM:
        return _MockLLM()

    def get_structured_llm(self, output_schema: Type[BaseModel]) -> _MockStructuredLLM:
        return _MockStructuredLLM(output_schema)
