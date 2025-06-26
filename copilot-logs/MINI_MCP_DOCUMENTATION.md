# Mini Function-Calling Controller (Mini-MCP)

## Overview

The Mini-MCP is a flexible function calling system that replaces the previous rigid, pattern-based approach with a dynamic, model-driven controller. It allows the AI model to choose which functions to call, in what order, and how many steps are needed based on the user's query and available tools.

## Key Features

### 🎯 **Dynamic Function Selection**
- The model analyzes the user query and available tools
- Decides which functions to use without predefined workflows
- Supports both single and multi-step function calls
- No hardcoded intent detection patterns

### 🔄 **Iterative Processing Loop**
- Runs up to 5 iterations to prevent infinite loops
- Each iteration can involve multiple function calls
- Context accumulates between iterations
- Model decides when to stop based on completeness

### 🧠 **Intelligent Context Building**
- Results from previous functions inform subsequent calls
- Conversation context grows with each successful step
- Failed steps are logged and handled gracefully
- Final response includes comprehensive step summary

### 📊 **Comprehensive Response Formatting**
- Shows all steps taken and their outcomes
- Provides detailed results for key functions
- Includes error summaries for failed steps
- Supports different response types based on function outcomes

## Architecture

### Main Components

1. **`_handle_multi_step_functions()`** - Main controller method
2. **`_summarize_function_result()`** - Context summarization helper
3. **`_format_mini_mcp_response()`** - Response formatting helper

### Flow Diagram

```
User Query → Mini-MCP Controller
    ↓
Dynamic System Prompt + Available Tools
    ↓
Model Analysis & Function Selection
    ↓
Iterative Execution Loop (max 5 iterations)
    ├── Execute Function Calls
    ├── Accumulate Context
    ├── Check for Completion
    └── Continue or Finish
    ↓
Comprehensive Response Formatting
    ↓
Final Response to User
```

## System Prompt Strategy

The mini-MCP uses a dynamic system prompt that:

- **Explains all available tools** and their capabilities
- **Provides strategy examples** without rigid workflows
- **Encourages creative combinations** of tools
- **Emphasizes intelligent decision-making** by the model
- **Supports both simple and complex requests**

## Example Workflows

### Simple Workflow: Email Summary
**User:** "Résume l'email de Jean sur le projet Alpha"

**Mini-MCP Process:**
1. Model analyzes query → detects need for email retrieval + summarization
2. Calls `retrieve_email_content(query="jean projet alpha")`
3. Calls `summarize_email(email_content=retrieved_content)`
4. Formats response with both steps

### Complex Workflow: Reply with Draft
**User:** "Réponds à l'email de Marie concernant la réunion"

**Mini-MCP Process:**
1. Model analyzes query → detects need for retrieval + reply + draft creation
2. Calls `retrieve_email_content(query="marie réunion")`
3. Calls `generate_email_reply(original_email=retrieved_content)`
4. Calls `create_draft_email(body=generated_reply, recipients=...)`
5. Formats comprehensive response showing all steps

### Batch Processing Workflow
**User:** "Trouve et classifie tous mes emails urgents"

**Mini-MCP Process:**
1. Model analyzes query → detects need for search + classification
2. Calls `search_emails(query="urgent")`
3. For each email found, calls `classify_email(email_content=...)`
4. Formats response with search results and classifications

## Error Handling

The mini-MCP provides robust error handling:

- **Partial Failures:** Continue processing even if some steps fail
- **Context Preservation:** Maintain successful results even with failures
- **Error Reporting:** Clear error messages in final response
- **Graceful Degradation:** Provide useful response even with limited success

## Performance Features

### Logging and Monitoring
- Detailed logging at each iteration
- Function execution timing
- Success/failure tracking
- Context accumulation monitoring

### Efficiency Optimizations
- Maximum iteration limit prevents infinite loops
- Context summarization reduces memory usage
- Early termination when model indicates completion
- Intelligent function result caching

## Comparison with Previous Approach

| Aspect | Previous Approach | Mini-MCP |
|--------|------------------|----------|
| **Function Selection** | Hardcoded patterns | Model-driven |
| **Workflows** | Predefined sequences | Dynamic decision-making |
| **Context Handling** | Limited accumulation | Rich context building |
| **Error Recovery** | Rigid failure handling | Graceful degradation |
| **Extensibility** | Requires code changes | Automatic with new tools |
| **Flexibility** | Pattern-bound | Fully adaptive |

## Benefits

### For Developers
- **Easier Maintenance:** No hardcoded workflows to maintain
- **Better Extensibility:** New tools work automatically
- **Cleaner Code:** Simplified architecture without pattern matching
- **Enhanced Debugging:** Comprehensive logging and monitoring

### For Users
- **More Intelligent Responses:** Model makes better decisions
- **Flexible Interactions:** Support for creative combinations
- **Better Error Handling:** Graceful degradation and clear feedback
- **Richer Context:** Comprehensive response with step details

### For the System
- **Scalability:** Easily supports new tools and functions
- **Reliability:** Robust error handling and recovery
- **Performance:** Efficient iteration and context management
- **Monitoring:** Detailed logging and success tracking

## Usage Examples

### Integration in Process User Message
```python
def process_user_message(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    # Try mini-MCP first
    mini_mcp_result = self._handle_multi_step_functions(user_message, user_id, conversation_history)
    if mini_mcp_result is not None:
        return mini_mcp_result
    
    # Fallback to regular processing
    # ... regular single-function processing
```

### Response Format
```json
{
    "success": true,
    "response": "🔧 **Actions effectuées:** 3 étape(s) - 3 réussie(s)\n\n**Détail des étapes:**\n✅ **Étape 1:** Email récupéré: 'Projet Alpha' de Jean\n✅ **Étape 2:** Email résumé avec succès\n✅ **Étape 3:** Brouillon créé avec succès\n\n📋 **Résumé:**\nJean demande une mise à jour sur le projet Alpha...",
    "type": "mini_mcp_completed",
    "steps_total": 3,
    "steps_successful": 3,
    "steps_failed": 0,
    "final_function": "create_draft_email"
}
```

## Future Enhancements

### Planned Improvements
- **Parallel Function Execution:** Support for concurrent function calls
- **Function Call Optimization:** Smart caching and result reuse
- **Advanced Context Management:** Semantic context compression
- **User Preference Learning:** Adapt to user patterns over time

### Integration Possibilities
- **Webhook Support:** External tool integration
- **Real-time Collaboration:** Multi-user function calling
- **Advanced Analytics:** Function usage pattern analysis
- **API Gateway Integration:** External service function calls

## Conclusion

The Mini-MCP represents a significant evolution in the chatbot's function calling capabilities. By removing rigid patterns and embracing model-driven decision making, it provides a more flexible, intelligent, and maintainable approach to complex email processing tasks.

The system's ability to dynamically compose function calls, accumulate context, and provide comprehensive responses makes it well-suited for the complex, varied needs of email management users.
