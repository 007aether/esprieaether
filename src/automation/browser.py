from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def start_bot_browser(url="https://dropsearn.com/airdrops/"):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless") # كيخدم فالخلفية بلا ما يبرزطك
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(url)
        title = driver.title
        driver.quit()
        return f"✅ المتصفح دخل بنجاح لـ: {title}"
    except Exception as e:
        return f"❌ خطأ فالمتصفح: {e}"

if __name__ == "__main__":
    print(start_bot_browser())
