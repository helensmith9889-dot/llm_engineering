from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scrape_horoscopes_ht(headless=True, timeout=3):
    """
    从 Hindustan Times 占星页面抓取星座运势。

    参数:
        headless (bool): 是否以无头模式运行 Chrome。默认 False。
        timeout (int): WebDriverWait 超时秒数。默认 3。

    返回:
        dict: 键为星座名、值为运势正文。失败时返回空字典。

    异常:
        Exception: 打印错误信息后继续抓取其他星座。
    """
    
    # 配置 Chrome 选项
    options = webdriver.ChromeOptions()
    print("Headless mode:", headless)
    if headless:
        options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=options)
    horoscope_data = {}
    
    # 要遍历的十二星座列表
    sun_signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
                 "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    
    try:
        for sign_index, sign_name in enumerate(sun_signs):
            try:
                # 打开占星页面
                driver.get("https://www.hindustantimes.com/astrology")
                
                # 等待星座列表加载
                wait = WebDriverWait(driver, timeout)
                horoscope_list = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "horoscopeSunSign"))
                )
                
                # 获取全部 li（12 个星座）
                li_elements = horoscope_list.find_elements(By.TAG_NAME, "li")
                
                # 按索引点击对应星座
                if sign_index < len(li_elements):
                    li = li_elements[sign_index]
                    
                    # 从 span 提取星座名
                    span = li.find_element(By.TAG_NAME, "span")
                    sun_sign_name = span.text
                    
                    # 找到并点击链接
                    anchor = li.find_element(By.TAG_NAME, "a")
                    driver.execute_script("arguments[0].click();", anchor)
                    
                    time.sleep(3)
                    
                    # 找到第一个预测卡片
                    prediction_card = wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "prediction-card"))
                    )
                    
                    # 点击「阅读完整预测」链接
                    read_link = prediction_card.find_element(By.TAG_NAME, "a")
                    driver.execute_script("arguments[0].click();", read_link)
                    
                    time.sleep(3)
                    
                    # 获取全部正文元素
                    content_elements = driver.find_elements(By.CLASS_NAME, "content")
                    
                    # 汇总所有正文文本
                    content_text = "\n".join([elem.text for elem in content_elements])
                    
                    # 存入字典
                    horoscope_data[sun_sign_name] = content_text
                    print(f"✓ Successfully processed {sun_sign_name}")
                
            except Exception as e:
                print(f"✗ Error processing sign at index {sign_index}: {str(e)}")
                
    finally:
        driver.quit()
    
    return horoscope_data


def scrape_horoscopes_vedicrishi(headless=True, timeout=3):
    """
    从 Vedic Rishi 每日运势页抓取数据。

    参数:
        headless (bool): 是否无头模式运行 Chrome。默认 False。
        timeout (int): WebDriverWait 超时秒数。默认 3。

    返回:
        dict: 键为星座名、值为运势正文。失败时返回空字典。
    """
    
    # 配置 Chrome 选项
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=options)
    horoscope_data = {}
    
    sun_signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
                 "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    
    try:
        for sign_index, sign_name in enumerate(sun_signs):
            try:
                # 打开当前星座的运势页
                driver.get(f"https://vedicrishi.in/horoscope/{sign_name}-daily-horoscope")
                
                wait = WebDriverWait(driver, timeout)
                horoscope_section = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#__next > div:nth-child(1) > div:nth-child(4) > div > section.w-full.bg-transparent.py-12 > div > div.lg\\:col-span-8 > div.flex.flex-col.gap-6.items-center.pb-10"))
                )
                
                # 提取可见运势文本
                content_text = horoscope_section.text.strip()
                horoscope_data[sign_name] = content_text
                print(f"✓ Successfully processed {sign_name}")
                
            except Exception as e:
                print(f"✗ Error processing sign at index {sign_index}: {str(e)}")
                
    finally:
        driver.quit()
    
    return horoscope_data


def scrape_horoscopes_indiatv(headless=True, timeout=3):
    """
    从 India TV 每日运势页抓取数据。

    参数:
        headless (bool): 是否无头模式运行 Chrome。默认 False。
        timeout (int): WebDriverWait 超时秒数。默认 3。

    返回:
        dict: 键为星座名、值为运势正文。失败时返回空字典。
    """
    
    # 配置 Chrome 选项
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=options)
    horoscope_data = {}
    
    sun_signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", 
                 "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
    
  
    try:
        # 打开当前星座的运势页
        driver.get(f"https://www.indiatvnews.com/astrology")
        
        wait = WebDriverWait(driver, timeout)
        today_horoscope_link = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body > main > section:nth-child(2) > div > div > div.lhs > div.cat-top-news > ul > li.big-news > a"))
        )
        
        today_horoscope_link.click()
        time.sleep(3)   
        # 提取可见运势文本
        content_text = driver.find_element(By.ID, "content").text.strip()
        
        # content 中含全部星座运势，需要拆成各个星座
        # 期望按「星座名: 运势」一类格式解析
        # 假定格式类似 "aries: ...\n taurus: ..."，按行再按冒号拆分
        lines = content_text.split("\n")
        if len(lines) < 12:
            raise Exception("Expected 12 lines of horoscope data, but got less.")
        
        for line in lines:
            # 若该行包含某个星座名，则新建一条字典记录
            # 若不含星座名，则把文本追加到上一个星座
            sign_match  =  False
            for sign in sun_signs:
                if sign in line.strip().lower():
                    sign_match = True
                    sign_name = sign.capitalize()
                    # horoscope_text = line.split(":", 1)[1].strip() if ":" in line else ""
                    horoscope_data[sign_name] = ""
                    last_sign = list(horoscope_data.keys())[-1]
                    break
            if not sign_match:
                # 不含星座名时，追加到上一个星座的文本
                if horoscope_data:
                    last_sign = list(horoscope_data.keys())[-1]
                    horoscope_data[last_sign] += " " + line.strip()

        print(f"✓ Successfully processed horoscopes for all signs")
        
    except Exception as e:
        print(f"✗ Error processing horoscopes: {str(e)}")
        
    finally:
        driver.quit()
    
    return horoscope_data