import json
import subprocess
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from openai import OpenAI
import os
from models import ApiTool

class AIToolExecutor:
    """AI-driven tool executor using OpenAI Function Calling"""
    
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()  # Remove any whitespace
        self.openai_client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
    
    def get_available_tools(self) -> List[ApiTool]:
        """Get all active API tools from database"""
        try:
            return ApiTool.query.filter_by(active=True).order_by(ApiTool.priority.desc()).all()
        except Exception as e:
            self.logger.error(f"Error loading API tools: {e}")
            return []
    
    def get_tools_as_openai_functions(self) -> List[Dict[str, Any]]:
        """Convert API tools to OpenAI function calling format"""
        tools = self.get_available_tools()
        functions = []
        
        for tool in tools:
            function_spec = tool.get_openai_function_spec()
            functions.append({
                "type": "function",
                "function": function_spec
            })
        
        return functions
    
    def should_use_tools(self, question: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str]]:
        """
        Use AI to determine if tools should be used and which one
        Returns: (should_use_tools, tool_name, tool_arguments, clarification_question)
        """
        try:
            tools = self.get_tools_as_openai_functions()
            
            if not tools:
                return False, None, None, None
            
            # First, check if the question is ambiguous and needs clarification
            clarification_check = self.check_for_clarification_needed(question, tools)
            if clarification_check:
                return False, None, None, clarification_check
            
            # Build conversation context with strict system prompt
            messages = [
                {
                    "role": "system",
                    "content": """You are a conservative AI assistant that only uses API tools when you are ABSOLUTELY CERTAIN they are needed.

CRITICAL RULES:
1. Only use API tools when the user's question DIRECTLY and SPECIFICALLY requests information that can ONLY be obtained from the API
2. If the question is vague, general, or could be answered with general knowledge, DO NOT use any tools
3. If you're unsure whether to use a tool, DON'T use it - default to general knowledge
4. Look for EXACT matches between the user's request and the tool's purpose
5. Pay attention to context - similar words don't mean the same thing (e.g., "credit limit" vs "buy credits")

Examples of when NOT to use tools:
- "Can you share your plan to buy credits" (asking about purchasing plans, not checking current balance)
- "How do I get more credits" (asking for instructions, not current status)
- "What are the credit options" (asking about available plans, not personal data)

Examples of when TO use tools:
- "What is my current credit limit" (directly asking for personal account data)
- "Show me my account balance" (directly requesting personal information)
- "What are my current credits" (directly asking for personal data)

Be extremely conservative. When in doubt, do NOT use tools."""
                }
            ]
            
            if conversation_history:
                messages.extend(conversation_history[-5:])  # Last 5 messages for context
            
            messages.append({
                "role": "user",
                "content": question
            })
            
            # Call OpenAI with function calling
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=messages,
                tools=tools,
                tool_choice="auto"  # Let AI decide whether to use tools
            )
            
            message = response.choices[0].message
            
            # Check if AI decided to use a tool
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                self.logger.info(f"AI selected tool: {function_name} with args: {function_args}")
                return True, function_name, function_args, None
            
            return False, None, None, None
            
        except Exception as e:
            self.logger.error(f"Error in AI tool selection: {e}")
            return False, None, None, None
    
    def check_for_clarification_needed(self, question: str, tools: List[Dict]) -> Optional[str]:
        """
        Check if the question is ambiguous and needs clarification
        Returns clarification question if needed, None otherwise
        """
        try:
            # Only check for clarification if we have multiple tools and the question is very short/generic
            if len(tools) < 2:
                return None
            
            # Pre-filter: Only check for clarification if the question is potentially ambiguous
            # Look for single words or very generic terms that could match multiple tools
            question_lower = question.lower().strip()
            
            # Common ambiguous keywords that might need clarification
            ambiguous_keywords = [
                'credits', 'credit', 'account', 'balance', 'status', 'info', 'information',
                'details', 'data', 'token', 'tokens', 'user', 'profile', 'settings'
            ]
            
            # Skip clarification if the question is long or contains action words
            if len(question.split()) > 5 or any(word in question_lower for word in [
                'how', 'what', 'where', 'when', 'why', 'can', 'could', 'should', 'would',
                'help', 'show', 'get', 'find', 'search', 'post', 'create', 'update', 'delete'
            ]):
                return None
            
            # Only proceed if the question contains ambiguous keywords
            if not any(keyword in question_lower for keyword in ambiguous_keywords):
                return None
                
            # Extract tool names and descriptions for context
            tool_context = []
            for tool in tools:
                func_spec = tool.get('function', {})
                tool_context.append({
                    'name': func_spec.get('name', ''),
                    'description': func_spec.get('description', '')
                })
            
            # Use AI to detect ambiguity - be more conservative
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a conservative assistant that only asks for clarification when a question is EXTREMELY ambiguous and could match multiple available tools.

Available tools and their purposes:
{json.dumps(tool_context, indent=2)}

ONLY ask for clarification if:
1. The question is a single generic word that could match multiple tools
2. The question is so vague it's impossible to determine intent
3. There are multiple tools that could handle the exact same keyword

DO NOT ask for clarification if:
1. The question contains context or action words
2. The question is a complete sentence
3. The question has clear intent even if it's not perfectly specific
4. The question doesn't match any tool closely

If clarification is absolutely needed, respond with:
CLARIFICATION_NEEDED: [Your clarifying question here]

If the question is clear enough to proceed, respond with:
CLEAR

Examples of when TO ask clarification:
- "credits" (single word, could mean balance OR purchase)
- "account" (single word, could mean details OR balance)

Examples of when NOT to ask clarification:
- "how can I post my job" (clear intent and context)
- "what is my balance" (clear intent)
- "help me with account settings" (clear context)
- "show me my status" (clear action)

Be extremely conservative - only ask when truly necessary."""
                },
                {
                    "role": "user", 
                    "content": f"User question: {question}"
                }
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=150,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            if result.startswith("CLARIFICATION_NEEDED:"):
                clarification = result.replace("CLARIFICATION_NEEDED:", "").strip()
                self.logger.info(f"Clarification needed for question: '{question}' -> '{clarification}'")
                return clarification
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking for clarification: {e}")
            return None
    
    def execute_tool(self, tool_name: str, tool_arguments: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """Execute the selected tool with given arguments"""
        try:
            # Get tool from database
            tool = ApiTool.query.filter_by(name=tool_name, active=True).first()
            if not tool:
                return {
                    'success': False,
                    'error': f'Tool {tool_name} not found or inactive'
                }
            
            # Process curl command with arguments
            processed_command = self._process_curl_command(tool.curl_command, tool_arguments, original_question)
            
            # Execute the curl command
            result = subprocess.run(
                processed_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Try to parse JSON response
                try:
                    response_data = json.loads(result.stdout)
                    
                    # Apply response mapping if configured
                    mapped_response = self._apply_response_mapping(response_data, tool.get_response_mapping())
                    
                    return {
                        'success': True,
                        'data': mapped_response,
                        'raw_data': response_data,
                        'tool_name': tool_name,
                        'response_template': tool.response_template
                    }
                except json.JSONDecodeError:
                    return {
                        'success': True,
                        'data': result.stdout,
                        'raw_data': result.stdout,
                        'tool_name': tool_name,
                        'response_template': tool.response_template
                    }
            else:
                return {
                    'success': False,
                    'error': f'Command failed: {result.stderr}',
                    'tool_name': tool_name
                }
                
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'error': f'Tool execution failed: {str(e)}',
                'tool_name': tool_name
            }
    
    def _process_curl_command(self, curl_command: str, arguments: Dict[str, Any], original_question: str) -> str:
        """Process curl command by replacing placeholders with actual values"""
        processed_command = curl_command
        
        # Replace function arguments
        for key, value in arguments.items():
            placeholder = f"{{{key}}}"
            processed_command = processed_command.replace(placeholder, str(value))
        
        # Replace special placeholders
        processed_command = processed_command.replace("{question}", original_question)
        processed_command = processed_command.replace("{user_query}", original_question)
        
        return processed_command
    
    def _apply_response_mapping(self, response_data: Any, mapping_config: Dict[str, Any]) -> Any:
        """Apply response mapping configuration to extract specific fields"""
        if not mapping_config:
            return response_data
        
        try:
            if isinstance(response_data, dict):
                mapped_response = {}
                
                # Apply field mappings
                if 'fields' in mapping_config:
                    for new_field, old_field in mapping_config['fields'].items():
                        if old_field in response_data:
                            mapped_response[new_field] = response_data[old_field]
                
                # Apply transformations
                if 'transformations' in mapping_config:
                    for field, transform in mapping_config['transformations'].items():
                        if field in mapped_response:
                            if transform == 'uppercase':
                                mapped_response[field] = str(mapped_response[field]).upper()
                            elif transform == 'lowercase':
                                mapped_response[field] = str(mapped_response[field]).lower()
                            elif transform == 'truncate':
                                mapped_response[field] = str(mapped_response[field])[:100]
                
                return mapped_response if mapped_response else response_data
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Error applying response mapping: {e}")
            return response_data
    
    def format_tool_response(self, tool_result: Dict[str, Any], original_question: str) -> str:
        """Format tool response using response template with field replacement"""
        try:
            if not tool_result.get('success'):
                return f"I encountered an error: {tool_result.get('error', 'Unknown error')}"
            
            response_template = tool_result.get('response_template', '')
            tool_data = tool_result.get('data', {})
            
            # If no template, provide a simple default format
            if not response_template:
                if isinstance(tool_data, dict):
                    formatted_data = []
                    for key, value in tool_data.items():
                        formatted_data.append(f"**{key.upper()}**: {value}")
                    return "Based on the API response:\n\n" + "\n".join(formatted_data)
                else:
                    return f"API Response: {tool_data}"
            
            # Use template with field replacement
            formatted_response = response_template
            
            # Replace placeholders in template with actual data
            if isinstance(tool_data, dict):
                for key, value in tool_data.items():
                    placeholder = f"{{{key}}}"
                    formatted_response = formatted_response.replace(placeholder, str(value))
            
            # Replace question placeholder if present
            formatted_response = formatted_response.replace("{question}", original_question)
            formatted_response = formatted_response.replace("{user_query}", original_question)
            
            return formatted_response
            
        except Exception as e:
            self.logger.error(f"Error formatting tool response: {e}")
            return f"I found some information but had trouble formatting it: {tool_result.get('data', 'No data available')}"
    
    def process_question_with_tools(self, question: str, conversation_history: List[Dict] = None) -> Tuple[bool, str]:
        """
        Main method to process a question with AI tool selection
        Returns: (used_tools, formatted_response)
        """
        # Check if AI wants to use tools
        should_use, tool_name, tool_args, clarification = self.should_use_tools(question, conversation_history)
        
        # If clarification is needed, return it immediately
        if clarification:
            return True, clarification
        
        if should_use and tool_name and tool_args is not None:
            # Execute the selected tool
            tool_result = self.execute_tool(tool_name, tool_args, question)
            
            # Format the response
            formatted_response = self.format_tool_response(tool_result, question)
            
            return True, formatted_response
        
        return False, ""