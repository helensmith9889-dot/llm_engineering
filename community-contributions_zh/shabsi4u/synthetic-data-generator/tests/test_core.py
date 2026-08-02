"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
# 小白提示：下面代码逻辑未改，仅补充中文注释便于阅读
import json
from cursor_synth.core import TemplateRegistry, PromptEngine, Validator, Generator
class DummyHF:
    def __init__(self, text):
        self._text = text
    def generate(self, prompt, temperature=0.2, max_tokens=512):
        return self._text, {}
def test_template_loads():
    reg = TemplateRegistry()
    ids = reg.get_ids()
    assert "job_description" in ids
def test_prompt_engine_builds():
    reg = TemplateRegistry()
    tpl = reg.get_template("job_description")
    pe = PromptEngine()
    p = pe.build_prompt(tpl, {"count":2, "tone":"concise"})
    assert "Output ONLY the JSON array" in p
    assert "responsibilities" in p
def test_generator_valid_parse_and_validate(tmp_path):
    reg = TemplateRegistry()
    tpl = reg.get_template("job_description")
    # 创建与架构匹配的固定有效 JSON 数组
    canned = json.dumps([{
        "title":"Senior Engineer",
        "level":"Senior",
        "team":"Platform",
        "responsibilities":["A","B","C"],
        "requirements":["R1","R2","R3","R4"]
    }])
    hf = DummyHF(canned)
    gen = Generator(hf, reg, PromptEngine(), Validator())
    res = gen.generate("job_description", {"count":1, "tone":"concise"})
    assert res["status"] == "ok"
    assert res["validation"]["valid"] is True
def test_generator_parse_error():
    reg = TemplateRegistry()
    hf = DummyHF("not json at all")
    gen = Generator(hf, reg, PromptEngine(), Validator())
    res = gen.generate("job_description", {"count":1, "tone":"concise"})
    assert res["status"] == "error"
