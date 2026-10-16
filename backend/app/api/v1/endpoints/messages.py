import os
import json
import logging
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

logger = logging.getLogger("pluto.messages")

router = APIRouter()

from datetime import datetime, timezone
from sqlalchemy import desc
from app.models.memory import UserMemory
from app.core.quota import (
    check_and_consume_message_quota,
    check_and_consume_image_quota,
    refund_message_quota,
    refund_image_quota
)
from app.ai.orchestrator import tool_orchestrator
from app.ai.image_service import image_service, detect_image_request
from app.ai.vision_service import vision_service
from app.ai.math_service import math_service

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

def generate_smart_title(content: str) -> str:
    """
    Generate a concise, professional, and relevant title (3-6 words) from the user's initial message.
    Cleans out greetings, filler words, question prefixes, and markdown syntax.
    """
    if not content or not isinstance(content, str):
        return "New Chat"

    raw = content.strip()
    clean_low = raw.lower()

    # Common greetings and conversational starters
    greetings = {
        "hello": "Hello & Greeting",
        "hi": "Hello & Greeting",
        "hey": "Hello & Greeting",
        "hi there": "Hello & Greeting",
        "hello pluto": "Hello & Greeting",
        "hola": "Hello & Greeting",
        "salam": "Greetings & Assistance",
        "assalamu alaikum": "Greetings & Assistance",
        "ki khobor": "Casual Conversation",
        "ki kora laghbe": "Guidance & Assistance",
        "ki kora lagbe": "Guidance & Assistance",
        "help": "Help & Support",
    }
    for greet_key, greet_title in greetings.items():
        if clean_low == greet_key or clean_low.startswith(greet_key + " ") or clean_low.startswith(greet_key + "!"):
            return greet_title

    # Image generation intent titles
    is_img, img_subj = detect_image_request(raw)
    if is_img and img_subj:
        words = [w.capitalize() for w in img_subj.split()[:5]]
        return f"Image: {' '.join(words)}"[:38]

    # Strip conversational question fillers
    fillers = [
        "can you please tell me about",
        "can you please help me with",
        "can you help me with",
        "can you help me",
        "can you explain",
        "could you please",
        "could you tell me",
        "i want you to",
        "i would like to",
        "how do i",
        "how to",
        "what is",
        "tell me about",
        "write a",
        "please",
    ]
    trimmed = raw
    for filler in fillers:
        if clean_low.startswith(filler):
            trimmed = raw[len(filler):].strip(" :,-?")
            break

    words = [w for w in trimmed.split() if w]
    if not words:
        words = raw.split()[:5]

    # Capitalize and take top 4-5 words
    title_words = [w.capitalize() for w in words[:5]]
    title = " ".join(title_words).strip(" .,?!:;-")
    if not title:
        title = "New Chat"
    return title[:38]

@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    # Detect natural language image generation intent first to avoid double quota deduction
    is_img_prompt, img_prompt = detect_image_request(msg_in.content)

    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conv:
            # Prevent IDOR: check if conversation belongs to another user
            other_conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if other_conv and other_conv.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            # Seamlessly recreate conversation for current_user if missing (e.g. serverless cold start)
            conv = Conversation(
                id=conversation_id,
                user_id=current_user.id,
                title="New Chat",
                model=msg_in.model or settings.DEFAULT_MODEL
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Consume quota according to request type (do not double-deduct)
        if is_img_prompt:
            check_and_consume_image_quota(db, current_user.id)
        else:
            check_and_consume_message_quota(db, current_user.id)
        
        # Save user message immediately to database with attachments
        attachments_json = json.dumps(msg_in.attachments) if msg_in.attachments else None
        user_message = Message(
            conversation_id=conv.id,
            role="user",
            content=msg_in.content,
            attachments=attachments_json,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user_message)
        conv.updated_at = datetime.now(timezone.utc)
        
        # Auto-update title if it's the first message or default title
        updated_title = None
        if not conv.title or conv.title.strip() in ("New Chat", "Live Test", "Untitled"):
            conv.title = generate_smart_title(msg_in.content)
            updated_title = conv.title
            
        db.commit()
        db.refresh(user_message)

        # Build context history from prior messages (sliding window of last 12 messages)
        history = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).limit(12).all()
        history.reverse()

        model_name = msg_in.model or conv.model
        temp = 0.7
        sys_instructions = ""
        memory_items = []
        try:
            if current_user and getattr(current_user, "settings", None):
                # Preserve 0.0 temperature properly
                if current_user.settings.temperature is not None:
                    temp = current_user.settings.temperature
                sys_instructions = current_user.settings.system_instructions or ""
                if current_user.settings.memory_enabled:
                    mems = db.query(UserMemory).filter(UserMemory.user_id == current_user.id).all()
                    memory_items = [m.content for m in mems if m.content]
        except Exception:
            pass
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Error preparing stream message in conversation {conversation_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Message setup failed: {str(exc)}"
        )
    finally:
        db.close()

    if is_img_prompt:
        if not img_prompt:
            img_prompt = msg_in.content

        async def sse_image_stream():
            try:
                init_msg = json.dumps({'token': '⚡ Generating high-speed image with Fast Turbo Mode...\n\n'})
                yield f"data: {init_msg}\n\n"
                img_result = await image_service.generate_image(prompt=img_prompt, model="turbo")
                image_card = f"![{img_prompt}]({img_result['url']})\n\n**Prompt:** *{img_prompt}*\n\n⚡ *Generated in Fast Turbo Mode (Watermark-free)*"
                card_msg = json.dumps({'token': image_card})
                yield f"data: {card_msg}\n\n"
                
                # Save assistant message
                db_save = SessionLocal()
                try:
                    asst_msg = Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=image_card,
                        model="fast-turbo-image-generator",
                        created_at=datetime.now(timezone.utc)
                    )
                    db_save.add(asst_msg)
                    db_save.commit()
                    db_save.refresh(asst_msg)
                    yield f"data: {json.dumps({'done': True, 'message_id': asst_msg.id, 'title': updated_title})}\n\n"
                finally:
                    db_save.close()
            except Exception as e:
                # Refund image quota on failure
                db_ref = SessionLocal()
                try:
                    refund_image_quota(db_ref, current_user.id)
                finally:
                    db_ref.close()
                yield f"data: {json.dumps({'error': f'Image generation failed: {str(e)}'})}\n\n"

        return StreamingResponse(
            sse_image_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    # Perform optional Web Search (explicit flag OR enabled in UserSettings with search-intent query)
    should_search = bool(msg_in.web_search)
    if not should_search and current_user and getattr(current_user, "settings", None) and current_user.settings.web_search_enabled:
        intent = tool_orchestrator.analyze_intent(msg_in.content, has_attachments=bool(msg_in.attachments))
        if intent.get("route") == "WEB_SEARCH":
            should_search = True

    search_context = ""
    citations_data = []
    if should_search:
        results = await search_service.search(msg_in.content)
        if results:
            search_context = search_service.format_search_context(results)
            citations_data = results

    # Perform optional Document RAG Retrieval (only for explicitly attached non-image documents)
    rag_context = ""
    if msg_in.file_ids:
        db_rag = SessionLocal()
        try:
            chunks = rag_service.search_relevant_chunks(
                db_rag,
                user_id=current_user.id,
                query=msg_in.content,
                file_ids=msg_in.file_ids
            )
            # Filter out any legacy image chunks that might exist in DB
            img_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")
            doc_chunks = [
                c for c in chunks
                if not c.get("filename", "").lower().endswith(img_exts)
                and "Visual Media Analysis" not in c.get("content", "")
            ]
            if doc_chunks:
                rag_context = rag_service.format_rag_context(doc_chunks)
        finally:
            db_rag.close()

    # Helper to extract valid image attachments from a list of attachment dicts (or JSON string)
    def _extract_valid_images(att_list, record_errors=True):
        if isinstance(att_list, str):
            try:
                att_list = json.loads(att_list)
            except Exception:
                return []
        extracted = []
        for a in (att_list or []):
            if not isinstance(a, dict):
                continue
            m_type = (a.get("media_type") or a.get("type", "file")).lower()
            f_name = a.get("filename") or a.get("name", "file")
            f_url = a.get("data_url") or a.get("url", "")

            is_image = m_type == "image" or any(
                f_name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
            ) or (isinstance(f_url, str) and f_url.startswith("data:image"))

            if is_image:
                data_url = f_url if (isinstance(f_url, str) and f_url.startswith("data:image")) else None
                if not data_url and f_url:
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
                        if record_errors:
                            image_validation_errors.append(f"Image `{f_name}`: {val_res.get('error')}")
                    else:
                        extracted.append({
                            "filename": f_name,
                            "data_url": val_res["data_url"],
                            "mime_type": val_res.get("mime_type", "image/jpeg"),
                            "dimensions": val_res.get("dimensions", "unknown"),
                            "size_bytes": val_res.get("size_bytes", 0),
                        })
                elif record_errors:
                    image_validation_errors.append(f"Image `{f_name}`: Missing image data or unreadable image file.")

                ext_text = (a.get("extracted_text") or "").strip()
                if ext_text and len(ext_text) > 15:
                    auxiliary_ocr_texts.append(f"--- Text recognized from {f_name} ---\n{ext_text}")
        return extracted

    # Helper to extract document attachments directly from attachments (stateless & serverless resilient)
    def _extract_document_contexts(att_list):
        if isinstance(att_list, str):
            try:
                att_list = json.loads(att_list)
            except Exception:
                return []
        doc_contexts = []
        for a in (att_list or []):
            if not isinstance(a, dict):
                continue
            f_name = a.get("filename") or a.get("name", "document")
            m_type = (a.get("media_type") or a.get("type", "document")).lower()
            ext = os.path.splitext(f_name)[1].lower()
            is_image = m_type == "image" or any(
                f_name.lower().endswith(e) for e in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
            )
            if is_image:
                continue

            # 1. Text already pre-extracted in attachment
            text = (a.get("extracted_text") or "").strip()

            # 2. Extract from data_url if base64 encoded document
            if not text:
                f_url = a.get("data_url") or a.get("url", "")
                if isinstance(f_url, str) and f_url.startswith("data:"):
                    try:
                        _, b64_part = f_url.split(",", 1)
                        raw_bytes = base64.b64decode(b64_part)
                        text = rag_service.extract_text_from_bytes(raw_bytes, filename=f_name, mime_type=a.get("mime_type", ""))
                    except Exception as b64_err:
                        logger.warning(f"Error decoding document data_url for {f_name}: {b64_err}")
                elif isinstance(f_url, str) and not f_url.startswith("http"):
                    base = os.path.basename(f_url)
                    for candidate in [
                        os.path.join(settings.UPLOAD_DIR, base),
                        os.path.join(tempfile.gettempdir(), base),
                        os.path.join(settings.UPLOAD_DIR, f_name),
                        os.path.join(tempfile.gettempdir(), f_name),
                    ]:
                        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                            text = rag_service.extract_text_from_file(candidate, a.get("mime_type", ""))
                            if text:
                                break

            if text:
                clean_snippet = text[:50000].strip()
                doc_contexts.append({
                    "filename": f_name,
                    "content": clean_snippet,
                    "char_count": len(clean_snippet)
                })

        return doc_contexts

    # Multimodal media attachments & Vision processing
    attached_images = []
    attached_documents = []
    auxiliary_ocr_texts = []
    image_validation_errors = []

    if msg_in.attachments:
        attached_images = _extract_valid_images(msg_in.attachments, record_errors=True)
        attached_documents = _extract_document_contexts(msg_in.attachments)

    # Multi-turn Vision Continuity: If the user didn't attach a new image on this turn,
    # check if a recent user message in this conversation had an uploaded image
    if not attached_images and not image_validation_errors and history:
        for past_msg in reversed(history[:-1][-6:]):
            if past_msg.role == "user" and getattr(past_msg, "attachments", None):
                carried = _extract_valid_images(past_msg.attachments, record_errors=False)
                if carried:
                    attached_images = carried
                    break

    # Multi-turn Document Continuity: If the user didn't attach a document on this turn,
    # carry forward document context from a recent user turn (e.g. Turn 1: uploads PDF, Turn 2: "pdf ta bujhai dao")
    if not attached_documents and history:
        for past_msg in reversed(history[:-1][-6:]):
            if past_msg.role == "user" and getattr(past_msg, "attachments", None):
                carried_docs = _extract_document_contexts(past_msg.attachments)
                if carried_docs:
                    attached_documents = carried_docs
                    break

    # If all uploaded images on the current turn failed validation, return immediate descriptive error
    if image_validation_errors and not attached_images:
        err_msg = "⚠️ **Image Processing Error**:\n" + "\n".join(f"- {e}" for e in image_validation_errors)
        async def err_gen():
            yield f"data: {json.dumps({'token': err_msg})}\n\n"
            yield f"data: {json.dumps({'done': True, 'error': err_msg})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    # Construct LLM prompt message sequence
    llm_messages = []
    base_system = (
        "You are Pluto AI, an advanced, intelligent, truthful, conversational, and helpful multimodal AI assistant with direct native vision capabilities.\n"
        "Communicate naturally, directly, and concisely. Understand the user's practical intent rather than over-complicating questions with unintended abstractions.\n"
        "You are completely fluent in both Bengali (বাংলা) and English. When a user writes, speaks, or asks in Bengali (or Bengali script / Banglish), respond in natural, grammatically correct, eloquent, and culturally authentic Bengali (বাংলা).\n"
        "VISION CAPABILITY DIRECTIVE: When an image is attached, you can see the actual pixels, text, equations, handwriting, diagrams, code screenshots, UI elements, and photographs directly. "
        "NEVER claim that you cannot see images, NEVER claim that an image contains no recognizable text because of OCR, and NEVER output generic OCR failure disclaimers. Always inspect and explain the visual content directly.\n"
        "When requested for translation or in voice translation mode, provide immediate, accurate, and idiomatic translations between Bengali and English.\n"
        "When answering questions like '1+1 how', explain clearly how 1 + 1 equals 2 using simple arithmetic and intuitive examples (e.g. starting with 1 unit and adding 1 more unit gives 2 units).\n"
        "Never interpret conversational English words (such as 'how', 'why', 'what', 'please') as literal algebraic variable multiplications.\n"
        "Format mathematical expressions cleanly using standard LaTeX ($...$ for inline, $$...$$ for display equations)."
    )
    if sys_instructions:
        base_system += f"\n\nUser Custom Instructions:\n{sys_instructions}"
    if memory_items:
        base_system += "\n\nRemembered User Information & Preferences (Memory):\n" + "\n".join(f"- {m}" for m in memory_items)
    if conv.system_prompt:
        base_system += f"\n\nConversation Directives:\n{conv.system_prompt}"

    # Mathematical Reasoning & Symbolic Verification (SymPy Engine)
    math_context = ""
    if math_service.is_math_query(msg_in.content):
        sol = math_service.solve_expression(msg_in.content)
        if sol.get("success"):
            math_context = math_service.format_math_context(msg_in.content, sol)

    # Document Comprehension Context (stateless & RAG fallback)
    document_context = ""
    if attached_documents:
        doc_lines = [
            "--- BEGIN ATTACHED USER DOCUMENTS ---",
            "CRITICAL DIRECTIVE: The user has uploaded the following document(s). You have direct, complete access to their text contents below.",
            "Carefully analyze, explain, summarize, or answer questions strictly using the actual information and facts provided in these documents.",
            "NEVER claim that you cannot open, access, or read the document.",
            "NEVER produce generic boilerplate templates with placeholder brackets (such as *[PDF-এর শিরোনাম এখানে]* or *[লেখক বা সংস্থা]*).",
            "When the user asks in Bengali (e.g. 'pdf ta bujhai dao' or 'explain this pdf'), explain and summarize the actual content, key sections, and findings in fluent, authentic Bengali.\n"
        ]
        for d in attached_documents:
            doc_lines.append(f"### Document: {d['filename']} ###\n{d['content']}\n")
        doc_lines.append("--- END ATTACHED USER DOCUMENTS ---")
        document_context = "\n".join(doc_lines)

    if math_context:
        base_system += f"\n\n{math_context}"
    if document_context:
        base_system += f"\n\n{document_context}"
    elif rag_context and not attached_images:
        base_system += f"\n\n{rag_context}"
    if search_context:
        base_system += f"\n\n{search_context}"

    llm_messages.append({"role": "system", "content": base_system})

    # Filter out any legacy OCR-refusal assistant messages from history so old turns don't poison the model
    refusal_markers = (
        "doesn’t contain any recognizable text",
        "doesn't contain any recognizable text",
        "কোনো স্পষ্ট টেক্সট সনাক্ত করা যায়নি",
        "পাঠযোগ্য টেক্সট সনাক্ত করা যায়নি",
        "স্ক্রিনশট থেকে কোনো পাঠ্য বের করা যায়নি",
        "লেগিবল টেক্সট রিকগনাইজড নয়",
    )
    for hist_msg in history[-10:]:
        if hist_msg.role == "assistant" and any(m in (hist_msg.content or "") for m in refusal_markers):
            continue
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
        has_vision = False
        if provider and hasattr(provider, "list_supported_models"):
            for m in provider.list_supported_models():
                if m["id"] == resolved_model and m.get("supports_vision"):
                    has_vision = True
                    break
        if not has_vision:
            err_msg = (
                "⚠️ **Vision Model Required**: Processing uploaded images requires a multimodal vision model "
                "(such as Google Gemini 3.5 Flash or OpenAI GPT-4o). "
                "Please configure `GEMINI_API_KEY` in your server/Vercel environment settings to enable image understanding."
            )
            async def err_gen():
                yield f"data: {json.dumps({'token': err_msg})}\n\n"
                yield f"data: {json.dumps({'done': True, 'error': err_msg})}\n\n"
            return StreamingResponse(err_gen(), media_type="text/event-stream")
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
        client_cancelled = False
        stream_error = None
        try:
            async for token in provider.stream_chat(
                messages=llm_messages,
                model=resolved_model,
                temperature=temp
            ):
                full_assistant_reply.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

        except asyncio.CancelledError:
            client_cancelled = True
            # Generator is closing: do not yield any further tokens
        except Exception as stream_err:
            stream_error = str(stream_err)
            err_msg = f"⚠️ An error occurred while generating the response: {stream_error}"
            yield f"data: {json.dumps({'error': err_msg})}\n\n"
        finally:
            if not client_cancelled:
                final_content = "".join(full_assistant_reply).strip()
                is_error_reply = (
                    stream_error is not None
                    or "**Error**:" in final_content
                    or final_content.startswith("⚠️")
                    or not final_content
                )
                if is_error_reply:
                    # Do NOT persist error to database as an assistant reply; refund quota
                    db_ref = SessionLocal()
                    try:
                        refund_message_quota(db_ref, current_user.id)
                    finally:
                        db_ref.close()
                else:
                    db_save = SessionLocal()
                    try:
                        assistant_msg = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=final_content,
                            model=resolved_model,
                            citations=json.dumps(citations_data) if citations_data else None,
                            created_at=datetime.now(timezone.utc)
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
                    except Exception:
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
    return {"message": "Feedback recorded", "feedback": feedback_in.feedback}

