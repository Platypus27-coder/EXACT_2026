# GIẢI PHÁP KỸ THUẬT: EXACT 2026 - NEUROSYMBOLIC AI

## 1. Tổng quan Kiến trúc (Neurosymbolic Hybrid)
Giải pháp của chúng tôi kết hợp thế mạnh của hai trường phái Trí tuệ Nhân tạo:
- **Neural Networks (LLMs):** Sử dụng LLM mã nguồn mở (Qwen2.5-7B) để hiểu ngôn ngữ tự nhiên, phân tích ngữ nghĩa câu hỏi và trích xuất thông tin.
- **Symbolic Solvers:** Sử dụng các bộ giải toán học và logic ký hiệu (SymPy, Z3 Theorem Prover) để tính toán chính xác tuyệt đối, loại bỏ hoàn toàn hiện tượng "ảo giác" (hallucination) thường gặp ở các LLM truyền thống.

## 2. Các Thành phần Cốt lõi

### 2.1. Lõi Ngôn ngữ (LLM)
- **Model:** `platypus123/Qwen-Z3-Merged-BTAM17026` (Dựa trên kiến trúc Qwen 7B).
- **Tối ưu hóa phần cứng:**
  - Lượng tử hóa 4-bit (NF4) bằng `BitsAndBytes` để có thể nhồi nhét mô hình vào các GPU có dung lượng VRAM hạn chế (như T4 15GB).
  - Tải mô hình thông minh với `device_map="auto"` và `low_cpu_mem_usage` giúp tự động phân bổ tải trọng khi chạy trên đa GPU (ví dụ: 2x T4 trên Kaggle).
- **Nhiệt độ (Temperature):** Được khóa ở mức `0.0` để đảm bảo tính tất định cao nhất khi sinh mã (Code Generation).

### 2.2. Hệ thống Truy xuất Thông tin (RAG Pipeline)
Hệ thống sử dụng cơ chế Tìm kiếm Lai (Hybrid Search) để tăng cường tri thức cho LLM:
- **Vector Database:** `Qdrant` (Lưu trữ cục bộ để tiết kiệm thời gian kết nối API).
- **Mô hình Nhúng (Embedding):** `BAAI/bge-m3` (Hỗ trợ đa ngôn ngữ và tối ưu cho việc biểu diễn ngữ nghĩa Toán/Lý).
- **Mô hình Xếp hạng lại (Reranker):** `BAAI/bge-reranker-base` (Đảm bảo Top-3 tài liệu đưa vào Prompt là chính xác nhất).
- **Thuật toán tìm kiếm:** Kết hợp BM25 (Tìm kiếm từ khóa) và Dense Retrieval (Tìm kiếm Vector) để không bỏ lót bất kỳ công thức vật lý hay điều luật logic nào.

### 2.3. Trái tim Hệ thống: LangGraph Pipeline
Luồng xử lý (Workflow) được xây dựng tự động hóa hoàn toàn thông qua `LangGraph`:
1. **Phân loại Câu hỏi (Classifier):** Tự động nhận diện câu hỏi là dạng Vật Lý (Physics) hay Logic (Logic).
2. **Kích hoạt RAG:** Truy xuất tài liệu phù hợp từ Vector DB.
3. **Sinh Mã Ký hiệu (Symbolic Code Generation):** LLM đọc ngữ cảnh và tự động sinh ra mã Python (Z3 cho Logic hoặc SymPy cho Vật lý).
4. **Hộp Cát Thực Thi (Sandbox Executor):** Chạy mã Python vừa sinh trong một môi trường an toàn (Subprocess) với giới hạn thời gian (Timeout).
   - Nếu lỗi cú pháp hoặc chạy sai, hệ thống tự động báo lỗi cho LLM và kích hoạt vòng lặp **Iterative Refinement** (Thử lại).
5. **Cơ chế Dự phòng (Fallback):** Nếu bộ giải ký hiệu vẫn thất bại sau nhiều lần thử, luồng sẽ tự động chuyển sang nhánh `Direct` để ép LLM tự nhẩm ra đáp án cuối cùng.

### 2.4. Trình phân tích Đầu ra (Answer Selector & Output Parser)
- Đảm bảo đầu ra luôn tuân thủ nghiêm ngặt định dạng JSON của Ban Tổ Chức (BTC).
- Tự động trích xuất chuỗi Logic bậc 1 (First-Order Logic - `fol`) từ mã nguồn Z3/SymPy.
- Tự động xây dựng chuỗi lý luận (Chain-of-Thought - `cot`) dựa trên các bước tính toán của máy.

## 3. Quản lý Tài nguyên & Khắc phục Nghẽn Cổ Chai
- **OOM (Out Of Memory):** Trên các thiết bị yếu, cấu trúc linh hoạt cho phép đẩy một phần kiến trúc (RAG) xuống tính toán bằng CPU, nhường toàn bộ VRAM cho việc sinh mã của LLM.
- **Threading Bottleneck:** Tối ưu hóa kiến trúc FastAPI (`def solve` vs `async def solve`) tùy thuộc vào cấu hình phần cứng để tránh tranh chấp luồng CPU khi truy vấn dữ liệu.

## 4. Cách triển khai (Deployment)
- Mã nguồn chạy độc lập, không phụ thuộc Database ngoại vi.
- Có thể khởi chạy chỉ bằng 1 dòng lệnh thông qua `uvicorn` trên máy tính cá nhân, Google Colab hoặc Kaggle Notebook.
- Mở luồng Internet (Tunnel) linh hoạt thông qua `Ngrok` để đáp ứng yêu cầu chấm điểm tự động từ máy chủ của BTC.
