from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.api.deps import get_current_user
from app.core.quota import check_and_consume_image_quota
from app.ai.image_service import image_service

router = APIRouter()

class ImageGenerateRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    model: Optional[str] = "turbo"

@router.post("/generate")
async def generate_ai_image(
    req: ImageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not req.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image generation prompt cannot be empty"
        )

    # Enforce and consume daily image generation quota
    check_and_consume_image_quota(db, current_user.id)

    try:
        result = await image_service.generate_image(
            prompt=req.prompt,
            width=req.width or 1024,
            height=req.height or 1024,
            model=req.model or "turbo"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}"
        )

    # If conversation_id is provided, save user request and assistant image reply to history
    if req.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == req.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if conv:
            user_msg = Message(
                conversation_id=conv.id,
                role="user",
                content=f"🎨 Generated image: {req.prompt}"
            )
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=f"Here is your generated image for **\"{req.prompt}\"**:\n\n![{req.prompt}]({result['url']})"
            )
            db.add_all([user_msg, assistant_msg])
            db.commit()

    return result
