# AI Tool System - Complete Logic Documentation

## Overview
This document explains the complete logic flow of the AI-driven tool system that intelligently routes user questions between API tools and the RAG knowledge base.

## System Architecture

### 1. Main Entry Point (`rag_chain.py` - `get_answer()`)
```
User Question → Small Talk Check → AI Tool System → RAG Fallback
```

### 2. AI Tool Processing Flow (`ai_tool_executor.py`)

#### A. Initial Setup
- Load active API tools from database (ordered by priority)
- Convert tools to OpenAI Function Calling format
- Prepare conversation context

#### B. Smart Pre-filtering for Clarification
```python
# Pre-filtering Rules:
1. Skip if less than 2 tools available
2. Skip if question is longer than 5 words
3. Skip if question contains action words: how, what, where, when, why, can, could, should, would, help, show, get, find, search, post, create, update, delete
4. Skip if question doesn't contain ambiguous keywords: credits, credit, account, balance, status, info, information, details, data, token, tokens, user, profile, settings
5. Only proceed if question is potentially ambiguous
```

#### C. Clarification Decision Logic
```python
# Conservative Clarification Rules:
ONLY ask for clarification if:
- Question is a single generic word that could match multiple tools
- Question is so vague it's impossible to determine intent
- There are multiple tools that could handle the exact same keyword

DO NOT ask for clarification if:
- Question contains context or action words
- Question is a complete sentence
- Question has clear intent even if not perfectly specific
- Question doesn't match any tool closely
```

#### D. Tool Selection Logic
```python
# Conservative Tool Selection Rules:
1. Only use API tools when user's question DIRECTLY and SPECIFICALLY requests information that can ONLY be obtained from the API
2. If question is vague, general, or could be answered with general knowledge, DO NOT use any tools
3. If unsure whether to use a tool, DON'T use it - default to general knowledge
4. Look for EXACT matches between user's request and tool's purpose
5. Pay attention to context - similar words don't mean the same thing
```

## Complete System Flow

### Step 1: Question Analysis
```
User asks: "credits limit i have"
↓
System analyzes: Contains "credits" (ambiguous) + "limit" (specific) + "i have" (context)
↓
Pre-filter decision: Skip clarification (has context words)
```

### Step 2: Tool Selection Process
```
System builds messages with:
- Conservative system prompt
- Available tools context
- Conversation history (last 5 messages)
- User question

↓

OpenAI Function Calling analyzes:
- Does this match any tool exactly?
- Is the intent clear and specific?
- Should I use a tool or general knowledge?
```

### Step 3: Decision Tree
```
If clarification needed:
    → Return clarification question immediately
    
If tool should be used:
    → Extract parameters from question
    → Execute curl command with parameter replacement
    → Apply response mapping
    → Format response using AI template
    → Return formatted response
    
If no tool matches:
    → Fall back to RAG knowledge base
    → Use document chunks + conversation memory
    → Generate contextual response
```

## Example Flows

### Example 1: Ambiguous Single Word
```
User: "credits"
↓
Pre-filter: Contains ambiguous keyword "credits", no action words, short
↓
Clarification check: CLARIFICATION_NEEDED
↓
Response: "Are you looking for your credit balance or information about purchasing credits?"
```

### Example 2: Clear Intent with Context
```
User: "how can I post my job"
↓
Pre-filter: Contains action word "how", "can", "post" - Skip clarification
↓
Tool selection: No matching API tools for job posting
↓
Response: Falls back to RAG knowledge base
```

### Example 3: Specific API Request
```
User: "credits limit i have"
↓
Pre-filter: Has context words "limit" and "i have" - Skip clarification
↓
Tool selection: Matches "get_user_token" tool for credit information
↓
API execution: curl command executed
↓
Response: "Based on the API response, here's your information: TOKEN: 300"
```

## System Prompts

### Conservative Tool Selection Prompt
```
You are a conservative AI assistant that only uses API tools when you are ABSOLUTELY CERTAIN they are needed.

CRITICAL RULES:
1. Only use API tools when the user's question DIRECTLY and SPECIFICALLY requests information that can ONLY be obtained from the API
2. If the question is vague, general, or could be answered with general knowledge, DO NOT use any tools
3. If you're unsure whether to use a tool, DON'T use it - default to general knowledge
4. Look for EXACT matches between the user's request and the tool's purpose
5. Pay attention to context - similar words don't mean the same thing

Examples of when NOT to use tools:
- "Can you share your plan to buy credits" (asking about purchasing plans, not checking current balance)
- "How do I get more credits" (asking for instructions, not current status)
- "What are the credit options" (asking about available plans, not personal data)

Examples of when TO use tools:
- "What is my current credit limit" (directly asking for personal account data)
- "Show me my account balance" (directly requesting personal information)
- "What are my current credits" (directly asking for personal data)
```

### Clarification Detection Prompt
```
You are a conservative assistant that only asks for clarification when a question is EXTREMELY ambiguous and could match multiple available tools.

ONLY ask for clarification if:
1. The question is a single generic word that could match multiple tools
2. The question is so vague it's impossible to determine intent
3. There are multiple tools that could handle the exact same keyword

DO NOT ask for clarification if:
1. The question contains context or action words
2. The question is a complete sentence
3. The question has clear intent even if it's not perfectly specific
4. The question doesn't match any tool closely
```

## Key Benefits

### 1. Reduced Friction
- Most questions bypass clarification through smart pre-filtering
- Only truly ambiguous single-word queries trigger clarification
- Clear context prevents unnecessary interruptions

### 2. Conservative Approach
- Prevents incorrect API calls by being extremely selective
- Defaults to general knowledge when uncertain
- Reduces API usage and potential errors

### 3. Intelligent Routing
- Context-aware decision making
- Conversation history consideration
- Priority-based tool selection

### 4. User Experience
- Minimal interruptions for clarification
- Fast responses for clear questions
- Helpful clarification when truly needed

## Configuration

### Pre-filter Settings
```python
# Ambiguous keywords that might need clarification
ambiguous_keywords = [
    'credits', 'credit', 'account', 'balance', 'status', 'info', 
    'information', 'details', 'data', 'token', 'tokens', 'user', 
    'profile', 'settings'
]

# Action words that indicate clear intent
action_words = [
    'how', 'what', 'where', 'when', 'why', 'can', 'could', 
    'should', 'would', 'help', 'show', 'get', 'find', 'search', 
    'post', 'create', 'update', 'delete'
]

# Length threshold for automatic clarification skip
max_words_for_clarification = 5
```

### Tool Selection Settings
```python
# Conservative thresholds
require_exact_match = True
default_to_knowledge_base = True
conversation_context_length = 5  # Last 5 messages
```

This system provides intelligent, context-aware routing while maintaining a smooth user experience through conservative clarification and smart pre-filtering.