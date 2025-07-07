import feedparser
from googletrans import Translator
import requests
import time
import logging
import re

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
translator = None

def initialize_translator():
    global translator
    try:
        logger.info("กำลังเริ่มต้น translator...")
        translator = Translator()
        logger.info("เริ่มต้น translator สำเร็จ")
    except Exception as e:
        logger.error(f"ไม่สามารถเริ่มต้น translator: {e}")
        translator = None

def clean_text(text):
    """ทำความสะอาดข้อความ"""
    if not text:
        return ""
    
    # ลบ HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # ลบ extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def simple_summarize(content, max_length=200):
    """สรุปข้อความอย่างง่าย โดยเอาประโยคแรก ๆ"""
    if not content:
        return ""
    
    content = clean_text(content)
    sentences = content.split('.')
    
    summary = ""
    for sentence in sentences:
        if len(summary + sentence) < max_length:
            summary += sentence + ". "
        else:
            break
    
    return summary.strip()

def translate_text(text, dest='th'):
    """แปลข้อความ"""
    try:
        if translator and text:
            result = translator.translate(text, dest=dest)
            return result.text
        else:
            return text
    except Exception as e:
        logger.error(f"ไม่สามารถแปลภาษา: {e}")
        return text

def send_discord(text):
    """ส่งข้อความไป Discord"""
    try:
        data = {"content": text}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        if response.status_code == 204:
            logger.info("✅ ส่งข้อความ Discord สำเร็จ")
            return True
        else:
            logger.error(f"❌ ส่งข้อความ Discord ล้มเหลว: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการส่ง Discord: {e}")
        return False

def parse_feed_safely(url):
    """อ่าน RSS feed อย่างปลอดภัย"""
    try:
        logger.info(f"กำลังอ่าน RSS: {url}")
        feed = feedparser.parse(url)
        if feed.entries:
            logger.info(f"พบข่าว {len(feed.entries)} ข่าว")
            return feed
        else:
            logger.warning(f"ไม่พบข่าวใน RSS: {url}")
            return None
    except Exception as e:
        logger.error(f"ไม่สามารถอ่าน RSS feed {url}: {e}")
        return None

def process_news_entry(entry, category):
    """ประมวลผลข่าวแต่ละรายการ"""
    try:
        link = entry.link
        title = entry.title
        content = entry.get("summary", entry.get("description", ""))
        
        # ตรวจสอบว่าส่งไปแล้วหรือยัง
        if link in sent_links:
            return False
        
        # ตรวจสอบคีย์เวิร์ด
        text_to_check = (title + " " + content).lower()
        if not any(kw in text_to_check for kw in KEYWORDS):
            return False
        
        # แปลและสรุป
        title_th = translate_text(title)
        summary_en = simple_summarize(content, max_length=300)
        summary_th = translate_text(summary_en)
        
        # จัดรูปแบบข้อความ
        full_text = (
            f"🗂️ หมวด: {category}\n"
            f"📰 {title_th}\n\n"
            f"📄 สรุป:\n{summary_th}\n\n"
            f"🔗 อ่านต่อ: {link}"
        )
        
        # ส่งข้อความ
        if send_discord(full_text):
            sent_links.add(link)
            logger.info(f"📨 ส่งข่าวใหม่ในหมวด {category} สำเร็จ")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการประมวลผลข่าว: {e}")
        return False

def run_news_bot():
    """รันบอทส่งข่าว"""
    logger.info("🚀 เริ่มระบบบอทส่งข่าว Discord")
    
    # เริ่มต้น translator
    initialize_translator()
    
    # ส่งข้อความเริ่มต้น
    send_discord("🤖 บอทข่าวเริ่มทำงานแล้ว!")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            logger.info(f"🔄 รอบที่ {cycle_count} - เริ่มตรวจสอบข่าวใหม่")
            
            news_sent = 0
            
            for category, url in rss_feeds.items():
                try:
                    feed = parse_feed_safely(url)
                    if not feed or not feed.entries:
                        continue
                    
                    # ประมวลผลข่าวใหม่ (เฉพาะข่าวแรก)
                    if process_news_entry(feed.entries[0], category):
                        news_sent += 1
                        time.sleep(3)  # หยุดพัก 3 วินาที
                    
                except Exception as e:
                    logger.error(f"ข้อผิดพลาดในการประมวลผล {category}: {e}")
                    continue
            
            logger.info(f"📊 รอบที่ {cycle_count} เสร็จสิ้น - ส่งข่าว {news_sent} ข่าว")
            
            # หยุดพัก 5 นาที
            sleep_time = 300
            logger.info(f"😴 หยุดพัก {sleep_time} วินาที")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในลูปหลัก: {e}")
            time.sleep(60)  # หยุดพัก 1 นาที แล้วลองใหม่

if __name__ == "__main__":
    run_news_bot()
