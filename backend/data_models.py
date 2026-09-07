from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TranscriptionRequest(BaseModel):
    audio_files_ids: List[str] = Field(..., description="List of audio file IDs")
    audio_files_ext: List[str] = Field(..., description="List of file extensions")
    user_info: Optional[str] = Field(None, description="User information")

class TranscriptionResponse(BaseModel):
    data: dict = Field(..., description="dict {file_id : text, ...}")
    user_info: Optional[str] = Field(None, description="User information")

class ChatHistory(BaseModel):
    messages: List[dict]

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    force_web_search: bool = False

class EditMessageRequest(BaseModel):
    message: str