import os
import sys
import base64
import json
import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Add backend directory to path
sys.path.insert(0, os.path.abspath("backend"))

from app.ai.gemini_provider import GeminiProvider
from app.core.config import settings

def load_real_api_key():
    candidates = [".env", "backend/.env"]
    for c in candidates:
        if os.path.exists(c):
            with open(c) as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        val = line.strip().split("=", 1)[1].strip("\"' ")
                        if val and not val.startswith("your_"):
                            return val
    return settings.GEMINI_API_KEY

def create_math_image(text="12 + 15 = ?") -> str:
    img = Image.new("RGB", (400, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw simple border
    draw.rectangle([5, 5, 395, 145], outline=(30, 30, 30), width=3)
    # Draw large clear text
    draw.text((60, 50), text, fill=(0, 0, 0))
    bio = BytesIO()
    img.save(bio, format="PNG")
    b64 = base64.b64encode(bio.getvalue()).decode()
    return f"data:image/png;base64,{b64}"

async def run_test_case(name: str, provider: GeminiProvider, messages: list, model: str = "gemini-3.5-flash"):
    print(f"\n{'='*70}")
    print(f"RUNNING TEST: {name}")
    print(f"Target Model: {model}")
    print(f"{'='*70}")
    
    tokens = []
    error = None
    start_time = asyncio.get_event_loop().time()
    try:
        async for token in provider.stream_chat(messages, model=model):
            tokens.append(token)
    except Exception as e:
        error = str(e)
    duration = asyncio.get_event_loop().time() - start_time
    
    full_output = "".join(tokens).strip()
    print(f"Status: {'FAILED' if error else 'SUCCESS'}")
    print(f"Duration: {duration:.2f}s")
    print(f"Total Output Tokens/Chunks: {len(tokens)}")
    print(f"Output Preview:\n{full_output[:1200]}")
    if len(full_output) > 1200:
        print(f"... [truncated {len(full_output) - 1200} characters]")
    if error:
        print(f"Exception: {error}")
    return {
        "name": name,
        "success": error is None and len(full_output) > 0,
        "duration": duration,
        "output": full_output,
        "error": error
    }

async def main():
    api_key = load_real_api_key()
    if not api_key:
        print("ERROR: No valid GEMINI_API_KEY found!")
        sys.exit(1)

    print(f"Using GEMINI_API_KEY: {api_key[:8]}...{api_key[-4:]}")
    provider = GeminiProvider(api_key=api_key)

    results = []

    # -------------------------------------------------------------
    # TEST 1: Math Image (12 + 15 = ?)
    # -------------------------------------------------------------
    math_data_url = create_math_image("12 + 15 = ?")
    msg_math = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Solve the arithmetic equation shown in the uploaded image. Provide the step-by-step answer and final sum."},
                {"type": "image_url", "image_url": {"url": math_data_url}}
            ]
        }
    ]
    res1 = await run_test_case("1. Math Image Equation (12 + 15 = ?)", provider, msg_math, model="gemini-3.5-flash")
    results.append(res1)

    # -------------------------------------------------------------
    # TEST 2: Real Visual Scene / Photograph (User uploaded UI / Image)
    # -------------------------------------------------------------
    photo_path = "/Users/apple/.gemini/antigravity/brain/63d13956-3279-410c-b0f1-a939d73a6c90/.user_uploaded/media_1791906020741.png"
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as f:
            photo_b64 = base64.b64encode(f.read()).decode()
        photo_data_url = f"data:image/png;base64,{photo_b64}"
        msg_photo = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze and visually explain all elements in this image in detail. What visual components, icons, badges, colors, and layout are present?"},
                    {"type": "image_url", "image_url": {"url": photo_data_url}}
                ]
            }
        ]
        res2 = await run_test_case("2. Real Visual Image / UI Analysis", provider, msg_photo, model="gemini-3.5-flash")
        results.append(res2)
    else:
        print(f"Warning: Photo path {photo_path} not found, skipping Test 2")

    # -------------------------------------------------------------
    # TEST 3: Pure Image-Only Submission (Empty Text Prompt)
    # -------------------------------------------------------------
    msg_image_only = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": ""},
                {"type": "image_url", "image_url": {"url": math_data_url}}
            ]
        }
    ]
    res3 = await run_test_case("3. Image-Only Message (Empty User Text)", provider, msg_image_only, model="gemini-3.5-flash")
    results.append(res3)

    # -------------------------------------------------------------
    # TEST 4: Invalid API Key Error Handling
    # -------------------------------------------------------------
    fake_provider = GeminiProvider(api_key="AIzaSyDummyInvalidKeyForTesting123456789")
    res4 = await run_test_case("4. Invalid API Key Error Handling", fake_provider, msg_math, model="gemini-3.5-flash")
    results.append(res4)

    # Summary
    print(f"\n{'='*70}")
    print("LIVE VISION TEST SUMMARY")
    print(f"{'='*70}")
    for r in results:
        status_str = "PASSED" if r["success"] or ("Invalid API Key" in r["name"] and "**Error**" in r["output"]) else "FAILED"
        print(f"[{status_str}] {r['name']} (Duration: {r['duration']:.2f}s)")

if __name__ == "__main__":
    asyncio.run(main())
