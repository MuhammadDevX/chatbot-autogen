# Chatbot AutoGen Frontend

A modern Next.js frontend for the Chatbot AutoGen application, featuring real-time streaming chat, user authentication, and markdown support.

## Features

- **Real-time Streaming Chat**: Server-Sent Events (SSE) for live AI responses
- **User Authentication**: JWT-based authentication with protected routes
- **Markdown Support**: Rich text rendering for AI responses
- **Conversation Management**: View and manage chat history
- **Auto-generated Titles**: Conversation titles generated automatically
- **Responsive Design**: Works on desktop and mobile devices
- **TypeScript**: Full type safety throughout the application

## Technology Stack

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript development
- **Tailwind CSS**: Utility-first CSS framework
- **React Query**: Data fetching and caching
- **React Markdown**: Markdown rendering with syntax highlighting
- **Lucide React**: Beautiful icons
- **UUID**: Unique ID generation

## Getting Started

### Prerequisites

- Node.js 18+
- Backend server running (see main README for setup)

### Installation

1. **Install dependencies**:
```bash
npm install
```

2. **Set up environment variables** in `.env.local`:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

3. **Run the development server**:
```bash
npm run dev
```

4. **Open** [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Authentication pages
│   ├── (chat)/            # Chat pages
│   ├── api/               # API routes (proxies to backend)
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ChatInput.tsx      # Message input component
│   ├── ChatList.tsx       # Conversation list
│   ├── MarkdownMessage.tsx # Message rendering
│   ├── ProtectedRoute.tsx # Auth protection
│   └── Sidebar.tsx        # Main sidebar
├── contexts/              # React contexts
│   └── AuthContext.tsx    # Authentication state
├── hooks/                 # Custom React hooks
│   ├── useChatStream.ts   # Streaming chat hook
│   └── useMessages.ts     # Messages management
└── lib/                   # Utility functions
```

## Key Components

### ChatInput
- Handles message input and sending
- Supports Enter key for sending
- Shows loading state during AI response

### MarkdownMessage
- Renders user and AI messages differently
- Supports markdown syntax highlighting
- Code blocks with language detection

### useChatStream
- Manages real-time streaming from backend
- Handles Server-Sent Events (SSE)
- Updates UI as chunks arrive

### AuthContext
- Manages authentication state
- Handles token storage and validation
- Provides login/logout functionality

## API Integration

The frontend communicates with the backend through Next.js API routes:

- `/api/chat/stream` - Streaming chat responses
- `/api/chat` - Get conversations list
- `/api/chat/[id]/messages` - Get conversation messages
- `/api/chat/[id]/title` - Generate conversation title
- `/api/auth/*` - Authentication endpoints

## Streaming Implementation

The chat uses Server-Sent Events (SSE) for real-time streaming:

```typescript
const reader = res.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // Process chunk and update UI
}
```

Each chunk is processed and added to the current message in real-time.

## Authentication Flow

1. **Sign Up/Sign In**: User authenticates via backend
2. **Token Storage**: JWT token stored in localStorage
3. **Protected Routes**: Unauthenticated users redirected to signin
4. **Auto-login**: Token validated on app startup
5. **Logout**: Token cleared and user redirected

## Styling

The application uses Tailwind CSS for styling with:
- Responsive design patterns
- Dark/light mode support (via CSS variables)
- Custom component styling
- Markdown content styling

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Environment Variables

- `NEXT_PUBLIC_BACKEND_URL` - Backend server URL

## Deployment

The frontend can be deployed to:
- **Vercel** (recommended for Next.js)
- **Netlify**
- **AWS Amplify**
- Any static hosting service

### Vercel Deployment

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy automatically on push to main branch

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure backend CORS settings include frontend URL
2. **Authentication Issues**: Check token storage and backend connectivity
3. **Streaming Problems**: Verify backend streaming endpoint is working
4. **Build Errors**: Check TypeScript types and dependencies

### Development Tips

- Use browser dev tools to inspect network requests
- Check console for error messages
- Verify environment variables are set correctly
- Test authentication flow in incognito mode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

