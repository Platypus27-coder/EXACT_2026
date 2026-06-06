import json
import os
import sys
import time
import re

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import settings
from src.utils.logger import logger

def parse_user_content(content: str):
    """Extract question and premises from train.jsonl content."""
    premises = []
    is_logic = "[LOGIC PROBLEM]" in content
    
    if is_logic and "Premises:" in content:
        parts = content.split("Question:")
        question = parts[-1].strip()
        premise_section = parts[0].split("Premises:")[1]
        for line in premise_section.split("\n"):
            line = line.strip()
            if line and re.match(r"^\d+\.", line):
                premise_text = re.sub(r"^\d+\.\s*", "", line)
                premises.append(premise_text)
    else:
        question = content.replace("[PHYSICS PROBLEM]", "").strip()
        
    return question, premises

def process_dataset():
    input_file = "data/sft_dataset/train.jsonl"
    output_file = "data/sft_dataset/train_code.jsonl"
    
    logger.info(f"Starting synthetic data generation. Reading from {input_file}")
    
    if settings.llm.model_id not in ["Qwen/Qwen2.5-7B-Instruct", "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"]:
        logger.warning(f"WARNING: You are using model_id = {settings.llm.model_id}.")
        logger.warning("Please revert to Qwen/Qwen2.5-7B-Instruct before running this to ensure proper code generation!")
        time.sleep(5)
        
    success_count = 0
    fail_count = 0
    
    # IMPORT AND INSTANTIATE OUTSIDE THE LOOP! (FAST + DUMB + BATCH)
    from src.llm.factory import LLMFactory
    from src.utils.output_parser import extract_code_block
    from langchain_core.messages import SystemMessage, HumanMessage
    from src.prompt import Z3_SYSTEM_PROMPT, PHYSICS_SYSTEM_PROMPT
    
    logger.info("Initializing LLM client...")
    llm = LLMFactory.create_client(purpose="code").get_llm()
    
    BATCH_SIZE = 16
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        lines = fin.readlines()
        total = len(lines)
        
        for i in range(0, total, BATCH_SIZE):
            batch_lines = lines[i:i+BATCH_SIZE]
            logger.info(f"--- Processing Batch {i//BATCH_SIZE + 1} (Items {i+1} to {min(i+BATCH_SIZE, total)})/{total} ---")
            
            batch_prompts = []
            batch_data = []
            
            for idx, line in enumerate(batch_lines):
                data = json.loads(line)
                conversations = data["conversations"]
                
                user_msg = next((msg for msg in conversations if msg["role"] == "user"), None)
                assistant_msg = next((msg for msg in conversations if msg["role"] == "assistant"), None)
                if not user_msg or not assistant_msg:
                    continue
                    
                question, premises = parse_user_content(user_msg["content"])
                
                # Extract the original ground-truth answer from the assistant message
                original_answer_match = re.search(r"<answer>\s*(.*?)\s*</answer>", assistant_msg["content"], re.DOTALL)
                original_answer = original_answer_match.group(1).strip() if original_answer_match else "Unknown"
                
                is_logic = bool(premises)
                sys_prompt = Z3_SYSTEM_PROMPT if is_logic else PHYSICS_SYSTEM_PROMPT
                
                if is_logic:
                    premises_text = "\n".join([f"- {p}" for p in premises])
                    user_prompt = f"Premises:\n{premises_text}\n\nLogic Problem:\n{question}\n\nTranslate the logic problem above into Python Z3 code."
                else:
                    user_prompt = f"Physics Problem:\n{question}\n\nGenerate Python code using sympy to solve the physics problem above."
                
                batch_prompts.append([
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=user_prompt),
                ])
                batch_data.append({
                    "conversations": conversations,
                    "assistant_msg": assistant_msg,
                    "original_answer": original_answer
                })
                
            if not batch_prompts:
                continue
                
            try:
                # 1. LLM Generate in BATCH!
                response_result = llm.generate(batch_prompts)
                
                for j, generations in enumerate(response_result.generations):
                    response_content = generations[0].text
                    if hasattr(generations[0], 'message'):
                        response_content = generations[0].message.content
                        
                    generated_code = extract_code_block(response_content) or response_content.strip()
                    
                    item_data = batch_data[j]
                    conversations = item_data["conversations"]
                    assistant_msg = item_data["assistant_msg"]
                    original_answer = item_data["original_answer"]
                    
                    # 2. NO EXECUTION! Just inject the code and keep the ground-truth answer!
                    if generated_code:
                        new_content = f"<think>\nTranslating to formal logic/physics and solving via SymPy/Z3...\n</think>\n```python\n{generated_code.strip()}\n```\n<answer>\n{original_answer}\n</answer>"
                        assistant_msg["content"] = new_content
                        success_count += 1
                    else:
                        fail_count += 1
                        logger.warning(f"Item failed to generate valid code. Kept original.")
                    
                    fout.write(json.dumps({"conversations": conversations}, ensure_ascii=False) + "\n")
                    
                fout.flush()
                
            except Exception as e:
                logger.error(f"Error on Batch {i//BATCH_SIZE + 1}: {e}")
                fail_count += len(batch_data)
                for item_data in batch_data:
                    fout.write(json.dumps({"conversations": item_data["conversations"]}, ensure_ascii=False) + "\n")
                fout.flush()
                
    logger.info(f"Done! Saved to {output_file}")
    logger.info(f"Successfully generated code for {success_count}/{total} items.")
    
if __name__ == "__main__":
    process_dataset()
