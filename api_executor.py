import subprocess
import json
import shlex
import logging
import re
from typing import Dict, List, Optional, Any

class ApiExecutor:
    """Handles API rule matching and execution"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_matching_rule(self, question: str, api_rules: List[Any]) -> Optional[Any]:
        """Find the best matching API rule for a question"""
        question_lower = question.lower()
        
        # Sort rules by priority (higher priority first)
        sorted_rules = sorted(api_rules, key=lambda x: x.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.active:
                continue
                
            keywords = rule.get_keywords_list()
            
            # Check if any keyword matches
            for keyword in keywords:
                if keyword in question_lower:
                    self.logger.info(f"Found matching rule '{rule.name}' for keyword '{keyword}'")
                    return rule
        
        return None
    
    def execute_curl_command(self, curl_command: str, question: str = "") -> Dict[str, Any]:
        """Execute a curl command and return the result"""
        try:
            # Replace placeholder variables if any
            processed_command = self._process_curl_command(curl_command, question)
            
            # Parse the curl command safely
            if not processed_command.strip().startswith('curl'):
                return {
                    'success': False,
                    'error': 'Invalid command: Only curl commands are allowed'
                }
            
            # Execute the command
            result = subprocess.run(
                processed_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0:
                # Try to parse JSON response
                try:
                    response_data = json.loads(result.stdout)
                    return {
                        'success': True,
                        'data': response_data,
                        'raw_output': result.stdout
                    }
                except json.JSONDecodeError:
                    # Return raw text if not JSON
                    return {
                        'success': True,
                        'data': result.stdout,
                        'raw_output': result.stdout
                    }
            else:
                return {
                    'success': False,
                    'error': f'Command failed with exit code {result.returncode}',
                    'stderr': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out after 30 seconds'
            }
        except Exception as e:
            self.logger.error(f"Error executing curl command: {str(e)}")
            return {
                'success': False,
                'error': f'Execution error: {str(e)}'
            }
    
    def _process_curl_command(self, curl_command: str, question: str) -> str:
        """Process curl command to replace placeholders"""
        # Replace common placeholders
        processed = curl_command
        
        # Replace {question} placeholder with actual question
        processed = processed.replace('{question}', shlex.quote(question))
        processed = processed.replace('{QUESTION}', shlex.quote(question))
        
        # You can add more placeholder replacements here
        # For example:
        # processed = processed.replace('{user_id}', str(user_id))
        
        return processed
    
    def format_api_response(self, response_data: Dict[str, Any], rule_name: str) -> str:
        """Format API response for display in chat"""
        if not response_data['success']:
            return f"❌ API Error ({rule_name}): {response_data['error']}"
        
        # Try to format the response nicely
        try:
            if isinstance(response_data['data'], dict):
                # Format JSON response
                formatted = json.dumps(response_data['data'], indent=2)
                return f"🔗 **API Response** ({rule_name}):\n```json\n{formatted}\n```"
            elif isinstance(response_data['data'], str):
                # Format string response
                return f"🔗 **API Response** ({rule_name}):\n{response_data['data']}"
            else:
                # Fallback formatting
                return f"🔗 **API Response** ({rule_name}):\n{str(response_data['data'])}"
        except Exception as e:
            self.logger.error(f"Error formatting API response: {str(e)}")
            return f"🔗 **API Response** ({rule_name}):\n{response_data['raw_output']}"