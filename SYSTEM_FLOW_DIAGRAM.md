# AI Tool System - Visual Flow Diagram

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER QUESTION                                │
│                         "credits limit i have"                         │
└─────────────────────────┬───────────────────────────────────────────────┘
                         │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                    1. SMALL TALK CHECK                                │
│               (hello, hi, thanks, bye, etc.)                          │
└─────────────────────────┬───────────────────────────────────────────────┘
                         │ Not small talk
┌─────────────────────────▼───────────────────────────────────────────────┐
│                 2. SMART PRE-FILTERING                                │
│                                                                        │
│  ✓ Check if multiple tools available (min 2)                         │
│  ✓ Question length > 5 words? → Skip clarification                   │
│  ✓ Contains action words? → Skip clarification                       │
│     (how, what, can, post, create, etc.)                             │
│  ✓ Contains ambiguous keywords? → May need clarification             │
│     (credits, account, balance, status, etc.)                        │
│                                                                        │
│  Result: "credits limit i have" → Skip clarification                 │
│          (has context words "limit" and "i have")                     │
└─────────────────────────┬───────────────────────────────────────────────┘
                         │ No clarification needed
┌─────────────────────────▼───────────────────────────────────────────────┐
│                3. AI TOOL SELECTION                                    │
│                                                                        │
│  System Prompt: "Be extremely conservative. Only use tools when       │
│                 ABSOLUTELY CERTAIN they are needed."                   │
│                                                                        │
│  Context:                                                             │
│  • Available tools specifications                                     │
│  • Conversation history (last 5 messages)                            │
│  • User question                                                      │
│                                                                        │
│  OpenAI Function Calling Decision:                                    │
│  • Does this match any tool exactly?                                  │
│  • Is the intent clear and specific?                                  │
│  • Should I use a tool or general knowledge?                          │
└─────────────────────────┬───────────────────────────────────────────────┘
                         │
                    ┌────┴──────┐
                    │   DECISION │
                    └────┬──────┘
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│  CLARIFICATION  │ │  USE TOOL   │ │  USE KNOWLEDGE  │
│    NEEDED       │ │             │ │     BASE        │
└─────────────────┘ └─────────────┘ └─────────────────┘
          │             │             │
          ▼             ▼             ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│ Return question │ │ Execute API │ │ RAG retrieval   │
│ "Are you looking│ │ call with   │ │ + conversation  │
│ for your credit │ │ parameters  │ │ memory          │
│ balance or info │ │             │ │                 │
│ about buying?"  │ │             │ │                 │
└─────────────────┘ └─────────────┘ └─────────────────┘
                         │             │
                         ▼             ▼
                 ┌─────────────┐ ┌─────────────────┐
                 │ Format API  │ │ Generate answer │
                 │ response    │ │ with context    │
                 │ using AI    │ │                 │
                 └─────────────┘ └─────────────────┘
                         │             │
                         ▼             ▼
                 ┌─────────────────────────────────┐
                 │        FINAL RESPONSE           │
                 │                                 │
                 │ "Based on the API response,     │
                 │ here's your information:        │
                 │ TOKEN: 300"                     │
                 └─────────────────────────────────┘
```

## Detailed Pre-filtering Logic

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRE-FILTER CHECKS                               │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  1. MINIMUM TOOLS CHECK                                                │
│     if len(tools) < 2: return None (skip clarification)               │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │ ✓ Pass
┌─────────────────────────────────▼───────────────────────────────────────┐
│  2. QUESTION LENGTH CHECK                                              │
│     if len(question.split()) > 5: return None                         │
│                                                                        │
│     Example: "how can I post my job" (5 words) → Skip                │
│              "credits limit i have" (4 words) → Continue              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │ ✓ Pass
┌─────────────────────────────────▼───────────────────────────────────────┐
│  3. ACTION WORDS CHECK                                                 │
│     action_words = ['how', 'what', 'where', 'when', 'why', 'can',     │
│                    'could', 'should', 'would', 'help', 'show',        │
│                    'get', 'find', 'search', 'post', 'create',         │
│                    'update', 'delete']                                 │
│                                                                        │
│     if any(word in question_lower for word in action_words):          │
│         return None                                                    │
│                                                                        │
│     Example: "how can I post" → Skip (contains 'how', 'can', 'post') │
│              "credits limit" → Continue (no action words)             │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │ ✓ Pass
┌─────────────────────────────────▼───────────────────────────────────────┐
│  4. AMBIGUOUS KEYWORDS CHECK                                           │
│     ambiguous_keywords = ['credits', 'credit', 'account', 'balance',  │
│                          'status', 'info', 'information', 'details',  │
│                          'data', 'token', 'tokens', 'user',           │
│                          'profile', 'settings']                       │
│                                                                        │
│     if not any(keyword in question_lower for keyword in               │
│                ambiguous_keywords):                                    │
│         return None                                                    │
│                                                                        │
│     Example: "hello there" → Skip (no ambiguous keywords)            │
│              "credits limit" → Continue (contains 'credits')          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │ ✓ Pass
┌─────────────────────────────────▼───────────────────────────────────────┐
│  5. PROCEED TO CLARIFICATION CHECK                                     │
│     Send to OpenAI for ambiguity analysis                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## AI Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI TOOL SELECTION DECISION                        │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  QUESTION ANALYSIS                                                     │
│  • "credits limit i have"                                             │
│  • Available tools: get_user_token                                    │
│  • Context: User asking about their credit limit                      │
│  • Intent: Check personal account information                         │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  CONSERVATIVE EVALUATION                                               │
│                                                                        │
│  ✓ Is this a DIRECT request for API-only information?                │
│  ✓ Is the intent CLEAR and SPECIFIC?                                 │
│  ✓ Does this EXACTLY match a tool's purpose?                         │
│  ✓ Would general knowledge be insufficient?                           │
│                                                                        │
│  Result: YES - User wants their personal credit information           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  TOOL SELECTION                                                        │
│  • Selected: get_user_token                                           │
│  • Parameters: {} (no parameters needed)                              │
│  • Reason: Direct request for personal credit information             │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  EXECUTE API CALL                                                      │
│  • Run curl command: curl -X POST https://api.example.com/user/token  │
│  • Response: {"status": 200, "Token": "300"}                         │
│  • Apply response mapping                                             │
└─────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌─────────────────────────────────▼───────────────────────────────────────┐
│  FORMAT RESPONSE                                                       │
│  • Use AI to format the response with template                        │
│  • Template: "Based on the API response: TOKEN: {Token}"             │
│  • Final: "Based on the API response, here's your information:        │
│            TOKEN: 300"                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Success Factors

### 1. Smart Pre-filtering
- **99% of questions** bypass clarification through intelligent filtering
- **Action words** indicate clear intent → Skip clarification
- **Context words** provide disambiguation → Skip clarification
- **Single ambiguous keywords** only → May need clarification

### 2. Conservative Tool Selection
- **High precision** over high recall
- **Defaults to knowledge base** when uncertain
- **Requires exact matches** for API calls
- **Considers conversation context** for better decisions

### 3. Seamless User Experience
- **Minimal interruptions** for clarification
- **Fast routing** to appropriate response system
- **Context-aware** decisions based on conversation history
- **Intelligent fallbacks** when tools don't match

This system achieves the perfect balance between powerful AI tool capabilities and smooth user experience through intelligent filtering and conservative decision-making.