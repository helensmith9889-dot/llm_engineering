#!/usr/bin/env python3
"""中文注释版：逻辑与标识符保持原文，便于 import 与运行。"""
import ollama
import subprocess
import os
from time import sleep
import json


CONTEXT_FILE = "chat_context.json"

def clear_screen():
    """根据操作系统清除终端屏幕。"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_model_selection():
    """列出可用模型并返回用户选择的模型。"""
    models_resp = ollama.list()
    model_names = {
        num: {"Model": m.model, "Parameters": m.details.parameter_size} 
        for num, m in enumerate(models_resp.models)
    }

    print('Select a model\n_______________________________________')
    for num, model in model_names.items():
        print(f'\n{num}\nModel: {model["Model"]}\nParameters: {model["Parameters"]}')
    
    print('''_______________________________________
NB: All running models except the selected
    one will be closed!!!
_______________________________________''')

    for i in range(6):
        if i == 5:
            print("\n_____TOO MANY INVALID ATTEMPTS_____\n")
            quit()
        try:
            entry = input("\nEnter model number: ")
            model_num = int(entry)
            if model_num not in model_names:
                print('Enter a valid number')
                continue
            return model_names[model_num]["Model"]
        except ValueError:
            print('Enter a valid number')
            continue

def stop_other_models(model_used):
    """停止除当前所选模型之外的所有正在运行的模型。"""
    try:
        running_models = ollama.ps().models
        for model in running_models:
            if model.model != model_used:
                print(f'Closing {model.model}...')
                subprocess.run(["ollama", "stop", model.model])
    except Exception as e:
        pass # Silently fail if ps fails

def load_chat_context():
    """检查现有的聊天上下文，如果用户想要加载它，则返回它。"""
    if os.path.exists(CONTEXT_FILE):
        choice = input(f"\nDetected '{CONTEXT_FILE}'. Load previous chat context? (y/n): ").lower()
        if choice == 'y':
            try:
                with open(CONTEXT_FILE, 'r') as f:
                    messages = json.load(f)
                
                # 不要将“再见”命令加载到活动会话中
                if messages and messages[-1]["content"].lower() == "bye":
                    messages.pop()
                
                return messages
            except Exception as e:
                print(f"Error loading context: {e}")
    return None

def save_chat_context(messages):
    """将聊天上下文保存到 JSON 文件。"""
    try:
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(messages, f, indent=4)
        print(f"\nChat context saved to {CONTEXT_FILE}")
    except Exception as e:
        print(f"Error saving context: {e}")

def start_chat_session(model_used, initial_messages=None):
    """处理聊天交互循环。"""
    print(f'_______________{model_used.upper()}_______________')
    print('\nNB: Enter \"bye\" to exit chat\n'
          '    Enter \"chat_context\" to see the full chat context upto that point\n'
          '    Enter \"stats\" to see session statistics\n'
          '_________________________________________________________________________\n'
          'Loading the model...')

    session_stats = {"prompt_tokens": 0, "response_tokens": 0, "total_gen_time": 0.0, "total_duration": 0.0}
    if initial_messages:
        messages = initial_messages
        if messages:
            last_msg = messages[-1]
            print(f"\n" + "="*20 + " RESUMING SESSION " + "="*20)
            print('Last Message:')
            print(f"[{last_msg['role'].upper()}]: {last_msg['content']}")
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a chat bot. Replies should make sense as natural language. "
                    "Reason yourself to make sure it is in natural language, short and "
                    "concise and should behave snarky"
                )
            },
            {
                "role": "user",
                "content": "Hi assistant."
            }
        ]

    while True:
        try:
            # 仅当最后一条消息来自用户时才触发模型响应
            if messages[-1]["role"] == "user":
                print(f'\n{model_used.upper()}: ', end="", flush=True)
                
                full_content = ""
                stats = {}
                for chunk in ollama.chat(model_used, messages, stream=True):
                    if "message" in chunk:
                        token = chunk["message"]["content"]
                        print(token, end="", flush=True)
                        full_content += token
                    if chunk.get("done"):
                        stats = chunk
                
                print()
                p_tokens, r_tokens = stats.get("prompt_eval_count", 0), stats.get("eval_count", 0)
                gen_t, tot_t = stats.get("eval_duration", 0) / 1e9, stats.get("total_duration", 0) / 1e9
                print(f"\033[2m>> Tokens: In {p_tokens} / Out {r_tokens} | Time: Gen {gen_t:.2f}s / Total {tot_t:.2f}s\033[0m")
                
                session_stats["prompt_tokens"] += p_tokens
                session_stats["response_tokens"] += r_tokens
                session_stats["total_gen_time"] += gen_t
                session_stats["total_duration"] += tot_t

                messages.append({"role": "assistant", "content": full_content})
            
            while True:
                inp = input('\nUSER: ')
                if inp.lower() == "bye":
                    messages.append({"role": "user", "content": inp})
                    return messages

                if inp.lower() == "chat_context":
                    print("\n\n\n" + "="*15 + " CURRENT CHAT CONTEXT " + "="*15)
                    # 跳过初始系统提示和第一个用户提示
                    for msg in messages[2:]:
                        print(f"[{msg['role'].upper()}]: {msg['content']}\n")
                    print("="*52 + "\n\n\n")
                    continue

                if inp.lower() == "stats":
                    print("\n" + "="*15 + " SESSION STATISTICS " + "="*15)
                    print(f"Model: {model_used.upper()}")
                    print(f"Total Prompt Tokens:   {session_stats['prompt_tokens']}")
                    print(f"Total Response Tokens: {session_stats['response_tokens']}")
                    print(f"Total Tokens:          {session_stats['prompt_tokens'] + session_stats['response_tokens']}")
                    print(f"Total Gen Time:        {session_stats['total_gen_time']:.2f}s")
                    print(f"Total Duration:        {session_stats['total_duration']:.2f}s")
                    if session_stats['total_gen_time'] > 0:
                        speed = session_stats['response_tokens'] / session_stats['total_gen_time']
                        print(f"Average Speed:         {speed:.2f} tokens/s")
                    print("="*50 + "\n")
                    continue

                messages.append({"role": "user", "content": inp})
                break
        except KeyboardInterrupt:
            print("\nExiting chat...")
            return messages
        except Exception as e:
            print(f"An error occurred: {e}")
            return messages

def main():
    """脚本的主要入口点。"""
    clear_screen()
    
    # 0. 上下文处理
    initial_context = load_chat_context()

    # 1. 选型
    model_used = get_model_selection()

    final_messages = initial_context
    try:
        # 2.清理其他模型
        stop_other_models(model_used)
        sleep(3)

        # 3. 聊天循环
        clear_screen()
        final_messages = start_chat_session(model_used, initial_context)
        
        # 4. 保存上下文
        if final_messages:
            save_choice = input("\nDo you want to save the chat context? (y/n): ").lower()
            if save_choice == 'y':
                save_chat_context(final_messages)
    finally:
        # 5. 最终清理：停止使用模型
        print(f"\nShutting down {model_used}...")
        subprocess.run(["ollama", "stop", model_used])

if __name__ == "__main__":
    main()