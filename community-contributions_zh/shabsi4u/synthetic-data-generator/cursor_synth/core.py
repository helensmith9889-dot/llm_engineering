"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
"""
Minimal core classes:
  - TemplateRegistry
  - PromptEngine
  - HFClient
  - Validator
  - Generator
Keep deliberately small and synchronous (httpx sync client) for local dev.
"""

import os
import json
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from jsonschema import validate as jsonschema_validate, ValidationError

from .utils import safe_json_load

load_dotenv()

DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "templates"

class TemplateRegistry:
    def __init__(self, templates_dir: Optional[str] = None):
        self.dir = Path(templates_dir) if templates_dir else DEFAULT_TEMPLATES_DIR
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self):
        if not self.dir.exists():
            return
        for p in self.dir.glob("*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                tid = j.get("id") or p.stem
                self._cache[tid] = j
            except Exception:
                # 跳过无效模板
                continue

    def get_ids(self) -> List[str]:
        return list(self._cache.keys())

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(template_id)

class PromptEngine:
    def build_prompt(self, template: Dict[str, Any], params: Dict[str, Any]) -> str:
        """
        Build a single prompt string.
        Template must include 'prompt_template' and 'schema'.
        params may include count, tone, etc.
        """
        tpl = template.get("prompt_template", "")
        schema = template.get("schema", {})
        # 渲染最小占位符：{{count}}、{{tone}}、{{schema}}
        prompt = tpl.replace("{{count}}", str(params.get("count", 1)))
        prompt = prompt.replace("{{tone}}", str(params.get("tone", "concise")))
        prompt = prompt.replace("{{schema}}", json.dumps(schema))
        return prompt

class HFClient:
    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self.model_id = model_id or "HuggingFaceTB/SmolLM3-3B:hf-inference"  # Default model
        self.api_key = api_key or os.getenv("HF_API_KEY")
        
        if not self.api_key:
            raise RuntimeError("HF_API_KEY not provided in environment (.env).")
        
        print(f"DEBUG: Initializing HFClient with model: {self.model_id}")
        
        # 使用 Hugging Face 路由器初始化 OpenAI 客户端
        self.client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=self.api_key,
        )
        
        print("DEBUG: HFClient initialized with OpenAI interface")

    def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int = 512) -> Tuple[str, Dict[str, Any]]:
        print(f"DEBUG: Generating text with prompt length: {len(prompt)}")
        print(f"DEBUG: Using model: {self.model_id}")
        
        try:
            # 使用 OpenAI 聊天完成界面
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # 提取生成的文本
            generated_text = completion.choices[0].message.content
            
            print(f"DEBUG: Generated text length: {len(generated_text)}")
            print(f"DEBUG: Generated text preview: {generated_text[:200]}")
            
            return generated_text, {"status": "success", "model": self.model_id}
            
        except Exception as e:
            error_msg = f"Generation failed: {str(e)}"
            print(f"DEBUG: {error_msg}")
            return f"Generation error: {error_msg}", {"status": "error", "error": error_msg}

class Validator:
    def validate(self, schema: Dict[str, Any], data: Any) -> Dict[str, Any]:
        if not schema:
            return {"valid": True, "errors": []}
        
        try:
            # 处理不同的数据类型和架构期望
            if isinstance(data, list):
                # 数据是一个数组 - 根据模式验证每个项目
                errors = []
                for i, item in enumerate(data):
                    try:
                        jsonschema_validate(instance=item, schema=schema)
                    except ValidationError as e:
                        errors.append(f"Item {i}: {str(e)}")
                    except Exception as e:
                        errors.append(f"Item {i}: {str(e)}")
                
                if errors:
                    return {"valid": False, "errors": errors}
                else:
                    return {"valid": True, "errors": []}
            else:
                # 数据是单个对象 - 直接验证
                jsonschema_validate(instance=data, schema=schema)
                return {"valid": True, "errors": []}
                
        except ValidationError as e:
            return {"valid": False, "errors": [str(e)]}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

class Generator:
    def __init__(self, hf_client: HFClient, registry: TemplateRegistry, prompt_engine: PromptEngine, validator: Validator):
        self.hf = hf_client
        self.registry = registry
        self.engine = prompt_engine
        self.validator = validator

    def generate(self,
                 template_id: Optional[str],
                 params: Dict[str, Any],
                 custom_prompt: Optional[str] = None,
                 temperature: float = 0.2,
                 max_tokens: int = 512) -> Dict[str, Any]:
        # 加载模板或构建临时模板
        if custom_prompt:
            # 对于自定义提示，让 LLM 直接从提示中了解计数
            tone = params.get('tone', 'concise')
            
            # 为社交媒体帖子创建更具体的少数示例
            # 这与常见用例相匹配并显示了正确的结构
            example = '[{"platform": "Instagram", "content": "Beautiful sunset today! 🌅", "hashtags": ["#sunset", "#nature"], "engagement_metrics": {"likes": 150, "shares": 25, "comments": 12}}, {"platform": "Twitter", "content": "Just finished an amazing workout! 💪", "hashtags": ["#fitness", "#motivation"], "engagement_metrics": {"likes": 89, "shares": 15, "comments": 8}}]'
            
            # 首先使用少量示例构建增强提示
            # 让法学硕士了解自定义提示本身的计数
            enhanced_prompt = f"{example} {custom_prompt} Tone: {tone}. CRITICAL: Start immediately with [ and end with ]. Do NOT use <think> tags. Do NOT explain your reasoning. Output ONLY the JSON array. No thinking, no explanations, just JSON."
            template = {"id": "custom", "prompt_template": enhanced_prompt, "schema": {}}
        else:
            template = self.registry.get_template(template_id) or {"id": template_id, "prompt_template": "", "schema": {}}

        prompt = self.engine.build_prompt(template, params)
        try:
            raw_text, meta = self.hf.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as exc:
            return {"status": "error", "output": None, "raw_model_text": "", "validation": {"valid": False, "errors": [str(exc)]}}

        parsed = safe_json_load(raw_text)
        if parsed is None:
            return {"status": "error", "output": None, "raw_model_text": raw_text, "validation": {"valid": False, "errors": ["parse_error"]}}

        validation = self.validator.validate(template.get("schema", {}), parsed)
        return {"status": "ok", "output": parsed, "raw_model_text": raw_text, "validation": validation}
