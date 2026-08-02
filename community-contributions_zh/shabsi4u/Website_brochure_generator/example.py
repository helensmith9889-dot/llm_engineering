#!/usr/bin/env python3
"""中文注释版：逻辑与标识符保持不变，仅增加/翻译注释便于小白阅读。"""
"""
Example usage of the Website Brochure Generator
"""

from website_brochure_generator import create_brochure, stream_brochure, get_links, translate_brochure

def main():
    # 示例网站网址
    url = "https://example.com"
    
    print("=== Website Brochure Generator Example ===\n")
    
    # 示例1：获取相关链接
    print("1. Analyzing website links...")
    links = get_links(url)
    print(f"Found {len(links['links'])} relevant pages:")
    for link in links['links']:
        print(f"  - {link['type']}: {link['url']}")
    
    print("\n" + "="*50 + "\n")
    
    # 示例2：创建宣传册（完整输出）
    print("2. Creating brochure (complete output)...")
    brochure = create_brochure(url)
    
    print("\n" + "="*50 + "\n")
    
    # 示例3：流式宣传册（实时生成）
    print("3. Streaming brochure generation...")
    streamed_brochure = stream_brochure(url)
    
    print("\n" + "="*50 + "\n")
    
    # 示例 4：将小册子翻译成西班牙语（完整输出）
    print("4. Translating brochure to Spanish (complete output)...")
    spanish_brochure = translate_brochure(url, "Spanish", stream_mode=False)
    
    print("\n" + "="*50 + "\n")
    
    # 示例 5：将小册子翻译成法语（流输出）
    print("5. Translating brochure to French (streaming output)...")
    french_brochure = translate_brochure(url, "French", stream_mode=True)
    
    print("\n=== Example Complete ===")

if __name__ == "__main__":
    main()
