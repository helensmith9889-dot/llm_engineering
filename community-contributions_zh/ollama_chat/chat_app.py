import streamlit as st
from openai import OpenAI
import requests
import datetime

st.set_page_config(
    page_title="Ollama Chat",
)


def get_ollama_models(ollama_url: str):
    # 从 Ollama /api/tags 拉取已安装模型列表
    try:
        resp = requests.get(f"{ollama_url.replace('/v1','')}/api/tags")
        if resp.status_code == 200:
            return [m["name"] for m in resp.json()["models"]]
    except Exception:
        pass
    return ["gemma:2b"]  # 连接失败时的回退模型


def get_ai_response(client: OpenAI, model: str, messages: list):
    # 调用聊天补全，并返回回复文本、用量与原始响应
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    reply = response.choices[0].message.content
    usage = response.usage if hasattr(response, "usage") else None
    return reply, usage, response


st.sidebar.header("Settings")

ollama_url = st.sidebar.text_input(
    "Ollama Server URL",
    value="http://localhost:11434/v1",
    help="Enter the Ollama API URL (default is local)"
)

@st.cache_data
def load_models(url):
    return get_ollama_models(url)

available_models = load_models(ollama_url)
selected_model = st.sidebar.selectbox("Choose a model", available_models)

# 清空当前会话对话
if st.sidebar.button("Clear Conversation"):
    st.session_state.messages = []

# 调试：是否展示原始 API 响应
debug = st.sidebar.checkbox("Show raw response")


if "client" not in st.session_state:
    st.session_state.client = OpenAI(base_url=ollama_url, api_key="ollama")

client = st.session_state.client



st.title("Chat with Ollama via OpenAI API")



if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示历史消息：时间戳 + token 用量
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        # 用小号灰色字显示附加信息
        extra_info = f" {message['time']}"
        if "tokens" in message:
            extra_info += f" | Tokens: {message['tokens']}"
        st.markdown(
            f"<span style='font-size:12px; color:grey;'>{extra_info}</span>",
            unsafe_allow_html=True
        )



user_input = st.chat_input("Type your message...")

if user_input:
    # 保存并展示用户消息（用户侧不计 token）
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": timestamp
    })
    with st.chat_message("user"):
        st.write(user_input)
        st.markdown(f"<span style='font-size:12px; color:grey;'>🕒 {timestamp}</span>", unsafe_allow_html=True)

    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                ai_reply, usage, response = get_ai_response(client, selected_model, st.session_state.messages)
            except Exception as e:
                ai_reply, usage, response = f" Error: {str(e)}", None, None

        # 保存并展示助手回复：时间戳 + tokens
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        token_info = None
        if usage:
            # 合并 prompt 与 completion 的 token 数
            token_info = f"in:{usage.prompt_tokens}, out:{usage.completion_tokens}, total:{usage.total_tokens}"

        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_reply,
            "time": timestamp,
            "tokens": token_info
        })

        st.write(ai_reply)
        extra_info = f" {timestamp}"
        if token_info:
            extra_info += f" |  Tokens used : {token_info}"
        st.markdown(f"<span style='font-size:12px; color:grey;'>{extra_info}</span>", unsafe_allow_html=True)

        # 调试模式：展示原始响应 JSON
        if debug and response is not None:
            st.json(response.model_dump())
