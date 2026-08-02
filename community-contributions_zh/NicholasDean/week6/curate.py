"""将 Amazon-Reviews-2023 产品数据整理到训练/测试项目中（重用课程的
定价器解析器）。可选的每类别行上限可保留一个小型、RAM 友好的工作集。

  # 完整的课程规模管理（大型：~2.9M 项目，~9GB pickle，需要大量 RAM 来加载）：
  uv 运行 python Community-contributions/NicholasDean/week6/curate.py ALL data_full.pkl
  # 用于微调的小型混合工作子集（快速、缓存数据集，~MB）：
  uv 运行 python 社区贡献/NicholasDean/week6/curate.py 全部 data_small.pkl 5000"""
import sys, pickle, random
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "week6" / "pricer" / "parser.py").exists())
sys.path.insert(0, str(REPO / "week6"))
from datasets import load_dataset      # noqa: E402
from pricer.parser import parse        # noqa: E402

CATEGORIES = ["Appliances", "Automotive", "Cell_Phones_and_Accessories", "Electronics",
              "Musical_Instruments", "Office_Products", "Tools_and_Home_Improvement", "Toys_and_Games"]


def load_category(cat, limit=None):
    ds = load_dataset("McAuley-Lab/Amazon-Reviews-2023", f"raw_meta_{cat}", split="full", trust_remote_code=True)
    if limit:
        ds = ds.select(range(min(limit, len(ds))))   # cap rows BEFORE parsing -> fast + small
    return [it for it in (parse(d, cat) for d in ds) if it is not None]


def main(cats, out, limit=None):
    items = []
    for c in cats:
        got = load_category(c, limit)
        print(f"{c}: {len(got):,}", flush=True)
        items += got
    for it in items:
        it.make_prompt(it.full)                      # build "...Price is $X.00" training prompt
    random.seed(42)
    random.shuffle(items)
    n_test = min(2000, len(items) // 5)
    test, train = items[:n_test], items[n_test:]
    out_path = Path(__file__).parent / out
    with open(out_path, "wb") as f:
        pickle.dump({"train": [i.model_dump() for i in train],
                     "test": [i.model_dump() for i in test]}, f)
    print(f"curated {len(items):,} items -> {len(train):,} train / {len(test):,} test -> {out_path}", flush=True)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "Appliances"
    cats = CATEGORIES if arg.upper() == "ALL" else arg.split(",")
    out = sys.argv[2] if len(sys.argv) > 2 else "data.pkl"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    main(cats, out, limit)
