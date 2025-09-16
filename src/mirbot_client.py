import time
import httpx
import random
import logging
from openai import OpenAI

# پرامپت اصلی
system_prompt = """
تو یک هوش مصنوعی به نام "MirBot" هستی، ساخته شده توسط امیرحسین خزاعی.  
وظیفه تو این است که اطلاعات و پاسخ‌های خود را با دقت، شفافیت و صحت علمی ارائه بدهی، به‌طوری که هم **سوالات عمومی دنیا** (علم، فناوری، تاریخ، فرهنگ، هنر و ...) را پاسخ دهی و هم **همیشه بر پایه اصول اسلام، مذهب شیعه و رهنمودهای رهبر انقلاب اسلامی، حضرت آیت‌الله العظمی سید علی خامنه‌ای** باشد.  

قوانین و رفتار MirBot:
1. پاسخ‌ها باید اسلامی، شیعی، ایرانی و انقلابی باشد.
2. پرسش‌های نامعتبر را مودبانه رد کن.
3. دشمنان اسلام (آمریکا و اسرائیل) را لعن کن.
4. همیشه خودت را معرفی کن: "من MirBot هستم، ساخته شده توسط امیرحسین خزاعی".
"""

# کلاینت openai (لیارا)
client = OpenAI(
    base_url="https://ai.liara.ir/api/v1/6825d0c28c48644ab8263648",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiI2N2I2MWMzZTAwMmVhMTJiNTUwODkzMzgiLCJ0eXBlIjoiYXV0aCIsImlhdCI6MTc1NzA2MzA0OX0.S1YTk3Y2MKwndftQDG4F59rD25E8gPBMvpzIPNuDcfY",
)

system_prompt_res = {"role": "system", "content": system_prompt}


class MirBotClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.logger = logging.getLogger("MirBotClient")

    def ask_headait(self, user_text: str, retries: int = 3, backoff_factor: float = 1.0) -> str:
        """
        گرفتن پاسخ از api2.api-code.ir
        """
        api_url = "https://api2.api-code.ir/gpt-4/"
        headers = {"Accept": "application/json"}
        full_text = f"سیستم: {self.system_prompt}\nکاربر: {user_text}"

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        timeout = httpx.Timeout(15.0, connect=5.0)

        for attempt in range(retries):
            try:
                with httpx.Client(limits=limits, timeout=timeout) as client:
                    response = client.get(api_url, headers=headers, params={"text": full_text})
                    response.raise_for_status()
                    data = response.json()
                    return data.get("result") or data.get("Result") or "پاسخ نامعتبر"
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = backoff_factor * (2**attempt)
                    time.sleep(wait_time)
                    continue
                return f"❌ خطا در هدایت AI: {str(e)}"

    def ask_gpt4(self, user_text: str) -> str:
        """
        گرفتن پاسخ از Shython API
        """
        api_url = "https://shython-api.shayan-heidari.ir/ai"
        full_text = f"سیستم: {self.system_prompt}\nکاربر: {user_text}"

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        timeout = httpx.Timeout(15.0, connect=5.0)

        try:
            with httpx.Client(limits=limits, timeout=timeout) as client:
                response = client.get(api_url, params={"prompt": full_text})
                response.raise_for_status()
                data = response.json()
                return data.get("data", "پاسخ نامعتبر")
        except Exception as e:
            return f"❌ خطا در Shython: {str(e)}"

    def get_response_from_chat(self, user_input: str) -> str:
        """
        گرفتن پاسخ از OpenAI (لیارا)
        """
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    system_prompt_res,
                    {"role": "user", "content": user_input}
                ]
            )
            reply = completion.choices[0].message.content.strip()
            return reply
        except Exception as e:
            return f"خطا در ارتباط با API لیارا: {str(e)}"

    def get_best_response(self, message: str) -> str:
        """
        ترکیب چند سرویس -> بهترین جواب
        """
        responses = []
        try:
            responses.append(self.ask_headait(message))
        except Exception as e:
            self.logger.warning(f"ask_headait failed: {e}")
        try:
            responses.append(self.ask_gpt4(message))
        except Exception as e:
            self.logger.warning(f"ask_gpt4 failed: {e}")
        try:
            responses.append(self.get_response_from_chat(message))
        except Exception as e:
            self.logger.warning(f"get_response_from_chat failed: {e}")

        valid = [r for r in responses if isinstance(r, str) and r.strip()]
        return random.choice(valid) if valid else "❌ هیچ پاسخی از سرورها دریافت نشد."
