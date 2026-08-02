"""
第一周练习：用 YouTube 字幕 API 拉取视频文稿，再调用 OpenAI 生成摘要。

小白说明：
1. youtube_transcript_api 获取字幕
2. OpenAI 根据字幕做摘要（本例以 RCB 球迷口吻）
3. 运行前请在 .env 中配置 OPENAI_API_KEY
"""

# 使用 youtube_transcript_api 获取视频字幕
# 使用 openai 生成视频摘要
# I have used the youtube_transcript_api to get the transcript of the video
# I have used the openai to get the summary of the video

from openai import OpenAI
from dotenv import load_dotenv
import os
from youtube_transcript_api import YouTubeTranscriptApi

# 加载 .env 中的环境变量
load_dotenv(override=True)
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()
api = YouTubeTranscriptApi()
# 目标 YouTube 视频 ID
video_id = "y8AXgTBdY5E"
# 拉取印地语（hi）自动生成字幕并拼接成文本
transcript = (
    api.list(video_id)
    .find_generated_transcript(["hi"])
    .fetch()
)
text = " ".join([t.text for t in transcript])

# 调用模型生成摘要（系统人设与用户内容保持原文，勿改）
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "i want you think like pure RCB fan"},
        {"role": "user", "content": "create the summary in english in for this news" + text}
    ]
)
print(response.choices[0].message.content)
