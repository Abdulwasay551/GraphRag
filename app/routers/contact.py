"""Contact form router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact", tags=["Contact"])


class ContactMessage(BaseModel):
    """Contact form message schema"""
    name: str
    email: EmailStr
    subject: str
    message: str


@router.post("")
async def submit_contact(message: ContactMessage):
    """Handle contact form submission"""
    try:
        # TODO: Implement email sending logic (SMTP, SendGrid, etc.)
        # For now, just log the message
        logger.info(f"Contact form submission from {message.name} ({message.email})")
        logger.info(f"Subject: {message.subject}")
        logger.info(f"Message: {message.message}")
        
        # In production, you would:
        # 1. Send email to support team
        # 2. Store message in database
        # 3. Send auto-reply to user
        
        return {
            "status": "success",
            "message": "Thank you for contacting us! We'll get back to you soon."
        }
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")
