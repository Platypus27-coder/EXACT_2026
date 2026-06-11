# Fine-Tuning Qwen2.5-7B on Google Colab (Unsloth)

> [!TIP]
> This notebook is optimized for **Google Colab's Free T4 GPU (15GB VRAM)**. We use the **Unsloth** library to speed up training by 2x and reduce memory usage by 60%, allowing a 7B model to be trained efficiently.

To use this, open [Google Colab](https://colab.research.google.com/), create a new notebook, ensure you are connected to a T4 GPU (`Runtime > Change runtime type > T4 GPU`), and paste the following cells in order.

---

### Cell 1: Install Dependencies
First, we install Unsloth and other necessary libraries for 4-bit quantization and LoRA fine-tuning.

```python
%%capture
# Cài đặt Unsloth và thư viện cần thiết
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps trl peft accelerate bitsandbytes
```

---

### Cell 2: Load the Base Model (4-bit)
We load the pre-quantized 4-bit version of Qwen2.5-7B-Instruct. This saves massive amounts of RAM and VRAM, ensuring Colab doesn't crash.

```python
from unsloth import FastLanguageModel
import torch

max_seq_length = 1536 # Giảm từ 2048 xuống 1536 để tiết kiệm VRAM
dtype = None          # None để tự động chọn (Float16 cho T4)
load_in_4bit = True   # Bật 4-bit để vừa với VRAM 15GB của Colab

# Tải model và tokenizer
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Qwen2.5-7B-Instruct", # Bản gốc 7B Instruct
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)
```

---

### Cell 3: Apply LoRA Adapters
We inject LoRA (Low-Rank Adaptation) adapters. This allows us to train only ~1-2% of the model's weights, making fine-tuning possible on a single GPU.

```python
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # Rank: 16 là mức tiêu chuẩn tốt nhất cho code generation
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 32,
    lora_dropout = 0, 
    bias = "none",    
    use_gradient_checkpointing = "unsloth", # Tối ưu hóa bộ nhớ siêu việt của Unsloth
    random_state = 3407,
    use_rslora = False,
    loftq_config = None,
)
```

---

### Cell 4: Load and Format the Dataset
Upload your `train_code_final.jsonl` file to the Colab environment (drag and drop it into the files pane on the left). We will use Unsloth's built-in Chat Template formatter.

```python
from datasets import load_dataset
from unsloth.chat_templates import get_chat_template

# Thiết lập Chat Template chuẩn của Qwen2.5
tokenizer = get_chat_template(
    tokenizer,
    chat_template = "qwen-2.5", 
    mapping = {"role" : "role", "content" : "content", "user" : "user", "assistant" : "assistant"}
)

def formatting_prompts_func(examples):
    convos = examples["conversations"]
    texts = [tokenizer.apply_chat_template(convo, tokenize = False, add_generation_prompt = False) for convo in convos]
    return { "text" : texts, }

# Tải file data bạn vừa up lên Colab
dataset = load_dataset("json", data_files="train_code_final.jsonl", split="train")

# Chuẩn hóa dữ liệu
dataset = dataset.map(formatting_prompts_func, batched = True,)
```

---

### Cell 5: Configure and Run the Trainer
Set up the `SFTTrainer`. We use `batch_size = 2` and `gradient_accumulation_steps = 4` to simulate a batch size of 8, which fits perfectly in the T4's 15GB VRAM.

```python
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import is_bfloat16_supported

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, # Khuyến nghị False khi dùng chat template
    args = TrainingArguments(
        per_device_train_batch_size = 1,      # GIẢM XUỐNG 1 ĐỂ TRÁNH LỖI OUT OF MEMORY
        gradient_accumulation_steps = 8,      # TĂNG LÊN 8 để bù lại batch_size = 1 (1x8 = 8)
        warmup_steps = 5,
        max_steps = 150,                      # Số bước huấn luyện (Tăng lên 300-500 nếu muốn học kỹ hơn toàn bộ dataset)
        # num_train_epochs = 1,               # Dùng epoch thay cho max_steps nếu muốn train toàn bộ data 1 vòng
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 10,
        optim = "adamw_8bit",                 # Optimizer 8-bit tiết kiệm VRAM
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

# Bắt đầu quá trình huấn luyện!
trainer_stats = trainer.train()
```

---

### Cell 6: Save the Trained Model & Push to Hub
Once training is complete, save the LoRA adapters locally or push them directly to your HuggingFace account.

> [!IMPORTANT]
> Replace `"your_huggingface_token"` with your actual Write-access token from HuggingFace, and `"your_username/EXACT-Qwen2.5-Z3-Code"` with your desired repository name.

```python
# Lưu mô hình (LoRA adapters) cục bộ trên Colab
model.save_pretrained("lora_model") 
tokenizer.save_pretrained("lora_model")

# Hoặc PUSH thẳng lên HuggingFace Hub (khuyến nghị để tải về máy sau này)
huggingface_token = "your_huggingface_token" # Điền token của bạn vào đây
repo_name = "platypus123/EXACT-Qwen-Z3-Code" # Đổi tên cho phù hợp

model.push_to_hub(repo_name, token = huggingface_token)
tokenizer.push_to_hub(repo_name, token = huggingface_token)
```

### Cách dùng model sau khi huấn luyện xong trên máy Local:
Trên máy của bạn, hãy cập nhật file `config/setting.yaml`:
- Đổi `model_id` thành tên repo bạn vừa push lên (ví dụ: `"platypus123/EXACT-Qwen-Z3-Code"`)
- Bật `load_in_4bit: true`
- Hệ thống HuggingFace Pipeline (`hf_client.py`) sẽ tự động tải base model và ghép LoRA weights này vào để chạy!
