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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
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
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

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
        temp = current_user.settings.temperature if current_user.settings else 0.7
        sys_instructions = current_user.settings.system_instructions if current_user.settings else ""
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

    # Multimodal media attachments & Vision OCR context
    multimodal_context = ""
    vision_blocks = []

    if msg_in.attachments:
        for a in msg_in.attachments:
            m_type = (a.get("media_type") or a.get("type", "file")).lower()
            f_name = a.get("filename") or a.get("name", "file")
            f_url = a.get("url", "")
            
            # Check if this is an image/screenshot
            is_image = m_type == "image" or any(f_name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"])
            if is_image and f_url:
                if f_url.startswith("data:image"):
                    temp_img_path = None
                    try:
                        _, b64data = f_url.split(",", 1)
                        img_bytes = base64.b64decode(b64data)
                        temp_img_path = os.path.join(tempfile.gettempdir(), f"vision_{uuid.uuid4().hex[:8]}.png")
                        with open(temp_img_path, "wb") as f_tmp:
                            f_tmp.write(img_bytes)
                        analysis = vision_service.analyze_image(temp_img_path)
                        vision_blocks.append(vision_service.format_vision_context(f_name, analysis))
                    except Exception:
                        vision_blocks.append(f"- [IMAGE ATTACHED] {f_name} (Multimodal visual data included)")
                    finally:
                        if temp_img_path and os.path.exists(temp_img_path):
                            try:
                                os.remove(temp_img_path)
                            except Exception:
                                pass
                else:
                    local_fname = os.path.basename(f_url)
                    local_path = os.path.join(settings.UPLOAD_DIR, local_fname)
                    if not os.path.exists(local_path):
                        local_path = os.path.join(tempfile.gettempdir(), local_fname)
                    if os.path.exists(local_path):
                        analysis = vision_service.analyze_image(local_path)
                        vision_blocks.append(vision_service.format_vision_context(f_name, analysis))
                    else:
                        vision_blocks.append(f"- [IMAGE] {f_name} (URL: {f_url})")
            else:
                vision_blocks.append(f"- [{m_type.upper()}] {f_name} (URL: {f_url})")

    # Auto-match: If user mentions a filename (e.g. 'Screenshot 2026-10-11 at 9.59.40 PM') without attachment, resolve it from uploaded docs
    db_find = SessionLocal()
    try:
        user_docs = db_find.query(Document).filter(Document.user_id == current_user.id).all()
        for d in user_docs:
            clean_base = os.path.splitext(d.filename)[0].strip().lower()
            if clean_base and clean_base in msg_in.content.lower():
                # Avoid duplicate if already in vision_blocks
                if not any(d.filename in vb for vb in vision_blocks):
                    analysis = vision_service.analyze_image(d.file_path)
                    vision_blocks.append(vision_service.format_vision_context(d.filename, analysis))
    finally:
        db_find.close()

    if vision_blocks:
        multimodal_context = "\n\n".join([
            "--- VISUAL & ATTACHMENT CONTEXT FOR PLUTO AI ---",
            *vision_blocks,
            "Carefully review the recognized visual text, OCR layout, and image details above to answer the user's questions about their screenshot/image thoroughly and accurately.",
            "--- END ATTACHMENT CONTEXT ---"
        ])

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
    if multimodal_context:
        base_system += f"\n\n{multimodal_context}"
    if rag_context:
        base_system += f"\n\n{rag_context}"
    if search_context:
        base_system += f"\n\n{search_context}"

    llm_messages.append({"role": "system", "content": base_system})

    # Add historical messages (limit to last 10 messages for token safety)
    for hist_msg in history[-10:]:
        llm_messages.append({"role": hist_msg.role, "content": hist_msg.content})

    # Resolve AI provider
    provider, resolved_model = ai_factory.get_provider_for_model(model_name)
    if not provider:
        async def err_gen():
            error_payload = {
                "error": "No AI providers configured. Please set OPENAI_API_KEY or GROQ_API_KEY in the server environment."
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
        finally:
            # Safely persist assistant message to DB
            final_content = "".join(full_assistant_reply).strip()
            if final_content:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    msg.feedback = feedback_in.feedback
    db.commit()
    return {"message": "Feedback recorded", "feedback": msg.feedback}
