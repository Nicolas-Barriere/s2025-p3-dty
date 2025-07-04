# Email Response Generator

This module provides functionality to generate AI-powered responses to emails with a single click.

## Features

1. **Automatic Response Generation**: Generate professional responses to emails based on their content
2. **Draft Creation**: Automatically create draft replies with the generated content
3. **Reply-All Support**: Option to include all original recipients in the generated response
4. **Context-Aware Responses**: Extracts key points from emails to generate more relevant responses

## Components

This module consists of several key components:

1. **API Endpoint**: `/api/answer_generator/generate-email-response/` for triggering response generation
2. **Chatbot Interface**: Simplified interface for generating responses (can be extended with a real AI service)
3. **Email Utilities**: Functions for retrieving email content and creating draft responses

## Usage

The module is integrated with the frontend through a "Générer une réponse" button next to the regular "Répondre" button in the thread view.

### API Flow

1. Frontend calls the API with a message ID, mailbox ID, and reply-all flag
2. Backend retrieves the original message content
3. The chatbot generates a professional response based on subject and key points
4. A draft reply is created in the user's mailbox
5. The frontend refreshes to show the newly created draft

## Implementation Details

### Response Generation

The chatbot extracts key information from the email:
- Email subject
- Key questions or requests in the body
- Sender information

It then structures a professional response that acknowledges these elements.

### HTML Content Handling

When an email contains HTML but no text body, a simple HTML cleaner converts the content to plain text for better analysis.

## Configuration

The module uses a simple chatbot implementation that can be extended with a real AI service if needed.

```python
from answer_generator.chatbot import get_chatbot

chatbot = get_chatbot()
response = chatbot.process_user_message(prompt, user_id, [])
```

## Error Handling

All functions follow a consistent error handling pattern, returning clear error messages in case of failure and providing detailed logging for troubleshooting.
