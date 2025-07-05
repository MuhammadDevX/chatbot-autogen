# Chatbot AutoGen with Authentication

A real-time chat application with streaming responses using Microsoft AutoGen, user authentication, and markdown support built with FastAPI backend and Next.js frontend.

## Features

- ✅ **Microsoft AutoGen Integration**: Powered by the latest AutoGen framework for AI agents
- ✅ **Real-time streaming chat responses** with markdown support
- ✅ **User Authentication**: Sign up, sign in, and secure user sessions
- ✅ **User-specific conversations**: Each user sees only their own chats
- ✅ **JWT-based authentication** with secure token management
- ✅ **Password hashing** using bcrypt for security
- ✅ **Protected routes** - unauthenticated users are redirected to signin
- ✅ **Auto-scroll to latest messages**
- ✅ **Loading states during responses**
- ✅ **CORS support for local development**
- ✅ **Conversation history persistence** with AutoGen's built-in context management

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Microsoft AutoGen**: AI agent framework for conversational AI
- **SQLAlchemy**: Async database ORM
- **PostgreSQL**: Database
- **JWT**: Authentication tokens
- **bcrypt**: Password hashing

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **React Query**: Data fetching and caching
- **React Markdown**: Markdown rendering

## Authentication System

### Backend Authentication (FastAPI)

The backend uses JWT tokens for authentication with the following endpoints:

- `POST /auth/signup` - Create a new user account
- `POST /auth/signin` - Sign in with email and password
- `GET /auth/me` - Get current user information (protected)
- `POST /chat/stream` - Chat streaming with AutoGen (protected)
- `GET /chat` - Get user conversations (protected)
- `POST /chat/{conversation_id}/title` - Generate conversation titles (protected)

### Frontend Authentication (Next.js)

- **AuthContext**: Manages authentication state across the app
- **Protected Routes**: Automatically redirect unauthenticated users
- **Token Storage**: JWT tokens stored in localStorage
- **Auto-login**: Tokens are validated on app startup

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL database
- OpenAI API key

### Backend Setup

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up environment variables** in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/chatbot
OPENAI_API_KEY=your_openai_api_key
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
```

3. **Run the backend**:
```bash
python main.py
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. **Navigate to the frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Create `.env.local` file**:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

4. **Run the frontend**:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## AutoGen Implementation

### Agent Configuration

The application uses Microsoft AutoGen's `AssistantAgent` with the following configuration:

```python
openai_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
openai_agent = AssistantAgent(
    name="openai_agent",
    model_client=openai_client,
    model_client_stream=True,
    system_message="You are a helpful AI assistant. Respond to the user's message while considering the conversation history. Be conversational and helpful."
)
```

### Streaming Implementation

The chat uses AutoGen's native streaming capabilities:

- **`on_messages_stream()`**: Real-time streaming of AI responses
- **Conversation Context**: AutoGen automatically manages conversation history
- **Chunk Processing**: Each response chunk is streamed to the frontend
- **Message Persistence**: Complete responses are saved to the database

### Key AutoGen Features Used

- **TextMessage**: Structured message format for user inputs
- **AssistantAgent**: Main AI agent with streaming support
- **CancellationToken**: Proper cancellation handling for streaming
- **ModelClientStreamingChunkEvent**: Real-time response chunks

## Database Schema

The application uses the following database models:

```sql
-- Users table
CREATE TABLE "User" (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    password VARCHAR NOT NULL,
    "createdAt" TIMESTAMP DEFAULT NOW()
);

-- Conversations table
CREATE TABLE "Conversation" (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    "userId" VARCHAR NOT NULL REFERENCES "User"(id),
    "createdAt" TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE "Message" (
    id VARCHAR PRIMARY KEY,
    role VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    "conversationId" VARCHAR NOT NULL REFERENCES "Conversation"(id),
    "createdAt" TIMESTAMP DEFAULT NOW()
);
```

## Usage

1. **Open** `http://localhost:3000` in your browser
2. **Sign up** for a new account or **sign in** with existing credentials
3. **Start chatting** - AutoGen will handle conversation context automatically
4. **View your chat history** in the sidebar
5. **Conversation titles** are automatically generated after 4 messages
6. **Sign out** when done

## Security Features

- **Password Hashing**: All passwords are hashed using bcrypt
- **JWT Tokens**: Secure token-based authentication
- **Protected Routes**: Backend endpoints require valid authentication
- **User Isolation**: Users can only access their own conversations
- **Token Expiration**: JWT tokens expire after 24 hours

## API Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/signin` - Login user
- `GET /auth/me` - Get current user info

### Chat
- `GET /chat?conversations=1` - Get user conversations
- `GET /chat/{conversation_id}/messages` - Get conversation messages
- `POST /chat/stream` - Stream chat responses with AutoGen
- `POST /chat/{conversation_id}/title` - Generate conversation title

## Streaming Protocol

The application uses Server-Sent Events (SSE) for real-time streaming:

```
data: Hello
data:  world
data: !
data: [DONE]
```

Each chunk is sent as a separate `data:` line, with `[DONE]` indicating the end of the stream.

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and DATABASE_URL is correct
2. **CORS Errors**: Check that frontend URL is in backend CORS settings
3. **Authentication Errors**: Verify JWT_SECRET is set and consistent
4. **AutoGen Import Errors**: Ensure all AutoGen packages are installed
5. **Streaming Issues**: Check that `model_client_stream=True` is set

### Development Tips

- Use browser dev tools to inspect network requests
- Check backend logs for detailed error messages
- Verify token is being sent in Authorization header
- Test authentication endpoints with tools like Postman
- Monitor AutoGen agent responses in backend logs

## Production Considerations

- Change JWT_SECRET to a strong, unique value
- Use HTTPS in production
- Set up proper database backups
- Configure CORS for production domains
- Add rate limiting for authentication endpoints
- Consider using Redis for session storage
- Implement password reset functionality
- Add email verification
- Monitor AutoGen agent performance and costs
- Consider implementing conversation context limits

## AutoGen vs OpenAI Agents SDK

This implementation migrated from OpenAI Agents SDK to Microsoft AutoGen for:

- **Better streaming support**: Native streaming with `on_messages_stream()`
- **Conversation management**: Built-in context handling
- **Extensibility**: Easy to add tools and multi-agent conversations
- **Active development**: Microsoft-backed framework with regular updates
- **Performance**: Optimized for conversational AI workloads
