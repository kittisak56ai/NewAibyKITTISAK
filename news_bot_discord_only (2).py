import feedparser
from googletrans import Translator
from transformers import pipeline
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import requests
import time
import os
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1391393540252237886/mfR4DoXUhNHJ03EJIaWMxca3M87kxTnfIpLsnmLE0aJb2R5gTtngi6UL5lc7pTBbhPpN"

rss_feeds = {
    "การเมือง": "http://feeds.bbci.co.uk/news/politics/rss.xml",
    "เศรษฐกิจ": "http://feeds.reuters.com/reuters/businessNews",
    "เทคโนโลยี": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "AI": "https://www.reuters.com/technology/ai/feed",
    "หุ้น": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI,^GSPC,^IXIC&region=US&lang=en-US",
    "คริปโต": "https://cryptonews.com/news/feed",
    "สงคราม": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "สตาร์ทอัพ": "https://techcrunch.com/startups/feed/",
    "วอร์เรน บัฟเฟตต์": "https://news.google.com/rss/search?q=warren+buffett",
    "ข่าวยา": "https://www.fiercepharma.com/rss.xml"
}

KEYWORDS = [
    "trump", "donald trump", "โดนัลด์ ทรัมป์",
    "elon musk", "อีลอน มัสก์", "มัสก์",
    "warren buffett", "วอร์เรน บัฟเฟตต์", "เบิร์กไชร์",
    "stock", "ตลาดหุ้น", "nasdaq", "dow jones", "s&p", "bond", "interest rate", "yield",
    "crypto", "คริปโต", "บิทคอยน์", "bitcoin", "ethereum", "เหรียญ", "defi",
    "ai", "ปัญญาประดิษฐ์", "openai", "chatgpt", "deeplearning", "machine learning",
    "war", "สงคราม", "ยูเครน", "รัสเซีย", "ไต้หวัน", "จีน", "อิสราเอล", "ฮามาส", "กาซา",
    "pharma", "drug", "ยา", "วัคซีน", "fda", "clinical trial",
    "startup", "venture capital", "series a", "funding", "tech startup"
]

sent_links = set()

# เริ่มต้น components
translator = None
summarizer = None

def initialize_components():
    global translator, summarizer
    try:
        logger.info("กำลังเริ่มต้น translator...")
        translator = Translator()
        logger.info("กำลังเริ่มต้น summarizer...")
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        logger.info("เริ่มต้น components สำเร็จ")
    except Exception as e:
        logger.error(f"ไม่สามารถเริ่มต้น components: {e}")
        raise

def summarize_and_translate(content):
    try:
        if not content or len(content) < 50:
            return content[:200]
        
        # ตัดข้อความให้สั้นลงก่อนส่งไป summarize
        content = content[:1000]
        
        if summarizer:
            summary = summarizer(content, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
        else:
            summary = content[:200]
        
        if translator:
            translated = translator.translate(summary, dest='th').text
            return translated
        else:
            return summary
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการสรุปและแปล: {e}")
        return content[:200]

def create_voice(text, filename="summary.mp3"):
    try:
        tts = gTTS(text=text, lang="th")
        tts.save(filename)
        logger.info(f"สร้างไฟล์เสียง: {filename}")
    except Exception as e:
        logger.error(f"ไม่สามารถสร้างไฟล์เสียง: {e}")

def create_image(title, summary, filename="news.png"):
    try:
        img = Image.new('RGB', (800, 600), color=(255, 255, 240))
        draw = ImageDraw.Draw(img)
        
        # ใช้ font เริ่มต้น
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

        # วาดชื่อเรื่อง
        draw.text((40, 40), title, font=font_title, fill=(0, 0, 0))

        # วาดเนื้อหา
        max_width = 720
        lines = []
        words = summary.split()
        line = ""
        for word in words:
            test_line = line + word + " "
            bbox = draw.textbbox((0, 0), test_line, font=font_body)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word + " "
        if line:
            lines.append(line)

        y_text = 100
        line_height = 30
        for l in lines:
            draw.text((40, y_text), l, font=font_body, fill=(50, 50, 50))
            y_text += line_height

        img.save(filename)
        logger.info(f"สร้างรูปภาพ: {filename}")
    except Exception as e:
        logger.error(f"ไม่สามารถสร้างรูปภาพ: {e}")

def send_discord(text):
    try:
        data = {"content": text}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        if response.status_code == 204:
            logger.info("✅ ส่งข้อความ Discord สำเร็จ")
        else:
            logger.error(f"❌ ส่งข้อความ Discord ล้มเหลว: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการส่ง Discord: {e}")

def parse_feed_safely(url):
    try:
        feed = feedparser.parse(url)
        return feed
    except Exception as e:
        logger.error(f"ไม่สามารถอ่าน RSS feed {url}: {e}")
        return None

def translate_safely(text, dest='th'):
    try:
        if translator:
            return translator.translate(text, dest=dest).text
        else:
            return text
    except Exception as e:
        logger.error(f"ไม่สามารถแปลภาษา: {e}")
        return text

def run_news_bot_loop(interval_seconds=300):  # เพิ่มช่วงเวลาเป็น 5 นาที
    logger.info("🚀 เริ่มระบบบอทส่งข่าว Discord")
    
    # เริ่มต้น components
    initialize_components()
    
    while True:
        try:
            logger.info("🔄 เริ่มรอบการตรวจสอบข่าวใหม่")
            
            for cat, url in rss_feeds.items():
                try:
                    logger.info(f"🔍 ตรวจสอบ {cat} จาก {url}")
                    
                    feed = parse_feed_safely(url)
                    if not feed or not feed.entries:
                        logger.warning(f"ไม่พบข่าวใน {cat}")
                        continue

                    entry = feed.entries[0]
                    link = entry.link

                    if link in sent_links:
                        logger.info(f"ข่าวใน {cat} ถูกส่งไปแล้ว")
                        continue

                    content = entry.get("summary", entry.get("description", ""))
                    title = entry.title

                    text_to_check = (title + " " + content).lower()
                    if not any(kw in text_to_check for kw in KEYWORDS):
                        logger.info(f"ข่าวใน {cat} ไม่ตรงกับคีย์เวิร์ด")
                        continue

                    logger.info(f"📰 พบข่าวใหม่ใน {cat}: {title}")

                    title_th = translate_safely(title)
                    summary_th = summarize_and_translate(content)

                    full_text = (
                        f"🗂️ หมวด: {cat}\n"
                        f"📰 {title_th}\n\n"
                        f"📄 สรุป:\n{summary_th}\n\n"
                        f"🔗 อ่านต่อ: {link}"
                    )

                    # สร้างไฟล์ (ถ้าต้องการ)
                    # create_image(title_th, summary_th)
                    # create_voice(summary_th)

                    send_discord(full_text)
                    sent_links.add(link)
                    logger.info(f"📨 ส่งข่าวใหม่ในหมวด {cat} สำเร็จ")
                    
                    # หยุดพักเล็กน้อยระหว่างการส่ง
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"เกิดข้อผิดพลาดในการประมวลผล {cat}: {e}")
                    continue

            logger.info(f"😴 หยุดพัก {interval_seconds} วินาที")
            time.sleep(interval_seconds)
            
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในลูปหลัก: {e}")
            time.sleep(60)  # หยุดพัก 1 นาทีก่อนลองใหม่

if __name__ == "__main__":
    run_news_bot_loop(interval_seconds=300)
