"""
EXACT 2026 — HuggingFace Client
Tai model tu dong tu HuggingFace Hub, ho tro 4-bit quantization.
Thay the LlamaCpp client — khong can tai GGUF thu cong.
"""
import torch
from typing import Any, Type

from pydantic import BaseModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

from src.core.config import settings
from src.llm.base import BaseLLM
from src.utils.logger import logger


class HuggingFaceClient(BaseLLM):
    """Client cho model HuggingFace — tu dong tai va load model.

    Khi khoi tao lan dau, model se duoc tai tu HuggingFace Hub.
    Cac lan sau se dung cache (khong tai lai).
    """

    _instance = None  # Singleton — chi load model 1 lan

    def __init__(
        self,
        model_id: str = None,
        temperature: float = 0.0,
        max_new_tokens: int = None,
        load_in_4bit: bool = None,
    ):
        self.model_id = model_id or settings.llm.model_id
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens or settings.llm.max_new_tokens
        self.load_in_4bit = load_in_4bit if load_in_4bit is not None else settings.llm.load_in_4bit

        self._llm = None
        self._chat_model = None

    def _load_model(self):
        """Load model va tokenizer (chi chay 1 lan, sau do dung cache)."""
        if self._chat_model is not None:
            return

        logger.info(f"Dang tai model: {self.model_id} ...")
        logger.info("(Lan dau se tai tu HuggingFace, cac lan sau dung cache)")

        # Cau hinh quantization 4-bit
        kwargs = {
            "device_map": "auto",           # Tự động chia tải ra nhiều GPU (rất tốt cho Kaggle 2x T4)
            "trust_remote_code": True,
            "dtype": torch.float16,         # Sửa cảnh báo torch_dtype is deprecated
            "low_cpu_mem_usage": True,      # Bắt buộc để không bị sập RAM thường (12GB) của Colab
        }
        
        if self.load_in_4bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            logger.info("Su dung 4-bit quantization (NF4)")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=True,
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load model trực tiếp vì model đã được Merge nguyên khối (không dùng LoRA nữa)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            **kwargs
        )

        # Tao pipeline
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,              # Deterministic (temperature=0)
            repetition_penalty=1.1,       # Tranh lap lai
            pad_token_id=tokenizer.eos_token_id,
            return_full_text=False,
        )

        # Wrap cho LangChain
        self._llm = HuggingFacePipeline(pipeline=pipe)
        self._chat_model = ChatHuggingFace(llm=self._llm)

        logger.info(f"[OK] Model da san sang: {self.model_id}")

    def get_llm(self, **kwargs) -> ChatHuggingFace:
        """Tra ve ChatHuggingFace instance (tu dong load neu chua co).

        Returns:
            Chat model san sang goi .invoke()
        """
        self._load_model()
        return self._chat_model

    def get_structured_llm(self, output_schema: Type[BaseModel]) -> Any:
        """Tra ve LLM da bind voi Pydantic schema.

        Note: Voi model 8B, nen dung output_parser.py (regex) thay the.

        Args:
            output_schema: Pydantic model class.

        Returns:
            Model instance enforcing output schema.
        """
        self._load_model()
        return self._chat_model.with_structured_output(output_schema)
