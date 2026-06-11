# EXACT 2026 — He thong AI giai bai toan Logic & Vat ly

He thong Agentic AI xay dung cho cuoc thi **EXACT 2026** (lan thu 2), su dung phuong phap **Neurosymbolic Hybrid** — ket hop LLM ma nguon mo voi cac bo giai ky hieu (Z3, SymPy) de tra loi chinh xac cac cau hoi giao duc.

## Muc tieu

- Tra loi cau hoi suy luan logic (quy che dao tao) — **Type 1**
- Giai bai toan vat ly STEM (mach dien, tu dien, luc Coulomb...) — **Type 2**
- Cung cap loi giai thich chi tiet cho tung cau tra loi

## Rang buoc cuoc thi

- Chi duoc dung LLM ma nguon mo, toi da **8 ty tham so**
- Cam su dung GPT, Claude, Gemini (model dong)
- API endpoint phai tra ket qua trong toi da **60 giay**
- Output phai co cau truc JSON (answer + explanation)

## Cong nghe su dung

| Thanh phan | Cong nghe |
|---|---|
| LLM | DeepSeek-R1-0528-Qwen3-8B (tu dong tai tu HuggingFace) |
| Quantization | BitsAndBytes 4-bit NF4 |
| Logic Solver | Z3 Theorem Prover (Microsoft) |
| Math Solver | SymPy |
| Pipeline | LangGraph (LangChain) |
| RAG | LlamaIndex + Qdrant + BM25 Hybrid Search |
| Embedding | BAAI/bge-m3 |
| Reranker | BAAI/bge-reranker-base |
| API | FastAPI + Uvicorn |

## Cau truc thu muc

```
EXACT_2026/
├── config/
│   ├── setting.yaml          # Cau hinh chinh (model, timeout, RAG...)
│   └── logging.yaml          # Cau hinh logging
│
├── data/
│   ├── raw data/             # Du lieu goc (CSV, JSON)
│   └── official data/        # Du lieu da xu ly (JSONL cho fine-tuning)
│
├── src/
│   ├── api/                  # FastAPI endpoint (POST /solve)
│   ├── agent/                # LangGraph pipeline
│   │   ├── nodes/            # Cac node xu ly
│   │   ├── state.py          # Dinh nghia trang thai pipeline
│   │   ├── graph.py          # Luong xu ly chinh
│   │   └── schema.py         # Pydantic schema cho request/response
│   ├── llm/                  # Quan ly LLM (factory, provider)
│   ├── prompt/               # Prompt templates (Z3, SymPy, Explanation...)
│   ├── retrieval/            # RAG engine (vector_db, hybrid search)
│   ├── sandbox/              # Chay code Z3/SymPy an toan
│   └── utils/                # Logger, output parser
│
├── scripts/                  # Script tien ich
├── logs/                     # File log tu dong tao
├── storage/                  # Vector DB (Qdrant) tu dong tao
├── requirements.txt
├── solution_description.md   # Mo ta giai phap (nop bai)
└── README.md
```

## Luong xu ly (Pipeline)

```
Cau hoi JSON --> Phan loai (co premises? logic : physics)
                      |
          +-----------+-----------+
          |                       |
       LOGIC                   PHYSICS
          |                       |
      Z3 Solver              RAG (tim cong thuc)
      (retry x1)                  |
          |                  SymPy Solver
     Thanh cong?             (retry x1)
      /       \                   |
    Co        Khong          Thanh cong?
     |          |             /       \
     |     LLM Direct       Co       Khong
     |      (fallback)       |          |
     |          |            |     LLM Direct
     +-----+---+            +-----+----+
           |                      |
     Answer Selector        Answer Selector
           |                      |
           +----------+-----------+
                      |
               JSON Response
          {answer, explanation}
```

**Diem noi bat:**
- Solver chay truoc, LLM Direct chi goi khi solver that bai (tiet kiem thoi gian)
- Neu Solver loi, tu dong sua code va thu lai (1 lan)
- Kien thuc vat ly tu dong nap vao Vector DB lan dau chay
- Toi uu cho GPU don (T4), dam bao <= 60 giay

---

## Huong dan cai dat

### Buoc 1: Tao moi truong Conda

```bash
conda create -n exact-env python=3.11 -y
conda activate exact-env
```

### Buoc 2: Cai dat thu vien

```bash
pip install -r requirements.txt
```

**Luu y:**
- Thu vien `bitsandbytes` chi ho tro GPU NVIDIA (CUDA). Tren Colab thi da co san.
- `torch` can phien ban tuong thich voi CUDA. Xem: https://pytorch.org/get-started/locally/

### Buoc 3: Cau hinh model (tuy chon)

Mac dinh he thong se tu dong tai model `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` tu HuggingFace khi chay lan dau. Neu muon doi model, sua file `config/setting.yaml`:

```yaml
llm:
  model_id: "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"   # Doi model o day
  load_in_4bit: true                                    # 4-bit quantization
```

**Khong can tai model thu cong** — he thong tu dong tai va cache.

### Buoc 4: Tao file .env (tuy chon)

```bash
copy .env.example .env
```

---

## Huong dan chay

### Cach 1: Chay API Server (dung cho nop bai thi)

```bash
conda activate exact-env
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Lan dau chay se mat vai phut de tai model. Cac lan sau se nhanh hon (dung cache).

Kiem tra trang thai:
```bash
curl http://localhost:8000/health
```

### Cach 2: Goi API bang Python

```python
import requests

# Bai toan Logic (Type 1)
response = requests.post("http://localhost:8000/solve", json={
    "question": "Sinh vien A co duoc pass mon khong?",
    "premises": [
        "Sinh vien A vang thi thuc hanh",
        "Dieu 13: Vang thi thuc hanh thi khong dat mon"
    ]
})
print(response.json())

# Bai toan Vat ly (Type 2)
response = requests.post("http://localhost:8000/solve", json={
    "question": "Tinh nang luong tu dien khi C = 100 uF va U = 30 V"
})
print(response.json())
```

### Cach 3: Goi pipeline truc tiep (khong qua API)

```python
from src.agent.graph import run_pipeline

result = run_pipeline(
    question="Sinh vien A co duoc pass mon khong?",
    premises=["Sinh vien A vang thi thuc hanh", "Dieu 13: Vang thi thuc hanh thi khong dat"]
)
print(result)
```

### Cach 4: Che do Mock (test offline, khong can model)

```bash
# Windows PowerShell
$env:USE_MOCK_LLM="true"
uvicorn src.api.main:app --port 8000
```

---

## Cau hinh

Toan bo cau hinh nam trong file `config/setting.yaml`:

| Tham so | Mo ta | Gia tri mac dinh |
|---|---|---|
| `llm.model_id` | Model ID tren HuggingFace | `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` |
| `llm.temperature` | Nhiet do sinh text (0 = deterministic) | `0.0` |
| `llm.max_new_tokens` | So token toi da LLM sinh ra | `1024` |
| `llm.load_in_4bit` | Bat 4-bit quantization | `true` |
| `pipeline.global_timeout` | Timeout tong cho pipeline (giay) | `55` |
| `pipeline.solver_timeout` | Timeout cho moi lan chay solver | `10` |
| `pipeline.max_retry` | So lan retry khi solver loi | `1` |
| `retrieval.top_k` | So candidates ban dau cho RAG | `10` |
| `retrieval.rerank_top_n` | So ket qua sau rerank | `3` |

---

## API Reference

### POST /solve

**Request:**
```json
{
    "question": "Cau hoi can giai",
    "premises": ["Gia thiet 1", "Gia thiet 2"],
    "type": "logic"
}
```

`premises` va `type` la tuy chon.

**Response:**
```json
{
    "answer": "No",
    "explanation": "Theo Dieu 13, sinh vien vang thi thuc hanh...",
    "confidence": 0.95,
    "task_type": "logic",
    "solver_used": "z3"
}
```

### GET /health

```json
{
    "status": "ok",
    "project": "EXACT 2026",
    "version": "2.0.0"
}
```

---

## Chay tren Google Colab

1. Upload folder `EXACT_2026/` len Colab (hoac clone tu GitHub)
2. Chay `pip install -r requirements.txt`
3. Chay pipeline — model tu dong tai, khong can thao tac gi them

---

## Ghi chu

- Model tu dong tai tu HuggingFace lan dau va duoc cache lai
- Kien thuc vat ly tu dong nap vao Vector DB lan dau chay (khong can chay script rieng)
- Log chi tiet duoc ghi vao `logs/exact_2026.log`
- Vector DB (Qdrant) luu tai `storage/qdrant_storage/`
- Du lieu fine-tuning o `data/official data/` da san sang dung
- File `solution_description.md` mo ta giai phap (nop bai thi)
