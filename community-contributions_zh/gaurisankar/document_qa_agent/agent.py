import transcript_parser
from config import SYSTEM_PROMPT
from llm import create_client, get_response


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def welcome_user():
    """向用户打印欢迎消息。"""
    print("Welcome to the Document Q&A Agent!")
    print("This Agent can answer questions about text files.")
    print("You can ask questions about the transcript, generate a summary, or generate content using the same.")
    print("Type 'exit' to quit.")
    print()


# ---------------------------------------------------------------------------
# 代理核心
# ---------------------------------------------------------------------------
def run_agent(raw_transcript: str):
    """运行主问答循环。保持对话记忆。

    参数：
        raw_transcript (str)：从文档中提取的全文。"""
    client = create_client()

    # 对话历史记录——随着多回合记忆的每次回合而增长
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + raw_transcript}
    ]

    while True:
        user_query = input("\nAsk anything or type exit to quit:\n> ").strip()

        if user_query.lower() == "exit":
            print("Goodbye!")
            break

        if not user_query:
            continue

        messages.append({"role": "user", "content": user_query})

        try:
            response_text = get_response(messages, client)
            print(f"\nAgent: {response_text}")
            messages.append({"role": "assistant", "content": response_text})

        except Exception as e:
            print(f"\n[Error] - Unable to generate response :(\nDetails: {e}")
            messages.pop()  # Remove failed query so history stays consistent


# ---------------------------------------------------------------------------
# 切入点
# ---------------------------------------------------------------------------
def main():
    welcome_user()

    raw_transcript = transcript_parser()
    run_agent(raw_transcript)


if __name__ == "__main__":
    main()
