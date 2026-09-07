from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TranscriptionRequest(BaseModel):
    audio_files_ids: List[str] = Field(..., description="Список ID аудиофайлов")
    audio_files_ext: List[str] = Field(..., description="Список расширений файлов")
    user_info: Optional[str] = Field(None, description="Информация о пользователе")

class TranscriptionResponse(BaseModel):
    data: dict = Field(..., description="словарь {file_id : text, ...}")
    user_info: Optional[str] = Field(None, description="Информация о пользователе")

class ChatHistory(BaseModel):
    messages: List[dict]

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    force_web_search: bool = False

class EditMessageRequest(BaseModel):
    message: str