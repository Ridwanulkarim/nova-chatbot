import io
import os
import sys
import json
import base64
import asyncio
from PIL import Image, ImageDraw, ImageFont

# Set up paths
sys.path.insert(0, os.path.abspath("backend"))

import app.database.base
from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from app.ai.provider_factory import ai_factory
from app.ai.gemini_provider import GeminiProvider

def get_or_create_test_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test_vision@pluto.ai").first()
        if not user:
            user = User(
                email="test_vision@pluto.ai",
                hashed_password=hash_password("TestPass123!"),
                full_name="Vision Tester",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id
    finally:
        db.close()

def create_image_data_url(img: Image.Image, format: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=format)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if format.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"

# 1. Create Image A: Math Question
def make_math_image():
    im = Image.new("RGB", (600, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    draw.rectangle([(10, 10), (590, 240)], outline=(50, 50, 150), width=3)
    draw.text((40, 40), "MATHEMATICS EXAM - QUESTION 1", fill=(0, 0, 120))
    draw.text((40, 90), "Solve the following quadratic equation for x:", fill=(20, 20, 20))
    draw.text((80, 140), "2x^2 - 8x + 6 = 0", fill=(180, 0, 0))
    draw.text((40, 190), "Show step-by-step algebraic working.", fill=(80, 80, 80))
    return create_image_data_url(im)

# 2. Create Image B: Code with Error
def make_code_error_image():
    im = Image.new("RGB", (650, 300), color=(30, 30, 30))
    draw = ImageDraw.Draw(im)
    draw.rectangle([(5, 5), (645, 295)], outline=(80, 80, 80), width=2)
    draw.text((25, 25), "# main.py", fill=(150, 150, 150))
    draw.text((25, 60), "def compute_average(values):", fill=(80, 200, 120))
    draw.text((55, 90), "return sum(values) / len(values)", fill=(240, 240, 240))
    draw.text((25, 130), "result = compute_average([])", fill=(240, 240, 240))
    draw.text((25, 160), "print(result)", fill=(240, 240, 240))
    draw.text((25, 210), "Traceback (most recent call last):", fill=(255, 100, 100))
    draw.text((25, 240), "ZeroDivisionError: division by zero", fill=(255, 80, 80))
    return create_image_data_url(im)

# 3. Create Image C: Flowchart Diagram with NO Text
def make_diagram_no_text():
    im = Image.new("RGB", (600, 300), color=(245, 247, 250))
    draw = ImageDraw.Draw(im)
    # Circle 1 (Start)
    draw.ellipse([(50, 110), (130, 190)], fill=(76, 175, 80), outline=(46, 125, 50), width=3)
    # Arrow 1
    draw.line([(130, 150), (220, 150)], fill=(60, 60, 60), width=4)
    draw.polygon([(220, 140), (240, 150), (220, 160)], fill=(60, 60, 60))
    # Rectangle (Process)
    draw.rectangle([(240, 110), (370, 190)], fill=(33, 150, 243), outline=(21, 101, 192), width=3)
    # Arrow 2
    draw.line([(370, 150), (460, 150)], fill=(60, 60, 60), width=4)
    draw.polygon([(460, 140), (480, 150), (460, 160)], fill=(60, 60, 60))
    # Diamond (Decision)
    draw.polygon([(530, 100), (580, 150), (530, 200), (480, 150)], fill=(156, 39, 176), outline=(106, 27, 154), width=3)
    return create_image_data_url(im)

# 4. Create Image D: Visual Landscape Scene with NO Text
def make_scene_no_text():
    im = Image.new("RGB", (600, 350), color=(135, 206, 235)) # Sky
    draw = ImageDraw.Draw(im)
    # Sun
    draw.ellipse([(480, 30), (560, 110)], fill=(255, 215, 0), outline=(255, 165, 0), width=2)
    # Grass ground
    draw.rectangle([(0, 240), (600, 350)], fill=(34, 139, 34))
    # Tree trunk
    draw.rectangle([(150, 170), (190, 270)], fill=(139, 69, 19))
    # Tree leaves
    draw.ellipse([(100, 70), (240, 200)], fill=(0, 100, 0))
    # Red apples on tree
    for x, y in [(130, 110), (170, 95), (200, 130), (150, 150)]:
        draw.ellipse([(x, y), (x + 14, y + 14)], fill=(220, 20, 60))
    return create_image_data_url(im)

async def run_test(name, prompt, data_url=None, expect_keywords=[]):
    print(f"\n==========================================")
    print(f"RUNNING: {name}")
    print(f"PROMPT: {prompt}")
    if data_url:
        print(f"IMAGE: data URL present ({len(data_url)} chars)")
    else:
        print("IMAGE: None (Text-only)")

    from app.schemas.message import MessageCreate
    from app.api.v1.endpoints.messages import stream_message
    from app.database.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_vision@pluto.ai").first()
    db.close()

    attachments = None
    if data_url is not None:
        attachments = [{
            "filename": f"{name.lower().replace(' ', '_')}.png",
            "media_type": "image",
            "data_url": data_url
        }]

    msg_in = MessageCreate(
        content=prompt,
        model="openai/gpt-oss-120b", # intentionally provide text model to test auto-routing!
        attachments=attachments,
        web_search=False
    )

    conv_id = f"test-conv-{os.urandom(4).hex()}"
    response = await stream_message(conversation_id=conv_id, msg_in=msg_in, current_user=user)

    collected_tokens = []
    async for chunk in response.body_iterator:
        line = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        for sub in line.split("\n"):
            sub = sub.strip()
            if sub.startswith("data: "):
                try:
                    payload = json.loads(sub[6:])
                    if "token" in payload:
                        collected_tokens.append(payload["token"])
                except Exception:
                    pass

    full_output = "".join(collected_tokens).strip()
    print("\n--- MODEL RESPONSE ---")
    print(full_output[:500] + ("..." if len(full_output) > 500 else ""))
    print("----------------------")

    matched = []
    for kw in expect_keywords:
        if kw.lower() in full_output.lower():
            matched.append(kw)

    passed = len(matched) == len(expect_keywords)
    print(f"VERDICT: {'PASSED [OK]' if passed else 'FAILED [X]'}")
    print(f"Matched keywords: {matched} / {expect_keywords}")
    return passed

async def main():
    get_or_create_test_user()
    print("Test user initialized.")

    results = {}

    # Test A: Math Question
    results["Test A (Math)"] = await run_test(
        "Test A - Math Quadratic Equation",
        "Solve this question step by step.",
        data_url=make_math_image(),
        expect_keywords=["1", "3", "quadratic"]
    )

    # Test B: Code with Error
    results["Test B (Code Error)"] = await run_test(
        "Test B - Python Code Screenshot",
        "What error is occurring and how do I fix it?",
        data_url=make_code_error_image(),
        expect_keywords=["zerodivisionerror", "division by zero", "empty"]
    )

    # Test C: Flowchart without Text
    results["Test C (Flowchart No Text)"] = await run_test(
        "Test C - Pure Flowchart",
        "Describe the shapes and flowchart structure shown in this image.",
        data_url=make_diagram_no_text(),
        expect_keywords=["circle", "rectangle", "arrow"]
    )

    # Test D: Scene without Text
    results["Test D (Visual Scene)"] = await run_test(
        "Test D - Everyday Scene",
        "What is in this picture? Describe what you see.",
        data_url=make_scene_no_text(),
        expect_keywords=["tree", "sun", "apple"]
    )

    # Test E: Text-only
    results["Test E (Text Query)"] = await run_test(
        "Test E - Text Only",
        "What is the speed of light in vacuum in meters per second?",
        data_url=None,
        expect_keywords=["299", "speed of light"]
    )

    # Test F: Invalid Image Upload
    print("\n==========================================")
    print("RUNNING: Test F (Corrupted Image)")
    from app.schemas.message import MessageCreate
    from app.api.v1.endpoints.messages import stream_message
    from app.database.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == "test_vision@pluto.ai").first()
    db.close()

    corrupt_msg = MessageCreate(
        content="Solve this.",
        model="openai/gpt-oss-120b",
        attachments=[{
            "filename": "corrupted.png",
            "media_type": "image",
            "data_url": "data:image/png;base64,CORRUPTED_BYTES_NOT_VALID_IMAGE"
        }]
    )
    conv_id = f"test-conv-{os.urandom(4).hex()}"
    resp_f = await stream_message(conversation_id=conv_id, msg_in=corrupt_msg, current_user=user)
    tokens_f = []
    async for chunk in resp_f.body_iterator:
        line = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        for sub in line.split("\n"):
            sub = sub.strip()
            if sub.startswith("data: "):
                try:
                    payload = json.loads(sub[6:])
                    if "token" in payload:
                        tokens_f.append(payload["token"])
                except Exception:
                    pass
    out_f = "".join(tokens_f)
    print("Corrupted image response:", out_f)
    test_f_passed = "Image Processing Error" in out_f or "Corrupted" in out_f or "Failed to decode" in out_f
    results["Test F (Corrupted Image)"] = test_f_passed
    print(f"VERDICT: {'PASSED [OK]' if test_f_passed else 'FAILED [X]'}")

    print("\n==========================================")
    print("TEST SUITE SUMMARY:")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    all_ok = all(results.values())
    print(f"OVERALL RESULT: {'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
