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
    
    def should_use_tools(self, question: str, conversation_history: List[Dict] = None) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Use AI to determine if tools should be used and which one
        Returns: (should_use_tools, tool_name, tool_arguments)
        """
        try:
            tools = self.get_tools_as_openai_functions()
            
            if not tools:
                return False, None, None
            
            # Build conversation context
            messages = []
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
                return True, function_name, function_args
            
            return False, None, None
            
        except Exception as e:
            self.logger.error(f"Error in AI tool selection: {e}")
            return False, None, None
    
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
        """Format tool response using AI and response template"""
        try:
            if not tool_result.get('success'):
                return f"I encountered an error: {tool_result.get('error', 'Unknown error')}"
            
            response_template = tool_result.get('response_template', '')
            tool_data = tool_result.get('data', {})
            
            # If no template, use AI to format the response
            if not response_template:
                response_template = "Please format this API response data in a clear, user-friendly way for the user's question: {question}"
            
            # Use AI to format the response
            format_prompt = f"""
            Original question: {original_question}
            
            API response data: {json.dumps(tool_data, indent=2)}
            
            Response template: {response_template}
            
            Please format this information in a clear, helpful way for the user. Focus on answering their specific question using the API data.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that formats API responses for users in a clear, concise way."
                    },
                    {
                        "role": "user",
                        "content": format_prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error formatting tool response: {e}")
            return f"I found some information but had trouble formatting it: {tool_result.get('data', 'No data available')}"
    
    def process_question_with_tools(self, question: str, conversation_history: List[Dict] = None) -> Tuple[bool, str]:
        """
        Main method to process a question with AI tool selection
        Returns: (used_tools, formatted_response)
        """
        # Check if AI wants to use tools
        should_use, tool_name, tool_args = self.should_use_tools(question, conversation_history)
        
        if should_use and tool_name and tool_args is not None:
            # Execute the selected tool
            tool_result = self.execute_tool(tool_name, tool_args, question)
            
            # Format the response
            formatted_response = self.format_tool_response(tool_result, question)
            
            return True, formatted_response
        
        return False, ""