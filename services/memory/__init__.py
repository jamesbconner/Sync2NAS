"""
Conversation Memory Services for Sync2NAS.

This module provides placeholder infrastructure for future conversation memory
capabilities using LangChain memory components.

Future Use Cases:
- Multi-turn conversations with LLM services
- Context preservation across filename parsing sessions
- User preference learning and adaptation
- Session-based configuration and state management

Planned LangChain Integration:
- ConversationBufferMemory for recent conversation history
- ConversationSummaryMemory for long conversation summarization
- VectorStoreRetrieverMemory for semantic conversation search
- Custom memory implementations for show/episode context

Example Future Usage:
    ```python
    from services.memory import ConversationMemory
    
    # Initialize conversation memory
    memory = ConversationMemory(
        memory_type="buffer",
        max_token_limit=2000
    )
    
    # Use in LangChain chains
    chain = create_filename_parser_with_memory(memory=memory)
    
    # Maintain context across multiple parsing operations
    result1 = chain.invoke({"filename": "show1_ep1.mkv"})
    result2 = chain.invoke({"filename": "show1_ep2.mkv"})  # Remembers show1 context
    ```

Integration Points:
- services.llm.chains: Enhanced chains with memory support
- cli.main: Session-based memory management
- api.routes: Conversation-aware API endpoints
- gui.main: Persistent GUI conversation state
"""

# Placeholder imports for future implementation
# from langchain.memory import ConversationBufferMemory
# from langchain.memory import ConversationSummaryMemory
# from langchain.memory import VectorStoreRetrieverMemory

__all__ = [
    # Future exports will include:
    # 'ConversationMemory',
    # 'SessionMemory', 
    # 'UserPreferenceMemory',
    # 'ShowContextMemory'
]