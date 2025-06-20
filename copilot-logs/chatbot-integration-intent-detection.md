# Chatbot Integration with Intent Detection and Function Calling

**Date:** 20 juin 2025  
**Subject:** Integration of Django backend chatbot with React frontend, including intent detection and dynamic function calling

## Overview

This conversation documents the complete implementation of an enhanced chatbot system that integrates a Django backend with a React frontend, featuring intelligent intent detection and dynamic function calling capabilities.

## Initial Request

The user requested integration of a chatbot from `src/backend/chatbot` into the React frontend component `src/frontend/src/features/layouts/components/thread-bot/components/chat-window/index.tsx`, with the simplest possible integration using the Django backend.

## Implementation Steps

### 1. Basic Integration Setup

**Backend Configuration:**
- Added `chatbot` to `INSTALLED_APPS` in `/src/backend/messages/settings.py`
- Added chatbot URLs to main URL configuration: `path("mails/chatbot/", include("chatbot.urls"))`
- Created simple chat endpoint at `/mails/chatbot/` in `chatbot/views.py`

**Frontend Updates:**
- Updated fetch URL to correct Docker port: `http://localhost:8071/mails/chatbot/`
- Improved response handling and error management
- Added French error messages

**Initial Testing:**
- Backend running on Docker port 8071
- Frontend running on npm port 3000
- Basic integration working with summarization function

### 2. Enhanced Requirements - Intent Detection

The user then requested a major enhancement to support:
- Dynamic behavior based on user intent
- Detection of: summarize email, generate reply, classify email
- Function calling mechanism
- Conversational responses as default
- Context-aware behavior

### 3. Advanced Implementation

#### Intent Detection System (`src/backend/chatbot/chatbot.py`)

Added three new methods:

1. **`detect_intent(user_message)`**
   - Multi-layer detection: keyword-based + AI analysis
   - Four intent types: conversation, summarize_email, generate_reply, classify_email
   - Confidence scoring (>70% threshold for function calling)

2. **`chat_conversation(user_message, conversation_history)`**
   - Conversational AI responses
   - Context-aware with history support
   - Email management advice and guidance

3. **`process_user_message(user_message, conversation_history)`**
   - Main orchestrator method
   - Routes to appropriate handler based on intent
   - Function calling with full prompt processing
   - Rich response formatting with metadata

#### Enhanced API Endpoint (`src/backend/chatbot/views.py`)

Updated `simple_chat_api`:
- Accepts conversation history for context
- Uses new `process_user_message()` method
- Returns rich response format with metadata:
  - `response`: The actual response text
  - `type`: Response type (conversation, email_summary, etc.)
  - `function_used`: Which function was called
  - `original_intent`: Detected intent

#### Frontend Enhancements (`src/frontend/.../chat-window/index.tsx`)

Major improvements:
- **Conversation Memory**: Maintains last 10 messages for context
- **Enhanced Message Types**: Support for different response types
- **Visual Differentiation**: Color-coded messages based on type
- **Loading States**: Shows thinking indicator
- **Metadata Display**: Shows which function was used
- **Better UX**: Timestamps, disabled states, placeholders

#### Styling (`ChatWindow.module.css`)

Created modern CSS module with:
- Responsive chat interface design
- Color-coded message types (email summary, reply, classification)
- Loading animations
- Professional styling with proper accessibility

## Technical Details

### Intent Detection Logic

```python
# Keyword-based detection (high confidence)
if any(keyword in message_lower for keyword in ['résume', 'résumé', 'synthèse']):
    return {'intent': 'summarize_email', 'confidence': 0.9}

# AI-assisted fallback detection
system_prompt = "Analyse ce message et détermine l'intention..."
```

### Function Calling Flow

1. User message → Intent detection
2. If confidence > 70% → Call specific function
3. Else → Default to conversation mode
4. Format response with metadata
5. Return to frontend with rich information

### Response Format

```json
{
    "success": true,
    "response": "📧 **Résumé de l'email:**...",
    "type": "email_summary",
    "function_used": "summarize_mail",
    "original_intent": "summarize_email"
}
```

## Testing Results

### ✅ Conversation Mode
```
Input: "Comment allez-vous?"
Output: Conversational response with email management advice
Type: conversation
```

### ✅ Email Summarization
```
Input: "Résume cet email: Bonjour, la réunion est annulée..."
Output: 📧 **Résumé de l'email:** [structured summary]
Type: email_summary, Function: summarize_mail
```

### ✅ Reply Generation
```
Input: "Réponds à cet email: Pouvez-vous confirmer..."
Output: ✉️ **Réponse proposée:** [professional reply]
Type: email_reply, Function: generate_mail_answer
```

### ✅ Email Classification
```
Input: "Classe cet email: URGENT - Le serveur est en panne..."
Output: 🏷️ **Classification:** [category with confidence]
Type: email_classification, Function: classify_mail
```

## Architecture

### Backend (Django + Albert API)
- **chatbot/chatbot.py**: Core logic with intent detection
- **chatbot/views.py**: API endpoints
- **chatbot/urls.py**: URL routing
- **messages/settings.py**: App configuration
- **messages/urls.py**: Main URL inclusion

### Frontend (React + TypeScript)
- **chat-window/index.tsx**: Main chat component
- **ChatWindow.module.css**: Styling
- **thread-bot/index.tsx**: Parent component

### Infrastructure
- Backend: Docker container on port 8071
- Frontend: npm dev server on port 3000
- API Communication: JSON over HTTP
- Styling: CSS Modules

## Key Features Delivered

- ✅ **Dynamic behavior** based on user intent
- ✅ **Intelligent detection** of email operations vs conversation  
- ✅ **Function calling** with full prompt processing
- ✅ **Context-aware responses** using conversation history
- ✅ **Visual differentiation** between response types
- ✅ **Robust error handling** and fallbacks
- ✅ **Professional UI/UX** with modern styling

## Files Modified

### Backend
- `/src/backend/messages/settings.py` - Added chatbot to INSTALLED_APPS
- `/src/backend/messages/urls.py` - Added chatbot URL inclusion
- `/src/backend/chatbot/views.py` - Enhanced simple_chat_api endpoint
- `/src/backend/chatbot/chatbot.py` - Added intent detection and conversation methods
- `/src/backend/chatbot/urls.py` - Added simple chat endpoint

### Frontend
- `/src/frontend/src/features/layouts/components/thread-bot/components/chat-window/index.tsx` - Enhanced chat component
- `/src/frontend/src/features/layouts/components/thread-bot/components/chat-window/ChatWindow.module.css` - Added styling

## Troubleshooting Notes

1. **Port Conflict**: Initial error with port 3000 being used by both npm and Docker frontend service
2. **Intent Detection**: Initially used function calling approach, switched to keyword + AI analysis due to Albert API limitations
3. **Response Format**: Adjusted backend response format to match frontend expectations
4. **Conversation History**: Implemented to maintain context across messages

## Success Metrics

- ✅ Django check passes with no issues
- ✅ All four intent types working correctly
- ✅ Conversation history maintained
- ✅ Visual differentiation implemented
- ✅ Professional user experience achieved
- ✅ Robust error handling in place

This implementation provides a sophisticated email assistant that seamlessly handles both casual conversation and specific email management tasks with intelligent function calling based on user intent.
