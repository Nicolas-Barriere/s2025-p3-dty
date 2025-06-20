# Technical Analysis: Connecting Chatbot Functions to Real User Emails

## Executive Summary

This document outlines the technical approach for connecting the existing Albert chatbot functions (summarize, reply, classify) to real email data managed by the messaging application. The analysis covers the required infrastructure, API modifications, and implementation strategy to enable the chatbot to operate on actual user emails instead of freeform text inputs.

## Current State Analysis

### Existing Chatbot Functions
The application already implements three core AI functions:
- **✂️ Email Summarization** (`summarize_mail`) 
- **✉️ Reply Generation** (`generate_mail_answer`)
- **🏷️ Email Classification** (`classify_mail`)

### Current Architecture
- **Frontend**: React-based chat interface in `/src/frontend/src/features/layouts/components/thread-bot/`
- **Backend**: Django-based chatbot module in `/src/backend/chatbot/`
- **API Integration**: REST endpoints exposed at `/mails/chatbot/`
- **Database**: Sophisticated email system with `Message`, `Thread`, `Mailbox`, and `Contact` models

### Database Schema Summary
```
Thread (id, subject, snippet, has_unread, has_draft, etc.)
├── ThreadAccess (thread, mailbox, role) - Controls access permissions
├── Message (id, thread, subject, sender, parent, is_draft, etc.)
│   ├── MessageRecipient (message, contact, type[TO/CC/BCC])
│   └── raw_mime (binary email content)
└── Mailbox (local_part, domain) - Email addresses
    └── MailboxAccess (mailbox, user, role) - User permissions
```

## Technical Integration Plan

### 1. Email Retrieval Service

#### 1.1 Core Email Retrieval Utility
Create a new service class in `/src/backend/chatbot/services/email_service.py`:

```python
from typing import Optional, Dict, Any, List
from django.contrib.auth.models import User
from core import models
from django.db.models import Q

class EmailRetrievalService:
    """Service for retrieving and processing emails for chatbot operations."""
    
    def __init__(self, user: User):
        self.user = user
    
    def get_message_by_id(self, message_id: str) -> Optional[models.Message]:
        """Retrieve a specific message by ID with permission checking."""
        try:
            return models.Message.objects.select_related(
                'thread', 'sender'
            ).prefetch_related(
                'recipients__contact'
            ).get(
                id=message_id,
                thread__accesses__mailbox__accesses__user=self.user
            )
        except models.Message.DoesNotExist:
            return None
    
    def get_latest_message_in_thread(self, thread_id: str) -> Optional[models.Message]:
        """Get the most recent message in a thread."""
        try:
            thread = models.Thread.objects.get(
                id=thread_id,
                accesses__mailbox__accesses__user=self.user
            )
            return thread.messages.filter(
                ~Q(is_draft=True)
            ).order_by('-created_at').first()
        except models.Thread.DoesNotExist:
            return None
    
    def search_messages_by_sender(self, sender_name: str, limit: int = 5) -> List[models.Message]:
        """Find recent messages from a specific sender."""
        return models.Message.objects.filter(
            sender__name__icontains=sender_name,
            thread__accesses__mailbox__accesses__user=self.user
        ).select_related('thread', 'sender').order_by('-created_at')[:limit]
    
    def extract_email_content(self, message: models.Message) -> Dict[str, Any]:
        """Extract structured content from a message for AI processing."""
        # Get parsed email data
        parsed_data = message.get_parsed_data()
        
        # Extract text content
        text_body = ""
        if parsed_data and 'textBody' in parsed_data:
            text_body = "\n".join([part.get('content', '') for part in parsed_data['textBody']])
        
        # Fallback to HTML if no text
        if not text_body and parsed_data and 'htmlBody' in parsed_data:
            # Simple HTML to text conversion (could be enhanced)
            import re
            html_content = "\n".join([part.get('content', '') for part in parsed_data['htmlBody']])
            text_body = re.sub(r'<[^>]+>', '', html_content)
        
        return {
            'content': text_body or message.subject,  # Fallback to subject
            'sender': message.sender.email,
            'sender_name': message.sender.name or message.sender.email,
            'subject': message.subject,
            'created_at': message.created_at.isoformat(),
            'recipients': {
                'to': [r.contact.email for r in message.recipients.filter(type='to')],
                'cc': [r.contact.email for r in message.recipients.filter(type='cc')],
                'bcc': [r.contact.email for r in message.recipients.filter(type='bcc')]
            }
        }
```

#### 1.2 Intent Processing Enhancement
Enhance the existing intent detection in `/src/backend/chatbot/chatbot.py`:

```python
def detect_email_intent(self, user_message: str, user: User) -> Dict[str, Any]:
    """Enhanced intent detection that can identify email references."""
    
    # Try to extract email identifiers from the message
    email_context = self._extract_email_references(user_message, user)
    
    # Enhanced keyword detection with email context
    message_lower = user_message.lower()
    
    intent_patterns = {
        'summarize_email': [
            'résume le message de',
            'résume l\'email de',
            'que dit le message de',
            'synthèse du dernier email',
            'résume le dernier message'
        ],
        'generate_reply': [
            'réponds à',
            'écris une réponse à',
            'réponds au message de',
            'génère une réponse pour'
        ],
        'classify_email': [
            'classe le message de',
            'catégorise l\'email de',
            'quel type de message est'
        ]
    }
    
    detected_intent = 'conversation'
    confidence = 0.5
    
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if pattern in message_lower:
                detected_intent = intent
                confidence = 0.9
                break
        if confidence > 0.8:
            break
    
    return {
        'success': True,
        'intent': detected_intent,
        'confidence': confidence,
        'email_context': email_context,
        'extracted_content': user_message,
        'reasoning': f'Pattern matching: {detected_intent}'
    }

def _extract_email_references(self, message: str, user: User) -> Dict[str, Any]:
    """Extract email references from user message."""
    email_service = EmailRetrievalService(user)
    
    # Look for sender names in the message
    words = message.split()
    potential_senders = [word.strip('.,!?') for word in words if len(word) > 2]
    
    # Try to find messages from mentioned senders
    referenced_messages = []
    for sender in potential_senders[:3]:  # Limit search
        messages = email_service.search_messages_by_sender(sender, limit=1)
        if messages:
            referenced_messages.extend(messages)
    
    # Look for keywords indicating "latest" or "last"
    if any(keyword in message.lower() for keyword in ['dernier', 'dernière', 'récent', 'latest']):
        # Get user's mailboxes and find latest message
        try:
            latest_message = models.Message.objects.filter(
                thread__accesses__mailbox__accesses__user=user,
                ~Q(is_draft=True)
            ).order_by('-created_at').first()
            
            if latest_message:
                referenced_messages = [latest_message]
        except:
            pass
    
    return {
        'referenced_messages': [msg.id for msg in referenced_messages],
        'message_count': len(referenced_messages),
        'primary_message': referenced_messages[0].id if referenced_messages else None
    }
```

### 2. Enhanced Chatbot API Integration

#### 2.1 Modified Chatbot Views
Update `/src/backend/chatbot/views.py` to handle email-specific requests:

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhanced_chat_api(request):
    """Enhanced chat endpoint with email integration."""
    try:
        user = request.user
        data = request.data
        
        message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        context = data.get('context', {})  # New: context from frontend
        
        # Initialize services
        chatbot = get_chatbot()
        email_service = EmailRetrievalService(user)
        
        # Enhanced intent detection with email context
        intent_result = chatbot.detect_email_intent(message, user)
        
        if not intent_result.get('success'):
            return chatbot.chat_conversation(message, conversation_history)
        
        intent = intent_result.get('intent', 'conversation')
        email_context = intent_result.get('email_context', {})
        
        # Handle email-specific intents
        if intent in ['summarize_email', 'generate_reply', 'classify_email']:
            return _handle_email_intent(
                intent, message, email_context, context, 
                email_service, chatbot, user
            )
        
        # Default to conversation
        return chatbot.chat_conversation(message, conversation_history)
        
    except Exception as e:
        logger.error(f"Error in enhanced_chat_api: {e}")
        return JsonResponse({
            'success': True,
            'response': 'Une erreur s\'est produite. Comment puis-je vous aider autrement ?',
            'type': 'error'
        })

def _handle_email_intent(intent, message, email_context, context, email_service, chatbot, user):
    """Handle email-specific chatbot intents."""
    
    # Try to get specific message ID from context (sent by frontend)
    message_id = context.get('message_id')
    if message_id:
        target_message = email_service.get_message_by_id(message_id)
    else:
        # Try to find message from intent detection
        primary_message_id = email_context.get('primary_message')
        target_message = email_service.get_message_by_id(primary_message_id) if primary_message_id else None
    
    if not target_message:
        return JsonResponse({
            'success': True,
            'response': 'Je n\'ai pas pu identifier l\'email à traiter. Pouvez-vous être plus spécifique ?',
            'type': 'error'
        })
    
    # Extract email content
    email_data = email_service.extract_email_content(target_message)
    
    # Route to appropriate function
    if intent == 'summarize_email':
        result = chatbot.summarize_mail(
            email_data['content'],
            email_data['sender'],
            email_data['subject']
        )
        
        if result.get('success'):
            summary_data = result.get('summary', {})
            summary_text = summary_data.get('summary', 'Résumé généré avec succès.')
            
            return JsonResponse({
                'success': True,
                'response': f"📧 **Résumé de l'email de {email_data['sender_name']}:**\n\n{summary_text}",
                'type': 'email_summary',
                'function_used': 'summarize_mail',
                'email_id': str(target_message.id),
                'metadata': {
                    'sender': email_data['sender_name'],
                    'subject': email_data['subject'],
                    'urgency': summary_data.get('urgency_level', 'medium')
                }
            })
    
    elif intent == 'generate_reply':
        result = chatbot.generate_mail_answer(
            email_data['content'],
            context.get('reply_context', ''),
            context.get('tone', 'professional'),
            'french'
        )
        
        if result.get('success'):
            response_data = result.get('response', {})
            reply_text = response_data.get('response', 'Réponse générée avec succès.')
            reply_subject = response_data.get('subject', f"Re: {email_data['subject']}")
            
            return JsonResponse({
                'success': True,
                'response': f"✉️ **Réponse proposée à {email_data['sender_name']}:**\n\n**Sujet:** {reply_subject}\n\n{reply_text}",
                'type': 'email_reply',
                'function_used': 'generate_mail_answer',
                'email_id': str(target_message.id),
                'metadata': {
                    'original_sender': email_data['sender_name'],
                    'reply_subject': reply_subject,
                    'tone': response_data.get('tone_used', 'professional')
                }
            })
    
    elif intent == 'classify_email':
        result = chatbot.classify_mail(
            email_data['content'],
            email_data['sender'],
            email_data['subject']
        )
        
        if result.get('success'):
            classification_data = result.get('classification', {})
            category = classification_data.get('primary_category', 'normal')
            confidence = classification_data.get('confidence_score', 0.5)
            reasoning = classification_data.get('reasoning', 'Classification automatique')
            
            return JsonResponse({
                'success': True,
                'response': f"🏷️ **Classification de l'email de {email_data['sender_name']}:**\n\n**Catégorie:** {category}\n**Confiance:** {confidence:.0%}\n**Explication:** {reasoning}",
                'type': 'email_classification',
                'function_used': 'classify_mail',
                'email_id': str(target_message.id),
                'metadata': {
                    'sender': email_data['sender_name'],
                    'category': category,
                    'confidence': confidence
                }
            })
    
    return JsonResponse({
        'success': True,
        'response': 'Je n\'ai pas pu traiter cette demande spécifique.',
        'type': 'error'
    })
```

#### 2.2 New URL Patterns
Add to `/src/backend/chatbot/urls.py`:

```python
urlpatterns = [
    # Existing endpoints...
    path('', views.simple_chat_api, name='simple_chat'),
    
    # New enhanced endpoint with email integration
    path('enhanced/', views.enhanced_chat_api, name='enhanced_chat'),
    
    # Direct email operation endpoints
    path('email/<uuid:message_id>/summarize/', views.summarize_email_by_id, name='summarize_email_by_id'),
    path('email/<uuid:message_id>/reply/', views.generate_reply_by_id, name='generate_reply_by_id'),
    path('email/<uuid:message_id>/classify/', views.classify_email_by_id, name='classify_email_by_id'),
]
```

### 3. Frontend Integration Strategy

#### 3.1 Enhanced Chat Window Component
Modify `/src/frontend/src/features/layouts/components/thread-bot/components/chat-window/index.tsx`:

```typescript
export const ChatWindow = ({ selectedThread, selectedMessage }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([...])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMsg: ChatMessage = { 
            role: "user", 
            text: input, 
            timestamp: new Date() 
        }
        setMessages(prev => [...prev, userMsg])
        setInput("")
        setIsLoading(true)

        try {
            // Build conversation history
            const conversationHistory = messages.slice(-10).map(msg => ({
                role: msg.role === "bot" ? "assistant" : "user",
                content: msg.text
            }))

            // Enhanced payload with email context
            const payload = {
                message: input,
                conversation_history: conversationHistory,
                context: {
                    // Pass current email context to chatbot
                    message_id: selectedMessage?.id,
                    thread_id: selectedThread?.id,
                    mailbox_id: getCurrentMailboxId(), // From context
                    tone: 'professional' // Could be user preference
                }
            }

            const res = await fetch("http://localhost:8071/mails/chatbot/enhanced/", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${getAuthToken()}` // Add auth
                },
                body: JSON.stringify(payload),
            })

            const data = await res.json()
            
            if (data.success && data.response) {
                const botMsg: ChatMessage = { 
                    role: "bot", 
                    text: data.response,
                    type: data.type || "conversation",
                    function_used: data.function_used,
                    email_id: data.email_id,
                    metadata: data.metadata,
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, botMsg])
            } else {
                // Error handling...
            }
        } catch (err) {
            // Error handling...
        } finally {
            setIsLoading(false)
        }
    }

    // Enhanced message formatting with email metadata
    const formatMessage = (msg: ChatMessage) => {
        let className = `${styles.msg} ${msg.role === 'user' ? styles.user : styles.bot}`
        
        if (msg.type === 'email_summary') className += ` ${styles.emailSummary}`
        if (msg.type === 'email_reply') className += ` ${styles.emailReply}`
        if (msg.type === 'email_classification') className += ` ${styles.emailClassification}`

        return (
            <div key={msg.timestamp?.getTime()} className={className}>
                <div className={styles.msgContent}>
                    {msg.text.split('\n').map((line, i) => (
                        <div key={i}>{line}</div>
                    ))}
                </div>
                
                {msg.metadata && (
                    <div className={styles.msgMetadata}>
                        {msg.email_id && (
                            <small>📧 Email ID: {msg.email_id}</small>
                        )}
                        {msg.metadata.sender && (
                            <small>👤 Expéditeur: {msg.metadata.sender}</small>
                        )}
                        {msg.metadata.category && (
                            <small>🏷️ Catégorie: {msg.metadata.category}</small>
                        )}
                    </div>
                )}
                
                {msg.function_used && (
                    <div className={styles.msgMeta}>
                        <small>🔧 Fonction: {msg.function_used}</small>
                    </div>
                )}
                
                <div className={styles.msgTimestamp}>
                    <small>{msg.timestamp?.toLocaleTimeString()}</small>
                </div>
            </div>
        )
    }

    return (
        <div className={styles.chatWindow}>
            {/* Add context info bar */}
            {selectedMessage && (
                <div className={styles.contextBar}>
                    <small>
                        💬 Contexte: Email de {selectedMessage.sender.name} - "{selectedMessage.subject}"
                    </small>
                </div>
            )}
            
            <div className={styles.chatMessages}>
                {messages.map((msg, i) => formatMessage(msg))}
                {isLoading && <LoadingIndicator />}
            </div>
            
            <div className={styles.chatInput}>
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && sendMessage()}
                    placeholder={selectedMessage ? 
                        "Demandez-moi de résumer, répondre ou classer cet email..." :
                        "Tapez votre message..."
                    }
                    disabled={isLoading}
                />
                <button onClick={sendMessage} disabled={isLoading || !input.trim()}>
                    {isLoading ? "..." : "Envoyer"}
                </button>
            </div>
        </div>
    )
}
```

#### 3.2 Action Bar Integration
Enhance `/src/frontend/src/features/layouts/components/thread-bot/components/thread-action-bar/index.tsx`:

```typescript
export const ActionBar = ({ selectedMessage, onQuickAction }) => {
    const quickActions = [
        {
            icon: "✂️",
            label: "Résumer",
            action: () => onQuickAction("summarize", selectedMessage)
        },
        {
            icon: "✉️", 
            label: "Répondre",
            action: () => onQuickAction("reply", selectedMessage)
        },
        {
            icon: "🏷️",
            label: "Classer", 
            action: () => onQuickAction("classify", selectedMessage)
        }
    ]

    return (
        <div className="action-bar">
            <div className="quick-actions">
                {quickActions.map((action, index) => (
                    <button
                        key={index}
                        className="quick-action-btn"
                        onClick={action.action}
                        disabled={!selectedMessage}
                        title={action.label}
                    >
                        <span className="icon">{action.icon}</span>
                        <span className="label">{action.label}</span>
                    </button>
                ))}
            </div>
        </div>
    )
}
```

### 4. Security and Permission Handling

#### 4.1 Permission Verification
The system leverages the existing permission model:
- **ThreadAccess**: Controls access to email threads
- **MailboxAccess**: Controls access to mailboxes
- All chatbot operations verify user permissions before processing emails

#### 4.2 Data Privacy Considerations
- Email content is processed in-memory only
- No email content is stored in chatbot logs
- All operations respect existing mailbox sharing permissions
- API requests include proper authentication tokens

### 5. User Experience Enhancements

#### 5.1 Context-Aware Prompting
The chatbot becomes context-aware by:
- Detecting when a specific email is selected in the UI
- Providing contextual quick actions
- Showing email metadata in responses
- Maintaining conversation context across operations

#### 5.2 Natural Language Processing
Enhanced prompts support:
- "Résume le dernier message de Claire"
- "Génère une réponse polie à cet email"
- "Dans quelle catégorie ranger ce message ?"
- "Que dit l'email d'hier de Jean ?"

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
1. Implement `EmailRetrievalService`
2. Enhance intent detection with email context
3. Create enhanced chatbot API endpoint
4. Basic frontend integration

### Phase 2: Advanced Features (Week 3-4)
1. Implement direct email operation endpoints
2. Enhanced UI components with metadata display
3. Quick action buttons
4. Context-aware prompting

### Phase 3: Polish and Testing (Week 5-6)
1. Comprehensive testing with real email data
2. Performance optimization
3. Error handling and edge cases
4. User experience refinements

## API Examples

### Frontend to Chatbot Communication
```typescript
// Context-aware message processing
POST /mails/chatbot/enhanced/
{
    "message": "Résume cet email",
    "context": {
        "message_id": "123e4567-e89b-12d3-a456-426614174000",
        "thread_id": "456e7890-e89b-12d3-a456-426614174000",
        "tone": "professional"
    },
    "conversation_history": [...]
}

// Direct email operations
POST /mails/chatbot/email/123e4567-e89b-12d3-a456-426614174000/summarize/
{
    "context": {"detailed": true}
}
```

### Chatbot Response Format
```json
{
    "success": true,
    "response": "📧 **Résumé de l'email de jean.dupont@example.com:**\n\nCet email concerne une demande urgente...",
    "type": "email_summary",
    "function_used": "summarize_mail",
    "email_id": "123e4567-e89b-12d3-a456-426614174000",
    "metadata": {
        "sender": "Jean Dupont",
        "subject": "Demande urgente",
        "urgency": "high",
        "confidence": 0.95
    }
}
```

## Conclusion

This integration approach enables seamless connection between the chatbot's AI capabilities and the application's real email data while:
- Maintaining existing security and permission models
- Providing intuitive user experience enhancements
- Supporting both natural language queries and direct actions
- Enabling progressive enhancement without disrupting current functionality

The implementation leverages the robust existing architecture and can be developed incrementally, ensuring minimal risk and maximum compatibility with the current system.
