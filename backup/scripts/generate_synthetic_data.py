import json
import csv
import os
import argparse

# Cấu hình
MOCK_MODE = True  # Để True để chạy test định dạng, False để gọi API thật
OUTPUT_FILE = "data/synthetic_dataset.jsonl"
LOGIC_FILE = "Logic_Based_Educational_Queries.json"
PHYSICS_FILE = "Physics_Problems_Text_Only.csv"

# Nếu chạy thật, hãy điền API Key vào đây (hoặc dùng biến môi trường)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

def call_llm(system_prompt, user_prompt):
    """Giả lập gọi API hoặc gọi thật tùy vào MOCK_MODE"""
    if MOCK_MODE:
        # Giả lập phản hồi của AI cho mục đích test format
        return (
            "<think>\n"
            "This is a mocked thinking process to test the output format.\n"
            "</think>\n"
            "<answer>\n"
            "```python\n"
            "import sympy as sp\n"
            "# MOCK CODE\n"
            "print('FINAL_ANSWER: 10')\n"
            "```\n"
            "</answer>"
        )
    else:
        # Gọi OpenAI API thật
        import openai
        openai.api_key = OPENAI_API_KEY
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Lỗi API: {e}")
            return None

def process_logic_data(limit=2):
    results = []
    print(f"Processing {limit} Logic questions...")
    with open(LOGIC_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    system_prompt = "You are an expert in Formal Logic. Solve the problem using Python Z3 solver. Output thinking in <think> and code in <answer> block."
    
    for i, item in enumerate(data[:limit]):
        # Gom các mệnh đề và câu hỏi lại thành 1 chuỗi
        premises = "\n".join(item.get("premises-NL", []))
        question = item.get("questions", [""])[0]
        user_prompt = f"Premises:\n{premises}\n\nQuestion:\n{question}"
        
        ai_response = call_llm(system_prompt, user_prompt)
        if ai_response:
            results.append({
                "messages": [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": ai_response}
                ]
            })
    return results

def process_physics_data(limit=2):
    results = []
    print(f"Processing {limit} Physics questions...")
    with open(PHYSICS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit: break
            
            question = row.get("question", "")
            system_prompt = "You are a Physics expert. Solve the problem using Python SymPy. Output thinking in <think> and code in <answer> block."
            
            ai_response = call_llm(system_prompt, question)
            if ai_response:
                results.append({
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": ai_response}
                    ]
                })
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--real', action='store_true', help='Chạy gọi API thật (tắt Mock)')
    parser.add_argument('--limit', type=int, default=2, help='Số lượng câu test mỗi loại')
    args = parser.parse_args()

    global MOCK_MODE
    if args.real:
        MOCK_MODE = False
        print("[!] DANG CHAY CHE DO GOI API THAT (REAL MODE) [!]")
    else:
        print("[!] DANG CHAY CHE DO TEST (MOCK MODE) - Khong ton tien API [!]")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    all_data = []
    all_data.extend(process_logic_data(args.limit))
    all_data.extend(process_physics_data(args.limit))
    
    # Ghi ra file JSONL chuẩn format Qwen
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"\n[OK] Da luu {len(all_data)} mau data vao {OUTPUT_FILE}")
    print("-> Format mau:")
    print(json.dumps(all_data[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
