import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.future import select
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
import asyncio
from openai.types.responses import ResponseTextDeltaEvent
from dotenv import load_dotenv
import jwt
import bcrypt
import uuid

# Load env vars
load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql+asyncpg://user:pass@localhost:5432/chatbot
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

openai_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
system_message = "You are a helpful AI assistant. Respond to the user's message while considering the conversation history. Be conversational and helpful."
openai_agent = AssistantAgent(
                name="openai_agent",
                model_client=openai_client,
                model_client_stream=True,
                system_message=system_message
            )


# SQLAlchemy async setup
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

# Security
security = HTTPBearer()

# Models - matching Prisma schema exactly
class User(Base):
    __tablename__ = "User"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "Conversation"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    userId = Column(String, ForeignKey("User.id"), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "Message"
    id = Column(String, primary_key=True, index=True)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    conversationId = Column(String, ForeignKey("Conversation.id"), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")

# Pydantic schemas
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserSignin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ChatRequest(BaseModel):
    user_id: str
    conv_id: str
    prompt: str

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

class ConversationOut(BaseModel):
    id: str
    title: str

    class Config:
        orm_mode = True

class TitleRequest(BaseModel):
    conversation_id: str

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.PyJWTError:
        return None

# Authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    print(f"Verifying token: {credentials.credentials[:20]}...")
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        print("Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Token verified, user_id: {user_id}")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        print(f"User not found in database: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"User found: {user.email}")
    return user

# Initialize app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication endpoints
@app.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        password=hashed_password.decode('utf-8'),
        createdAt=datetime.utcnow()
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.createdAt
        )
    )

@app.post("/auth/signin", response_model=TokenResponse)
async def signin(user_data: UserSignin, db: AsyncSession = Depends(get_db)):
    print(f"Signin attempt for email: {user_data.email}")
    
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        print(f"User not found for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"User found: {user.id}")
    
    # Verify password
    if not bcrypt.checkpw(user_data.password.encode('utf-8'), user.password.encode('utf-8')):
        print(f"Invalid password for user: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"Password verified for user: {user.id}")
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    print(f"Token created for user: {user.id}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.createdAt
        )
    )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    print(f"Getting user info for: {current_user.id}")
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.createdAt
    )

# Helper to save messages
async def save_message(db: AsyncSession, conv_id: str, role: str, content: str):
    # Generate a simple unique ID - in production, you might want to use a proper cuid generator
    msg_id = str(uuid.uuid4())
    
    msg = Message(
        id=msg_id, 
        role=role, 
        content=content, 
        conversationId=conv_id,
        createdAt=datetime.utcnow()
    )
    db.add(msg)
    await db.commit()


async def get_or_create_conversation(db: AsyncSession, user_id: str, conv_id: str):
    # Use async select to get conversation
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    
    if not conv:
        conv = Conversation(
            id=conv_id, 
            title="New Conversation", 
            userId=user_id, 
            createdAt=datetime.utcnow()
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv    


@app.get("/chat", response_model=List[ConversationOut])
async def get_conversations(
    conversations: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if conversations != 1:
        return []

    # Fetch conversations belonging to the current user
    result = await db.execute(
        select(Conversation).where(Conversation.userId == current_user.id)
    )
    convs = result.scalars().all()
    return convs


@app.get("/chat/{conversation_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # First verify that the conversation belongs to the current user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.userId == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        # Return empty list if conversation doesn't exist or doesn't belong to user
        return []
    
    # Get all messages for this conversation, ordered by creation time
    result = await db.execute(
        select(Message).where(Message.conversationId == conversation_id)
        .order_by(Message.createdAt)
    )
    messages = result.scalars().all()
    
    return [
        MessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.createdAt
        )
        for msg in messages
    ]


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Ensure conversation exists and belongs to current user
    await get_or_create_conversation(db, current_user.id, req.conv_id)
    
    # Get conversation history
    result = await db.execute(
        select(Message).where(Message.conversationId == req.conv_id)
        .order_by(Message.createdAt)
    )
    history_messages = result.scalars().all()
    
    # Build conversation context from history
    conversation_context = ""
    if history_messages:
        conversation_context = "Previous conversation:\n"
        for msg in history_messages:
            role = "User" if msg.role == "user" else "Assistant"
            conversation_context += f"{role}: {msg.content}\n"
        conversation_context += "\nCurrent user message: "
    
    # Save user message
    await save_message(db, req.conv_id, "user", req.prompt)
    
    async def event_generator():
        assistant_response = ""
        try:
            

            # Only pass the latest user message
            message = TextMessage(content=req.prompt, source="user")

            # Use the streaming method
            cancellation_token = CancellationToken()
            async for event in openai_agent.on_messages_stream([message], cancellation_token=cancellation_token):
                # Each event is a ModelClientStreamingChunkEvent
                if hasattr(event, "content") and event.content:
                    assistant_response += event.content
                    yield f"data: {event.content}\n\n"

            # Save the full assistant response after streaming
            if assistant_response:
                async with AsyncSessionLocal() as save_db:
                    await save_message(save_db, req.conv_id, "assistant", assistant_response)

            yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"Error in streaming: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/chat/{conversation_id}/title")
async def generate_conversation_title(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify conversation belongs to current user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.userId == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get conversation messages
    result = await db.execute(
        select(Message).where(Message.conversationId == conversation_id)
        .order_by(Message.createdAt)
        .limit(10)  # Limit to first 10 messages for context
    )
    messages = result.scalars().all()
    
    if not messages:
        return {"title": "New Conversation"}
    
    # Build context for title generation
    conversation_text = ""
    for msg in messages:
        role = "User" if msg.role == "user" else "Assistant"
        conversation_text += f"{role}: {msg.content}\n"
    
    try:
        # Create title generation agent
        openai_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
        title_agent = AssistantAgent(
            name="TitleGenerator",
            model_client=openai_client,
            system_message="You are a title generation specialist. Based on the conversation content, generate a concise, descriptive title (maximum 50 characters) that captures the main topic or theme of the conversation. Return only the title, nothing else."
        )
        
        # Generate title
        message = TextMessage(content=f"Generate a title for this conversation:\n\n{conversation_text}", source="user")
        cancellation_token = CancellationToken()
        response = await title_agent.on_messages([message], cancellation_token=cancellation_token)
        
        if hasattr(response, 'chat_message') and response.chat_message:
            title = response.chat_message.content.strip()
        else:
            title = "Conversation"
        
        # Clean up the title (remove quotes, extra spaces, etc.)
        title = title.replace('"', '').replace("'", "").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        
        # Update conversation title in database
        conversation.title = title
        await db.commit()
        
        return {"title": title}
        
    except Exception as e:
        print(f"Error generating title: {e}")
        return {"title": "Conversation"}

if __name__ == "__main__":
    import uvicorn
    
    # Create tables if they don't exist
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created/verified")
    
    # Run database initialization
    import asyncio
    asyncio.run(init_db())
    
    uvicorn.run(app, host="0.0.0.0", port=8000)