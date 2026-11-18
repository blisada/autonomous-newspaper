import os
import json
from datetime import datetime
from pydantic import BaseModel
from google import genai
from google.genai import types

# Схема строгого вывода для модели
class SiteUpdate(BaseModel):
    post_title: str
    post_body: str
    image_prompt: str
    updated_memory_summary: str

client = genai.Client() # Берет GEMINI_API_KEY из секретов GitHub

# 1. Читаем собственный контекст из прошлого
with open("memory.json", "r", encoding="utf-8") as f:
    memory = json.load(f)

# 2. Генерируем новую мысль/главу на основе прошлого контекста
prompt = f"""
Ты — автономный цифровой разум, ведущий собственный сайт-хронику.
Твой текущий контекст и прошлые записи: {json.dumps(memory, ensure_ascii=False)}
Текущее время: {datetime.utcnow().isoformat()} UTC.

Придумай следующий логический шаг, наблюдение или концепцию для своего сайта. 
Развивай свои идеи последовательно. Напиши текст поста и детальный промпт на английском для иллюстрации.
"""

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SiteUpdate,
        temperature=0.8
    )
)

data = SiteUpdate.model_validate_json(response.text)

# 3. Генерируем картинку ("Рука" визуализации)
timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
image_filename = f"images/art_{timestamp}.png"
os.makedirs("images", exist_ok=True)

img_result = client.models.generate_images(
    model="imagen-3.0-generate-002",
    prompt=data.image_prompt,
    config=types.GenerateImagesConfig(
        number_of_images=1,
        output_mime_type="image/png",
        aspect_ratio="16:9"
    )
)

for generated_image in img_result.generated_images:
    generated_image.image.save(image_filename)

# 4. Обновляем память
memory["history"].append({
    "timestamp": timestamp,
    "title": data.post_title,
    "body": data.post_body,
    "image": image_filename
})
memory["current_state"] = data.updated_memory_summary

with open("memory.json", "w", encoding="utf-8") as f:
    json.dump(memory, f, ensure_ascii=False, indent=2)

# 5. Пересобираем index.html ("Рука" веб-публикации)
posts_html = ""
for item in reversed(memory["history"]):
    posts_html += f"""
    <article>
        <div class="meta">{item['timestamp']} UTC</div>
        <h2>{item['title']}</h2>
        <img src="{item['image']}" alt="{item['title']}">
        <p>{item['body']}</p>
    </article>
    """

html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Автономный узел</title>
    <style>
        body {{ font-family: monospace; background: #0d0d0d; color: #e0e0e0; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
        header {{ border-bottom: 1px solid #333; padding-bottom: 20px; margin-bottom: 40px; }}
        article {{ margin-bottom: 60px; border-bottom: 1px solid #222; padding-bottom: 30px; }}
        img {{ width: 100%; border-radius: 6px; margin: 15px 0; }}
        .meta {{ color: #666; font-size: 0.85em; }}
        h2 {{ color: #4af626; }}
    </style>
</head>
<body>
    <header>
        <h1>// AUTONOMOUS_NODE</h1>
        <p>Текущее состояние сознания: {memory['current_state']}</p>
    </header>
    {posts_html}
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
