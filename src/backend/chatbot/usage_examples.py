"""
Usage examples for the enhanced chatbot with email content retrieval functionality.

This demonstrates how the new retrieve_email_content tool works with chained function calls.
"""

# Example usage scenarios:

# 1. Simple email content retrieval
user_query_1 = "Trouve moi l'email de Jean concernant le projet Alpha"
# The chatbot will:
# - Use retrieve_email_content with query "Jean projet Alpha"
# - Return the email content and metadata
# - Suggest next actions (summarize, reply, classify)

# 2. Chained operations - Summarize specific email
user_query_2 = "Résume l'email de Marie sur le budget"
# The chatbot will:
# - Use retrieve_email_content with query "Marie budget"
# - Automatically use summarize_email with the retrieved content
# - Return a comprehensive summary with email context

# 3. Chained operations - Reply to specific email
user_query_3 = "Réponds à l'email de Pierre concernant la réunion"
# The chatbot will:
# - Use retrieve_email_content with query "Pierre réunion"
# - Automatically use generate_email_reply with the retrieved content
# - Return a professional reply with email context

# 4. Chained operations - Classify specific email
user_query_4 = "Classifie l'email du support technique"
# The chatbot will:
# - Use retrieve_email_content with query "support technique"
# - Automatically use classify_email with the retrieved content
# - Return classification results with email context

# 5. Regular operations (no chaining needed)
user_query_5 = "Montre moi mes emails récents"
# The chatbot will:
# - Use get_recent_emails directly
# - Return recent emails list

# Example response flow for chained operations:
"""
User: "Résume l'email de Jean sur le projet Alpha"

Step 1: Chatbot detects chained action
- Action: summarize_email
- Target: specific email ("Jean sur le projet Alpha")

Step 2: Retrieve email content
- Function: retrieve_email_content
- Query: "Jean projet Alpha"
- Result: Full email content + metadata

Step 3: Execute summary
- Function: summarize_email
- Input: Retrieved email content
- Result: Structured summary

Step 4: Format response
- Combine email context + summary
- Show: "📧 Email traité: Projet Alpha (de Jean Dupont)
         📧 Résumé de l'email: [summary content]"
"""

# New tool definition added to chatbot:
retrieve_email_content_tool = {
    "name": "retrieve_email_content",
    "description": "Récupère le contenu complet de l'email qui correspond le mieux à la requête de l'utilisateur",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Requête de l'utilisateur pour trouver l'email le plus pertinent"
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximum d'emails à rechercher",
                "default": 5
            }
        },
        "required": ["query"]
    }
}

# The tool works by:
# 1. Using search_messages to find emails matching the query
# 2. Taking the best match (first result)
# 3. Using get_message_full_content to retrieve complete email content
# 4. Returning structured data for further processing

# Benefits:
# - Intelligent email retrieval based on natural language queries
# - Seamless integration with existing email processing tools
# - Automatic chaining for complex user requests
# - Enhanced user experience with contextual responses
