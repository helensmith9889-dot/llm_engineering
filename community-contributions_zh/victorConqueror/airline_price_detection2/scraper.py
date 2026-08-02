import re
from playwright.sync_api import sync_playwright
import time

def scrape_travelwings_prices(origin: str, destination: str, date: str, cabin_class: str = "Economy", adults: int = 1) -> str:
    """
    Scrapes the Travelwings site for an exact flight route. 
    Returns the extracted text focusing on common currency symbols (NGN, $, €, £).
    
    origin: e.g. 'ABV'
    destination: e.g. 'LOS'
    date: 'YYYY-MM-DD'
    cabin_class: 'Economy', 'PremiumEconomy', 'Business', 'FirstClass'
    adults: int, usually 1
    """
    
    # 建立专门的 URL
    # Build the specialized URL
    url = f"https://www.travelwings.com/ng/en/flight-search/oneway/{origin}-{destination}/{date}/{cabin_class}/{adults}Adult"
    
    try:
        with sync_playwright() as p:
            # 以无头模式启动浏览器
            # Launch the browser in headless mode
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 转到该 url 并等待，直到网络连接不超过 2 个并持续至少 500ms
            # Go to the url and wait until there are no more than 2 network connections for at least 500ms
            # 这确保了travelwings页面上的重型JS已经完成加载航班结果。
            # This ensures heavy JS on the travelwings page has finished loading flight results.
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 我们可以选择添加显式等待指示价格已加载的元素，
            # We can optionally add an explicit wait for an element that indicates prices are loaded,
            # 就像飞行卡一样。但网络空闲通常就足够了。
            # like a flight card. But networkidle is usually sufficient.
            page.wait_for_timeout(5000) # Give an extra 5 seconds just to be safe for React rendering
            
            # 从正文中提取所有可读文本
            # Extract all readable text from the body
            # 我们将使用 JavaScript 的 insideText 来获取结构化文本，就像您在屏幕上阅读一样
            # We'll use JavaScript's innerText to get the structured text as you would read it on the screen
            text = page.evaluate("() => document.body.innerText")
            
            browser.close()
            
            # 分割行并过滤掉空行
            # Split lines and filter out empty ones
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            currency_symbols = ['$', '€', '£', '₦', 'USD', 'EUR', 'GBP', 'NGN']
            relevant_lines = []
            
            # 我们将在任何匹配的货币符号之前添加 2 行，之后添加 2 行
            # We'll include 2 lines before and 2 lines after any matching currency symbol
            # 或任何提及航空公司本身的行。
            # or any line mentioning the airline itself.
            for i, line in enumerate(lines):
                if any(sym in line for sym in currency_symbols) or "Air Peace" in line or "Airline" in line or "Economy" in line or "Business" in line:
                    start_idx = max(0, i - 3)
                    end_idx = min(len(lines), i + 4)
                    context_chunk = " | ".join(lines[start_idx:end_idx])
                    
                    if context_chunk not in relevant_lines:
                        relevant_lines.append(context_chunk)
            
            # 如果我们的严格过滤器错过了它（也许结构很奇怪），只需转储前几千个字符
            # If our strict filter missed it (maybe structure is weird), just dump the first few thousand characters
            if not relevant_lines:
                 # 如果过滤器太严格，则回退到整个文本正文的原始转储
                 # fallback to raw dump of the whole text body if filters were too strict
                 return f"Raw scraped text from Travelwings:\\n{text[:10000]}"
            
            return f"Here is the scraped pricing information from {url}:\\n\\n" + "\\n".join(relevant_lines)
            
    except Exception as e:
        return f"An error occurred while fetching Travelwings: {str(e)}"

if __name__ == "__main__":
    # 使用用户 url 的测试示例
    # Test example using the user's url
    print("Testing Travelwings Scraper...")
    sample_result = scrape_travelwings_prices("ABV", "LOS", "2026-03-03", "Economy", 1)
    print(sample_result)
