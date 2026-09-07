import asyncio
import contextlib
import datetime
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Any, Optional
import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form, Query, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse,JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import requests
from fastapi.responses import HTMLResponse, StreamingResponse
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from init_local_storage import add_user_folder
from document_processing import document_to_txt
from dotenv import load_dotenv
from data_models import *
from tools import  *
from cipher import cipher
from fastapi.responses import RedirectResponse
from db import get_db, async_session
import models
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _run_migrations() -> None:
    """Applies pending Alembic migrations (sync call — alembic's own async engine handling
    needs to run outside the already-running FastAPI event loop, see asyncio.to_thread below)."""
    config = AlembicConfig(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    alembic_command.upgrade(config, "head")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # datefmt="%Y-%m-%d %H:%M:%S"
    datefmt="%H:%M:%S",
    filename=str(BASE_DIR / "fastapi_backend.log"),
    filemode="a")
logger = logging.getLogger(__name__)

#LOCAL_LLM_URL = "http://localhost:8000"
local_storage_path = Path(os.environ['LOCAL_STORAGE'])
LOCAL_LLM_URL = os.environ["LOCAL_LLM_URL"]
MODEL_NAME = os.environ["MODEL_NAME"]
REDIRECT_URL = os.environ["REDIRECT_URL"]
# Optional: age (in days) after which an inactive conversation is auto-deleted. Unset disables
# the cleanup task entirely (opt-in, so it never silently deletes data unless configured).
CHAT_RETENTION_DAYS = os.environ.get("CHAT_RETENTION_DAYS")
CHAT_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

# Bounds how long a chat request can hang when the LLM server is unreachable or stalls:
# fail fast on connect, but stay tolerant of legitimate gaps between streamed tokens.
LLM_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)

# One shared client for the process, reused across requests, so concurrent chats reuse a
# pooled set of keep-alive connections to the LLM server instead of each opening its own.
llm_client = AsyncOpenAI(
    base_url=LOCAL_LLM_URL + "/v1",
    api_key="",
    timeout=LLM_TIMEOUT,
    max_retries=1,
    http_client=httpx.AsyncClient(
        timeout=LLM_TIMEOUT,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ),
)

async def _cleanup_old_conversations_loop() -> None:
    """Deletes conversations whose last activity is older than CHAT_RETENTION_DAYS days.
    Runs immediately on startup, then every CHAT_CLEANUP_INTERVAL_SECONDS. DB-level ON DELETE
    CASCADE (Postgres) / ORM-level cascade="all, delete-orphan" (models.py) takes care of the
    conversation's messages and their uploaded files."""
    retention_days = int(CHAT_RETENTION_DAYS)
    while True:
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
        async with async_session() as session:
            result = await session.execute(
                select(models.Conversation).where(models.Conversation.updated_at < cutoff)
            )
            stale_conversations = result.scalars().all()
            # Deleted one-by-one through the ORM (not a bulk `delete()` statement) so the
            # cascade="all, delete-orphan" relationships in models.py fire and remove each
            # conversation's messages/files even on sqlite, which has no DB-level ON DELETE
            # CASCADE (see migration 0002).
            for conversation in stale_conversations:
                await session.delete(conversation)
            await session.commit()
        if stale_conversations:
            logger.info(
                f"Chat auto-cleanup: deleted {len(stale_conversations)} conversation(s) older than {retention_days} day(s)."
            )
        await asyncio.sleep(CHAT_CLEANUP_INTERVAL_SECONDS)


REQUIRED_DIRS = [
    local_storage_path,
    local_storage_path / "user_files",
    local_storage_path / "files_chat_cache",
    local_storage_path / "chats",
]


@asynccontextmanager
async def lifespan(app: FastAPI):

    """Creates required directories on application startup."""
    logger.info("Checking and creating required directories...")

    created_dirs = []
    existing_dirs = []

    for dir_path in REQUIRED_DIRS:
        path = dir_path

        # Check whether the directory exists
        if not dir_path.exists():
            # Create the directory and any missing parents
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(dir_path))
            logger.info(f"✓ Created directory: {dir_path}")
        else:
            existing_dirs.append(str(path))
            logger.info(f"✓ Directory already exists: {path}")

    await asyncio.to_thread(_run_migrations)
    logger.info("✓ Database migrations applied")

    cleanup_task = None
    if CHAT_RETENTION_DAYS:
        cleanup_task = asyncio.create_task(_cleanup_old_conversations_loop())
        logger.info(f"✓ Chat auto-cleanup enabled: retention {CHAT_RETENTION_DAYS} day(s).")

    yield
    # Runs on application shutdown
    if cleanup_task:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
    await llm_client.close()

app = FastAPI(lifespan=lifespan)

# transcribe router (backend/routers/transcribe.py) is not present in this checkout — audio
# upload/transcription is out of scope for now.

app.add_middleware(
    CORSMiddleware,
    #allow_origins=["http://localhost:*", "http://192.168.*","http://localhost:5173","http://192.*"],
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# with open('index.html', 'r', encoding='utf-8') as f:
#     HTML = f.read()
#

# @app.get("/", response_class=HTMLResponse)
# async def root(email: str = ""):
#     return HTML

async def tool_handler(tool_name,tool_query):
    logger.info(f"Calling function {tool_name} {tool_query}")
    if tool_name == "web_search":
        # arguments = json.loads(tool_query)
        # query = arguments["query"]
        return await web_search(tool_query)
    else:
        logger.info(f"Problem calling function ({tool_name}  {tool_query})")
        return "The called function was not found or is unavailable"




async def generate(client, messages, depth=0, max_depth=5, force_web_search=False, web_search_query=None):
    """Recursive core generator: yields structured events (dicts), not raw text."""
    if depth >= max_depth:
        logger.warning(f"Reached maximum recursion depth {max_depth}")
        logger.info("Exceeded the maximum number of function calls.")
        yield {"type": "error", "message": "Exceeded the maximum number of function calls."}
        return

    if force_web_search:
        query = (web_search_query or "").strip()
        if query:
            tool_call_id = str(uuid.uuid4())[:4]
            logger.info("Forced web search (requested by user)")
            yield {"type": "tool_call_start", "tool": "web_search", "query": query}
            content = await tool_handler("web_search", query)
            yield {"type": "tool_result", "tool": "web_search", "content": content}
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": query})
                        }
                    }
                ]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "type": "function",
                "name": "web_search",
                "content": content
            })
        async for event in generate(client, messages, depth + 1, max_depth):
            yield event
        return

    stream = await client.chat.completions.create(
        messages=messages,
        model=MODEL_NAME,
        stream = True,
        tool_choice="auto",
        tools=tools,
        temperature=0.2
    )

    tool_query = ""
    tool_name = None
    content_started = False

    async for chunk in stream:

        token = chunk.choices[0].delta.content

        if chunk.choices[0].finish_reason == 'tool_calls':
            logger.info(f"Attempting to call function {tool_name}") #finish_reason=None
            try:
                arguments = json.loads(tool_query)
                query = arguments["query"]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Invalid arguments for function call {tool_name} ({tool_query!r}): {e}")
                yield {"type": "error", "message": "Failed to execute the function call: the model passed invalid arguments."}
                return
            id = str(uuid.uuid4())[:4]
            yield {"type": "tool_call_start", "tool": tool_name, "query": query}
            content = await tool_handler(tool_name,query)
            logger.info(f"Received data from function {tool_name}")
            yield {"type": "tool_result", "tool": tool_name, "content": content}
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": id ,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps({"query": query})
                        }
                    }
                ]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": id,
                "type": "function",
                "name": tool_name,
                "content": content
            })

            async for event in generate(client, messages, depth + 1, max_depth):
                yield event

            tool_query = ""
            tool_name = None
            continue

        if chunk.choices[0].delta.tool_calls: # accumulate the function-call argument string
            #print(chunk)
            if not chunk.choices[0].delta.tool_calls[0].function.arguments: # if the argument is empty (the first tool-call chunk is always empty, it only carries the function name)
                tool_name= chunk.choices[0].delta.tool_calls[0].function.name
                #print(chunk.choices[0].delta.tool_calls[0].function.name)
                continue
            tool_query += chunk.choices[0].delta.tool_calls[0].function.arguments

            print(tool_query)
            continue

        if token:
            if not content_started:
                if not token.strip():
                    continue
                content_started = True
            await asyncio.sleep(0.01)
            yield {"type": "token", "content": token}



TITLE_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)


async def generate_title(client, user_text: str) -> str | None:
    """Asks the LLM for a short conversation title based on the first user message."""
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Come up with a short topical title for the conversation (no more than 5 words) "
                                "based on the user's first message. Reply with only the title, no quotes, "
                                "no trailing period, and no explanations.",
                },
                {"role": "user", "content": user_text[:2000]},
            ],
            temperature=0.3,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=TITLE_TIMEOUT,
            max_tokens=50
        )
        #logger.info(f"Title generation ({response.json()}s)")
        title = (response.choices[0].message.content or "").strip().strip('"').strip("'").strip()
        return title[:80] or None
    except (APIConnectionError, APITimeoutError) as e:
        logger.warning(f"Title generation timed out ({TITLE_TIMEOUT.read}s): {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate conversation title: {e}")
        return None


async def stream_and_persist(client, messages, conversation, db: AsyncSession, title_source_text: str | None = None,
                              force_web_search: bool = False, web_search_query: str | None = None):
    """Wraps generate(), turns events into NDJSON lines, and persists the assembled
    assistant message (plus any tool-call events) once the stream finishes."""
    full_text = ""
    tool_events = []

    try:
        async for event in generate(client, messages, force_web_search=force_web_search, web_search_query=web_search_query):
            if event["type"] == "token":
                full_text += event["content"]
            elif event["type"] in ("tool_call_start", "tool_result"):
                tool_events.append(event)
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except (APIConnectionError, APITimeoutError) as e:
        logger.error(f"LLM unavailable: {e}")
        yield json.dumps(
            {"type": "error", "message": "No connection to the LLM server. Check your connection and try again."},
            ensure_ascii=False,
        ) + "\n"
    except Exception as e:
        logger.error(e)
        yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + "\n"

    assistant_message = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=full_text,
        tool_calls=tool_events or None,
    )
    db.add(assistant_message)
    await db.commit()

    if title_source_text:

        title = await generate_title(client, title_source_text)
        if title:
            conversation.title = title
            await db.commit()
            yield json.dumps({"type": "title", "title": title}, ensure_ascii=False) + "\n"

    yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"



async def check_tokens_chat_history(messages=None):
    """Trims history if it's close to the model's context limit. Never raises: if the LLM
    server can't be reached to tokenize, the untrimmed history is returned as-is and the
    failure surfaces later, from the actual chat completion call."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(
                LOCAL_LLM_URL + "/tokenize",
                json={'model': MODEL_NAME, 'messages': messages}
            )
            response.raise_for_status()
            data = response.json()

        logger.info(f"Chat token count {data['count']} max_model_len {data['max_model_len']}")
        if data["max_model_len"] / data["count"] > 0.85:  # if the message history exceeds 85% of the available context
            if messages and messages[0]["role"] == "system":  # never trim the system prompt
                system_message, rest = messages[0], messages[1:]
                return [system_message] + rest[len(rest) // 2:]
            return messages[len(messages) // 2:]  # drop the first half of the history
        return messages
    except Exception as e:
        logger.warning(f"Failed to check history token count (LLM unavailable?): {e}")
        return messages

async def check_tokens_document(document_text = None):
    """Returns False only when the document is confirmed too large. If the LLM server can't
    be reached to tokenize, returns True so the failure surfaces later, from the actual chat
    completion call, instead of this best-effort check blocking a legitimate message."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(
                LOCAL_LLM_URL + "/tokenize",
                json={"model": MODEL_NAME, "prompt": document_text}
            )
            response.raise_for_status()
            data = response.json()
        logger.info(f"Document token count {data['count']} max_model_len {data['max_model_len']}")
        return data["count"] < 0.85 * data["max_model_len"]
    except Exception as e:
        logger.warning(f"Failed to check document token count (LLM unavailable?): {e}")
        return True

def build_system_prompt() -> dict:
    """Built fresh per request so the embedded date stays correct across long-running processes."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return {'role': 'system', 'content': f'You are an assistant at a company who answers user questions. Today is {today}. '
                                          f'Reply in English unless asked to use another language. '
                                          f'If you use information from web_search results, always cite the source as a markdown link '
                                          f'in the format [source name](URL), rather than just the site or article name without a link.'
                                          }


def build_messages(history: list[dict]) -> list[dict]:
    return [build_system_prompt()] + history


async def get_current_user(
        x_user_email: str = Header(...),
        db: AsyncSession = Depends(get_db)) -> models.User:
    email = x_user_email.strip().lower()
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = models.User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def _get_owned_conversation(conversation_id: str, user: models.User, db: AsyncSession) -> models.Conversation:
    result = await db.execute(
        select(models.Conversation).where(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _load_history(conversation_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(models.Message)
        .where(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at)
        .options(selectinload(models.Message.files))
    )
    history = []
    for m in result.scalars().all():
        content = m.content
        for uploaded_file in m.files:  # reconstruct document text only for the LLM context
            content = (
                f"{content}\n### DOCUMENT START ### {uploaded_file.filename}: \n"
                f"{uploaded_file.extracted_text}\n ### DOCUMENT END ###\n"
            )
        history.append({"role": m.role, "content": content})
    return history


@app.get("/api/v1/conversations")
async def list_conversations(
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Conversation)
        .where(models.Conversation.user_id == user.id)
        .order_by(models.Conversation.updated_at.desc())
    )
    return [
        {"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()}
        for c in result.scalars().all()
    ]


@app.post("/api/v1/conversations")
async def create_conversation(
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    conversation = models.Conversation(user_id=user.id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return {"id": conversation.id, "title": conversation.title, "updated_at": conversation.updated_at.isoformat()}


@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages(
        conversation_id: str,
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    await _get_owned_conversation(conversation_id, user, db)
    result = await db.execute(
        select(models.Message)
        .where(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at)
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "created_at": m.created_at.isoformat(),
        }
        for m in result.scalars().all()
    ]


@app.post("/api/v1/chat/completions")
async def chat_stream(
        request: ChatMessageRequest,
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    logger.info("request received to /api/v1/chat/completions")

    conversation = await _get_owned_conversation(request.conversation_id, user, db)

    user_message = models.Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_message)
    await db.commit()

    history = await _load_history(conversation.id, db)
    is_first_message = len(history) == 1
    messages = await check_tokens_chat_history(build_messages(history))

    return StreamingResponse(
        stream_and_persist(
            llm_client, messages, conversation, db,
            title_source_text=request.message if is_first_message else None,
            force_web_search=request.force_web_search, web_search_query=request.message,
        ),
        media_type="application/x-ndjson",
    )

@app.put("/api/v1/conversations/{conversation_id}/messages/{message_id}")
async def edit_message(
        conversation_id: str,
        message_id: str,
        request: EditMessageRequest,
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    logger.info("request received to /api/v1/conversations/{conversation_id}/messages/{message_id} (edit)")

    conversation = await _get_owned_conversation(conversation_id, user, db)

    result = await db.execute(
        select(models.Message).where(
            models.Message.id == message_id,
            models.Message.conversation_id == conversation.id,
        )
    )
    message = result.scalar_one_or_none()
    if message is None or message.role != "user":
        raise HTTPException(status_code=404, detail="Message not found")

    message.content = request.message
    await db.execute(
        delete(models.Message).where(
            models.Message.conversation_id == conversation.id,
            and_(
                models.Message.created_at >= message.created_at,
                models.Message.id != message.id,
            ),
        )
    )
    await db.commit()

    history = await _load_history(conversation.id, db)
    is_first_message = len(history) == 1
    messages = await check_tokens_chat_history(build_messages(history))

    return StreamingResponse(
        stream_and_persist(
            llm_client, messages, conversation, db,
            title_source_text=request.message if is_first_message else None,
        ),
        media_type="application/x-ndjson",
    )


@app.post("/api/v1/chat/completions_files")
async def upload_file_with_metadata(
        conversation_id: str = Form(...),
        message: str = Form(...),
        force_web_search: bool = Form(False),
        files: list[UploadFile] = File(...),
        user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)):
    logger.info("request received to /api/v1/chat/completions_files")

    conversation = await _get_owned_conversation(conversation_id, user, db)

    files_names = []

    for uploaded_file in files:  # save the user's files to the local folder
        file_id = str(uuid.uuid4())[:8]
        save_path = local_storage_path / "files_chat_cache" / f"{file_id}_{uploaded_file.filename}"
        files_names.append(f"{file_id}_{uploaded_file.filename}")
        with open(save_path, "wb") as buffer:
            content = await uploaded_file.read()
            buffer.write(content)
    extracted_texts: dict[str, str] = {}
    for file_name in files_names:
        try:
            extracted_texts[file_name] = document_to_txt(local_storage_path / "files_chat_cache" / file_name)
        except Exception as e:
            logger.error(f"Failed to process document {file_name}: {e}")
            extracted_texts[file_name] = f"An error occurred while processing the document: {e}"

    full_message = message
    for file_name, text in extracted_texts.items():
        full_message = f"{full_message}\n### DOCUMENT START ### {file_name}: \n{text}\n ### DOCUMENT END ###\n"

    check_document_size = await check_tokens_document(full_message)

    if not check_document_size:
        raise HTTPException(
            status_code=422,
            detail="Document too large. Use the option from the toolbar.",
        )

    display_content = message or f"[Sent {len(files_names)} file(s)]"
    user_message = models.Message(conversation_id=conversation.id, role="user", content=display_content)
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    for file_name in files_names:
        db.add(models.UploadedFile(
            message_id=user_message.id,
            filename=file_name,
            extracted_text=extracted_texts.get(file_name, ""),
        ))
    await db.commit()

    history = await _load_history(conversation.id, db)
    is_first_message = len(history) == 1
    messages = await check_tokens_chat_history(build_messages(history))

    return StreamingResponse(
        stream_and_persist(
            llm_client, messages, conversation, db,
            title_source_text=message if is_first_message else None,
            force_web_search=force_web_search, web_search_query=message,
        ),
        media_type="application/x-ndjson",
    )


@app.get("/api/sso")
async def sso_login(email: str = Query()):
    if not email:
        raise HTTPException(status_code=400, detail="Invalid email")

    encrypted = cipher.encrypt(email.lower())
    return RedirectResponse(
        f"{REDIRECT_URL}?user_info={encrypted}",
        status_code=303
    )
@app.post("/api/login")
async def login(user_info: str = Form(...), db: AsyncSession = Depends(get_db)):
    logger.info("Login endpoint accessed")
    try:
        email = cipher.decrypt(user_info).strip().lower()
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Invalid user_info")

    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = models.User(email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    add_user_folder(email)

    return {"user_id": user.id, "email": user.email}

@app.get("/api/health")
async def check_health():
    """Proxies a health check to the local LLM."""
    logger.info("Health endpoint accessed")
    try:
        async with httpx.AsyncClient() as http:
            response = await http.get(LOCAL_LLM_URL + "/health")
            return response.status_code
    except Exception as error:
        logger.info(error)
        return JSONResponse(
            status_code=205,
            content="no connection to the LLM API")


