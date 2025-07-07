
import feedparser
from googletrans import Translator
from transformers import pipeline
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import requests
import time

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

translator = Translator()
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
sent_links = set()

def summarize_and_translate(content):
    try:
        summary = summarizer(content, max_length=250, min_length=80, do_sample=False)[0]['summary_text']
        return translator.translate(summary, dest='th').text
    except:
        return content[:300]

def create_voice(text, filename="summary.mp3"):
    gTTS(text=text, lang="th").save(filename)

def create_image(title, summary, filename="news.png"):
    img = Image.new('RGB', (800, 600), color=(255, 255, 240))
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    draw.text((40, 40), title, font=font_title, fill=(0, 0, 0))

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
    lines.append(line)

    y_text = 100
    line_height = 30
    for l in lines:
        draw.text((40, y_text), l, font=font_body, fill=(50, 50, 50))
        y_text += line_height

    img.save(filename)

def send_discord(text):
    data = {"content": text}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("✅ ส่งข้อความ Discord สำเร็จ")
    else:
        print("❌ ส่งข้อความ Discord ล้มเหลว:", response.text)

def run_news_bot_loop(interval_seconds=60):
    print("🚀 เริ่มระบบบอทส่งข่าว Discord")
    while True:
        for cat, url in rss_feeds.items():
            feed = feedparser.parse(url)
            if not feed.entries:
                continue

            entry = feed.entries[0]
            link = entry.link

            if link in sent_links:
                continue

            content = entry.get("summary", entry.get("description", ""))
            title = entry.title

            text_to_check = (title + " " + content).lower()
            if not any(kw in text_to_check for kw in KEYWORDS):
                continue

            title_th = translator.translate(title, dest='th').text
            summary_th = summarize_and_translate(content)

            full_text = (
                f"🗂️ หมวด: {cat}\n"
                f"📰 {title_th}\n\n"
                f"📄 สรุป:\n{summary_th}\n\n"
                f"🔗 อ่านต่อ: {link}"
            )

            create_image(title_th, summary_th)
            create_voice(summary_th)
            send_discord(full_text)
            sent_links.add(link)
            print(f"📨 ส่งข่าวใหม่ในหมวด {cat}: {title}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_news_bot_loop(interval_seconds=60)
