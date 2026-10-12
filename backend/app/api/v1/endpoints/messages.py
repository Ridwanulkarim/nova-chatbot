import os
import json
import asyncio
import uuid
import base64
import tempfile
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.session import get_db, SessionLocal
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.schemas.message import MessageCreate, MessageFeedback, MessageOut
from app.api.deps import get_current_user
from app.ai.provider_factory import ai_factory
from app.ai.search_service import search_service
from app.ai.rag_service import rag_service
from app.core.config import settings

router = APIRouter()

@router.get("/{conversation_id}/messages", response_model=List[MessageOut])
def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.user_id = current_user.id
            db.commit()
    if not conv:
        return []
    return conv.messages

from app.core.quota import check_and_consume_message_quota, check_and_consume_image_quota
from app.ai.image_service import image_service
from app.ai.vision_service import vision_service
from app.ai.math_service import math_service

@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            if conv.user_id != current_user.id:
                conv.user_id = current_user.id
                db.commit()
        else:
            default_mod = settings.DEFAULT_MODEL
            try:
                if current_user and getattr(current_user, "settings", None) and current_user.settings.default_model:
                    default_mod = current_user.settings.default_model
            except Exception:
                pass
            conv = Conversation(
                id=conversation_id,
                user_id=current_user.id,
                title="New Chat",
                model=msg_in.model or default_mod
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Check and consume daily message quota
        check_and_consume_message_quota(db, current_user.id)
        
        # Save user message immediately to database with attachments
        attachments_json = json.dumps(msg_in.attachments) if msg_in.attachments else None
        user_message = Message(
            conversation_id=conv.id,
            role="user",
            content=msg_in.content,
            attachments=attachments_json
        )
        db.add(user_message)
        conv.updated_at = datetime.utcnow()
        
        # Auto-update title if it's the first message
        updated_title = None
        if conv.title == "New Chat":
            clean_first = " ".join(msg_in.content.strip().split()[:6])
            conv.title = clean_first[:40] if clean_first else "New Chat"
            updated_title = conv.title
            
        db.commit()
        db.refresh(user_message)

        # Build context history from prior messages (sliding window of last 12 messages)
        history = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.asc()).all()

        model_name = msg_in.model or conv.model
        temp = 0.7
        sys_instructions = ""
        try:
            if current_user and getattr(current_user, "settings", None):
                temp = current_user.settings.temperature or 0.7
                sys_instructions = current_user.settings.system_instructions or ""
        except Exception:
            pass
    finally:
        db.close()

    # Detect natural language image generation intent
    clean_low = msg_in.content.strip().lower()
    is_img_prompt = (
        clean_low.startswith(("/image", "generate an image", "create an image", "draw an image", "draw a picture", "make an image"))
        or "generate an image of" in clean_low
        or "create a picture of" in clean_low
    )
    if is_img_prompt:
        # Extract prompt
        img_prompt = msg_in.content
        for prefix in ["/image", "generate an image of", "generate an image", "create an image of", "create an image", "draw a picture of", "draw an image of", "make an image of"]:
            if clean_low.startswith(prefix):
                img_prompt = msg_in.content[len(prefix):].strip(" :,-")
                break
        if not img_prompt:
            img_prompt = msg_in.content

        async def sse_image_stream():
            try:
                # Check and consume image quota
                db_quota = SessionLocal()
                try:
                    check_and_consume_image_quota(db_quota, current_user.id)
                finally:
                    db_quota.close()

                init_msg = json.dumps({'token': '🎨 Generating photorealistic image with AI...\n\n'})
                yield f"data: {init_msg}\n\n"
                img_result = await image_service.generate_image(prompt=img_prompt)
                image_card = f"![{img_prompt}]({img_result['url']})\n\n**Prompt:** *{img_prompt}*\n\n[📥 Download Image]({img_result['url']})"
                card_msg = json.dumps({'token': image_card})
                yield f"data: {card_msg}\n\n"
                
                # Save assistant message
                db_save = SessionLocal()
                try:
                    asst_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=f"![{img_prompt}]({img_result['url']})\n\n**Prompt:** *{img_prompt}*\n\n[📥 Download Image]({img_result['url']})",
                        model="flux-image-generator"
                    )
                    db_save.add(asst_msg)
                    db_save.commit()
                    db_save.refresh(asst_msg)
                    yield f"data: {json.dumps({'done': True, 'message_id': asst_msg.id, 'title': updated_title})}\n\n"
                finally:
                    db_save.close()
            except Exception as e:
                yield f"data: {json.dumps({'error': f'Image generation failed: {str(e)}'})}\n\n"

        return StreamingResponse(
            sse_image_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    # Perform optional Web Search
    search_context = ""
    citations_data = []
    if msg_in.web_search:
        results = await search_service.search(msg_in.content)
        if results:
            search_context = search_service.format_search_context(results)
            citations_data = results

    # Perform optional Document RAG Retrieval
    rag_context = ""
    db_rag = SessionLocal()
    try:
        if msg_in.file_ids or True: # Check if user has uploaded docs
            chunks = rag_service.search_relevant_chunks(
                db_rag,
                user_id=current_user.id,
                query=msg_in.content,
                file_ids=msg_in.file_ids
            )
            if chunks:
                rag_context = rag_service.format_rag_context(chunks)
    finally:
        db_rag.close()

    # Multimodal media attachments & Vision processing
    attached_images = []
    auxiliary_ocr_texts = []
    image_validation_errors = []

    if msg_in.attachments:
        for a in msg_in.attachments:
            m_type = (a.get("media_type") or a.get("type", "file")).lower()
            f_name = a.get("filename") or a.get("name", "file")
            f_url = a.get("data_url") or a.get("url", "")

            # Check if this is an image/screenshot
            is_image = m_type == "image" or any(
                f_name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
            )
            if is_image:
                data_url = f_url if (f_url and f_url.startswith("data:image")) else None
                if not data_url and f_url:
                    # Resolve from local file path or upload directory
                    candidates = []
                    if not f_url.startswith("http"):
                        base = os.path.basename(f_url)
                        candidates.append(os.path.join(settings.UPLOAD_DIR, base))
                        candidates.append(os.path.join(tempfile.gettempdir(), base))
                    if f_name:
                        candidates.append(os.path.join(settings.UPLOAD_DIR, f_name))
                        candidates.append(os.path.join(tempfile.gettempdir(), f_name))
                    for p in candidates:
                        if os.path.exists(p) and os.path.getsize(p) > 0:
                            try:
                                import mimetypes
                                mime, _ = mimetypes.guess_type(p)
                                if not mime or not mime.startswith("image/"):
                                    mime = "image/jpeg"
                                with open(p, "rb") as f_img:
                                    b64_raw = base64.b64encode(f_img.read()).decode("utf-8")
                                data_url = f"data:{mime};base64,{b64_raw}"
                                break
                            except Exception:
                                pass

                if data_url:
                    val_res = vision_service.validate_and_optimize(data_url)
                    if not val_res.get("valid"):
                        image_validation_errors.append(f"Image `{f_name}`: {val_res.get('error')}")
                    else:
                        attached_images.append({
                            "filename": f_name,
                            "data_url": val_res["data_url"],
                            "mime_type": val_res.get("mime_type", "image/jpeg"),
                            "dimensions": val_res.get("dimensions", "unknown"),
                            "size_bytes": val_res.get("size_bytes", 0),
                        })
                else:
                    image_validation_errors.append(f"Image `{f_name}`: Missing image data or unreadable image file.")

                # Optional supporting OCR text if available
                ext_text = a.get("extracted_text", "").strip()
                if ext_text and len(ext_text) > 15:
                    auxiliary_ocr_texts.append(f"--- Text recognized from {f_name} ---\n{ext_text}")

    # If all uploaded images failed validation, return immediate descriptive error
    if image_validation_errors and not attached_images:
        err_msg = "⚠️ **Image Processing Error**:\n" + "\n".join(f"- {e}" for e in image_validation_errors)
        async def err_gen():
            yield f"data: {json.dumps({'token': err_msg})}\n\n"
            yield f"data: {json.dumps({'done': True, 'error': err_msg})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    # Construct LLM prompt message sequence
    llm_messages = []
    base_system = (
        "You are Pluto AI, an advanced, intelligent, truthful, conversational, and helpful multimodal AI assistant like ChatGPT, Claude, and Gemini.\n"
        "Communicate naturally, directly, and concisely. Understand the user's practical intent rather than over-complicating questions with unintended abstractions.\n"
        "You are completely fluent in both Bengali (বাংলা) and English. When a user writes, speaks, or asks in Bengali (or Bengali script / Banglish), respond in natural, grammatically correct, eloquent, and culturally authentic Bengali (বাংলা).\n"
        "When requested for translation or in voice translation mode, provide immediate, accurate, and idiomatic translations between Bengali and English.\n"
        "When answering questions like '1+1 how', explain clearly how 1 + 1 equals 2 using simple arithmetic and intuitive examples (e.g. starting with 1 unit and adding 1 more unit gives 2 units).\n"
        "Never interpret conversational English words (such as 'how', 'why', 'what', 'please') as literal algebraic variable multiplications.\n"
        "Format mathematical expressions cleanly using standard LaTeX ($...$ for inline, $$...$$ for display equations)."
    )
    if sys_instructions:
        base_system += f"\n\nUser Custom Instructions:\n{sys_instructions}"
    if conv.system_prompt:
        base_system += f"\n\nConversation Directives:\n{conv.system_prompt}"

    # Mathematical Reasoning & Symbolic Verification (SymPy Engine)
    math_context = ""
    if math_service.is_math_query(msg_in.content):
        sol = math_service.solve_expression(msg_in.content)
        if sol.get("success"):
            math_context = math_service.format_math_context(msg_in.content, sol)

    if math_context:
        base_system += f"\n\n{math_context}"
    if rag_context:
        base_system += f"\n\n{rag_context}"
    if search_context:
        base_system += f"\n\n{search_context}"

    llm_messages.append({"role": "system", "content": base_system})

    # Add historical messages (clean textual representation for prior turns)
    for hist_msg in history[-10:]:
        llm_messages.append({"role": hist_msg.role, "content": hist_msg.content})

    # Build latest user turn with direct native multimodal image parts
    if attached_images:
        clean_user_prompt = msg_in.content.strip()
        low = clean_user_prompt.lower()
        is_solve_intent = (
            not clean_user_prompt
            or any(w in low for w in [
                "answer", "anser", "ans", "solve", "solution", "ques", "question",
                "উত্তর", "সমাধান", "প্রশ্ন", "exam", "paper", "explain", "ব্যাখ্যা"
            ])
            or len(clean_user_prompt) < 25
        )

        if not clean_user_prompt:
            clean_user_prompt = (
                "Please analyze this uploaded image thoroughly. "
                "If it contains questions, problems, or exercises (e.g. an exam paper, homework, or textbook page), "
                "solve ALL questions step-by-step with complete, clear answers. "
                "If it contains diagrams, flowcharts, code screenshots, UI screens, or photographs, "
                "explain and describe all visible visual contents in detail."
            )
        elif is_solve_intent:
            clean_user_prompt = (
                f"{clean_user_prompt}\n\n"
                "Please solve and provide comprehensive, step-by-step answers for ALL questions "
                "and problems visible in the attached image in complete detail."
            )

        if auxiliary_ocr_texts:
            clean_user_prompt += "\n\n" + "\n\n".join(auxiliary_ocr_texts)

        # Structure as OpenAI/Gemini standard multimodal parts array
        user_parts = [{"type": "text", "text": clean_user_prompt}]
        for img in attached_images:
            user_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": img["data_url"]
                }
            })

        # Replace or add latest user turn with multimodal structure
        if llm_messages and llm_messages[-1]["role"] == "user":
            llm_messages[-1]["content"] = user_parts
        else:
            llm_messages.append({"role": "user", "content": user_parts})

    # Resolve AI provider: Auto-route to a genuine vision-capable provider if images are present
    if attached_images:
        provider, resolved_model = ai_factory.get_vision_capable_provider(model_name)
    else:
        provider, resolved_model = ai_factory.get_provider_for_model(model_name)

    if not provider:
        async def err_gen():
            error_payload = {
                "error": "No AI providers configured. Please set GEMINI_API_KEY or GROQ_API_KEY in the server environment."
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    # Generator for SSE Streaming
    async def sse_event_stream():
        full_assistant_reply = []
        try:
            async for token in provider.stream_chat(
                messages=llm_messages,
                model=resolved_model,
                temperature=temp
            ):
                full_assistant_reply.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected early or pressed Stop
            pass
        except Exception as stream_err:
            err_msg = f"\n\n**Error**: An unexpected error occurred while processing the response: {str(stream_err)}"
            full_assistant_reply.append(err_msg)
            yield f"data: {json.dumps({'token': err_msg})}\n\n"
        finally:
            # Safely persist assistant message to DB
            final_content = "".join(full_assistant_reply).strip()
            if not final_content:
                final_content = "⚠️ The AI vision model did not return a response. Please try again with a clearer image or prompt."
                yield f"data: {json.dumps({'token': final_content})}\n\n"

            db_save = SessionLocal()
            try:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_content,
                    model=resolved_model,
                    citations=json.dumps(citations_data) if citations_data else None
                )
                db_save.add(assistant_msg)
                db_save.commit()
                db_save.refresh(assistant_msg)
                done_payload = {
                    "done": True,
                    "message_id": assistant_msg.id,
                    "title": updated_title,
                    "citations": citations_data
                }
                yield f"data: {json.dumps(done_payload)}\n\n"
            except Exception as save_err:
                db_save.rollback()
            finally:
                db_save.close()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/{message_id}/feedback")
def set_message_feedback(
    message_id: str,
    feedback_in: MessageFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    msg = db.query(Message).join(Conversation).filter(
        Message.id == message_id,
        Conversation.user_id == current_user.id
    ).first()
    if not msg:
        msg = db.query(Message).filter(Message.id == message_id).first()
    if msg:
        msg.feedback = feedback_in.feedback
        db.commit()
    return {"message": "Feedback recorded", "feedback": feedback_in.feedback}

