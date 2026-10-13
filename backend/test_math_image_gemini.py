import asyncio
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import time

async def main():
    print("==================================================")
    print("TEST: Multimodal Vision with Image '12 + 15 = ?'")
    print("==================================================")

    # 1. Generate image with '12 + 15 = ?'
    img = Image.new("RGB", (400, 150), color="white")
    draw = ImageDraw.Draw(img)
    # Draw dark border
    draw.rectangle([5, 5, 395, 145], outline="black", width=2)
    # Draw text
    draw.text((80, 55), "12 + 15 = ?", fill="black")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64_data}"
    print(f"Generated test image: size={len(b64_data)} bytes base64")

    # 2. Instantiate GeminiProvider
    from app.core.config import settings
    from app.ai.gemini_provider import GeminiProvider

    if not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not configured!")
        return

    provider = GeminiProvider(api_key=settings.GEMINI_API_KEY)
    print(f"Using GeminiProvider with key starting with: {settings.GEMINI_API_KEY[:8]}...")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Solve the arithmetic equation shown in the image."},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }
    ]

    print("\nSending request to Gemini API (gemini-3.5-flash)...")
    start = time.time()
    tokens = []
    try:
        async for tok in provider.stream_chat(messages, model="gemini-3.5-flash", temperature=0.1):
            tokens.append(tok)
            print(tok, end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\nAPI Call Failed: {e}")
        return

    elapsed = time.time() - start
    full_text = "".join(tokens).strip()
    print("--------------------------------------------------")
    print(f"Total time elapsed: {elapsed:.2f}s")
    print(f"Tokens received count: {len(tokens)}")
    print(f"Full Response:\n{full_text}")
    print("--------------------------------------------------")

    # Verification
    if "27" in full_text:
        print("✅ SUCCESS: Gemini correctly read the image and answered 27!")
    else:
        print("❌ FAILURE: Expected '27' in response, but got different answer.")

if __name__ == "__main__":
    asyncio.run(main())
