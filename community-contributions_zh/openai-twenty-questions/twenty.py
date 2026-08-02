import openai
import os
import time

# openai.api_key = os.getenv("OPENAI_API_KEY")
# openai.api_key = "<<Your Open AI Key here>>"

# 可用模型："gpt-4o"、"gpt-4-turbo" 或 "gpt-3.5-turbo"；双方都用 "gpt-4o" 或 "gpt-4o-mini"
MODEL = "gpt-4o-mini"

def call_chatgpt(messages):
    # 调用 ChatCompletion，返回助手文本
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message["content"].strip()

# 步骤 1：出题者选定秘密物品
thinker_messages = [
    {"role": "system", "content": "You are playing 20 Questions. Think of an object or thing and just one word. Keep it secret and reply only with: 'I have thought of something. Let's begin.'"},
]
thinker_reply = call_chatgpt(thinker_messages)
print("Thinker:", thinker_reply)

# 模拟用：向出题者询问真实物品（真游戏中应对猜测者隐藏）
reveal_object_prompt = [
    {"role": "system", "content": "You are playing 20 Questions. Think of an object or thing and just one word. Now tell me (just for logging) what you are thinking of. Reply only with the thing."}
]
object_answer = call_chatgpt(reveal_object_prompt)
print("🔒 Secret Object:", object_answer)

# 步骤 2：猜测者开始提问
guesser_messages = [
    {"role": "system", "content": f"You are playing 20 Questions. Ask yes/no questions to figure out what the object is. Do not repeat questions. The object is kept secret by the other player. Begin by asking your first question."},
]

# 记录问答历史
history = []
q_count = 1

for i in range(1, 11):
    print(f"\n🔄 Round {q_count}")
    q_count += 1
    # 猜测者提问
    question = call_chatgpt(guesser_messages)
    print("Guesser:", question)
    history.append(("Guesser", question))

    # 出题者回答（是/否）
    thinker_round = [
        {"role": "system", "content": f"You are playing 20 Questions. The secret object is: {object_answer}."},
        {"role": "user", "content": f"The other player asked: {question}. Respond only with 'Yes', 'No', or 'I don't know'."}
    ]
    answer = call_chatgpt(thinker_round)
    print("Thinker:", answer)
    history.append(("Thinker", answer))

    # 将问答写入猜测者对话历史
    guesser_messages.append({"role": "assistant", "content": question})
    guesser_messages.append({"role": "user", "content": answer})


    print(f"\n🔄 Round {q_count}")
    q_count += 1
    # 检查猜测者是否要直接猜答案
    guess_check_prompt = guesser_messages + [
        {"role": "user", "content": "Based on the answers so far, do you want to guess? If yes, say: 'Is it <guess>?'. If not, ask the next yes/no question."}
    ]
    next_move_question = call_chatgpt(guess_check_prompt)
    print("Guesser next move:", next_move_question)
    history.append(("Guesser", next_move_question))

    if next_move_question.lower().startswith("is it a"):
        # 出题者核验猜测
        guess = next_move_question[8:].strip(" ?.")
        guess = next_move_question[8:].strip(" ?")

        if guess.lower() == object_answer.lower():
            print("Guesser guessed correctly!")
            break
    # 出题者对下一步动作作答（是/否）
    thinker_round = [
        {"role": "system", "content": f"You are playing 20 Questions. The secret object is: {object_answer}."},
        {"role": "user", "content": f"The other player asked: {next_move_question}. Respond only with 'Yes', 'No', or 'I don't know'."}
    ]
    answer = call_chatgpt(thinker_round)
    print("Thinker next move:", answer)
    history.append(("Thinker", answer))

    # 将本轮写入猜测者历史
    guesser_messages.append({"role": "assistant", "content": next_move_question})
    guesser_messages.append({"role": "user", "content": answer})

    # 为下一轮做准备
    guesser_messages.append({"role": "assistant", "content": next_move_question})
    question = next_move_question

else:
    print("❌ Guesser used all 20 questions without guessing correctly.")
