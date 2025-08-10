"""
Contract Validator - Validates generated code against interface contracts
========================================================================
This module ensures that generated code properly implements the required
interfaces from shared/contracts.py
"""

import ast
import re
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validates that generated code implements required interfaces correctly"""
    
    def __init__(self, contracts_path: str = "generated_surf_lamp_app/shared/contracts.py"):
        self.contracts_path = contracts_path
        self.interfaces = self._load_interfaces()
        
    def _load_interfaces(self) -> Dict[str, Dict[str, List[str]]]:
        """Load and parse interface definitions from contracts"""
        interfaces = {}
        
        try:
            with open(self.contracts_path, 'r') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's an interface (inherits from ABC or has abstractmethods)
                    if any(base.id == 'ABC' for base in node.bases if isinstance(base, ast.Name)):
                        interface_name = node.name
                        methods = []
                        
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                # Skip __init__ and private methods
                                if not item.name.startswith('_'):
                                    # Get method signature
                                    params = []
                                    for arg in item.args.args[1:]:  # Skip 'self'
                                        params.append(arg.arg)
                                    methods.append({
                                        'name': item.name,
                                        'params': params,
                                        'is_async': isinstance(item, ast.AsyncFunctionDef)
                                    })
                        
                        interfaces[interface_name] = methods
                        
        except Exception as e:
            logger.error(f"Failed to load interfaces: {e}")
            
        return interfaces
    
    def validate_implementation(self, code: str, required_interface: str) -> Tuple[bool, List[str]]:
        """
        Validate that code implements a specific interface
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if required_interface not in self.interfaces:
            return True, []  # Interface not found, skip validation
        
        required_methods = self.interfaces[required_interface]
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error in generated code: {e}")
            return False, errors
        
        # Find all class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class claims to implement the interface
                implements_interface = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == required_interface:
                        implements_interface = True
                        break
                
                if implements_interface:
                    # Get all methods in the class
                    class_methods = {}
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith('_'):
                                params = [arg.arg for arg in item.args.args[1:]]  # Skip 'self'
                                class_methods[item.name] = {
                                    'params': params,
                                    'is_async': isinstance(item, ast.AsyncFunctionDef)
                                }
                    
                    # Check if all required methods are implemented
                    for req_method in required_methods:
                        method_name = req_method['name']
                        if method_name not in class_methods:
                            errors.append(f"Missing required method: {method_name}")
                        else:
                            # Check if async matches
                            if req_method['is_async'] != class_methods[method_name]['is_async']:
                                async_str = "async " if req_method['is_async'] else ""
                                errors.append(f"Method {method_name} should be {async_str}def")
                            
                            # Check parameters (basic check)
                            if len(req_method['params']) != len(class_methods[method_name]['params']):
                                errors.append(f"Method {method_name} has wrong number of parameters")
        
        return len(errors) == 0, errors
    
    def extract_pure_code(self, llm_response: str) -> str:
        """
        Extract only executable Python code from LLM response
        Removes markdown, explanations, and other non-code text
        """
        # First, try to extract from markdown code blocks
        code_block_pattern = r'```(?:python)?\n(.*?)```'
        matches = re.findall(code_block_pattern, llm_response, re.DOTALL)
        
        if matches:
            # Return the longest code block (likely the main implementation)
            return max(matches, key=len).strip()
        
        # If no markdown blocks, try to identify where code starts
        lines = llm_response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Detect code start patterns
            if not in_code:
                if any(pattern in line for pattern in [
                    'import ', 'from ', 'class ', 'def ', 'async def ',
                    '"""', "'''", '#!'
                ]):
                    in_code = True
                    code_lines.append(line)
            else:
                # Stop at obvious non-code patterns
                if line.strip() and not line.startswith((' ', '\t')) and \
                   not any(pattern in line for pattern in [
                       '=', '(', ')', '{', '}', '[', ']', ':', '#', '"', "'"
                   ]) and \
                   len(line) > 50 and line[0].isupper():
                    # Likely explanation text, stop here
                    break
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        # Last resort: return as-is and hope it's valid Python
        return llm_response.strip()
    
    def validate_arduino_response(self, code: str) -> Tuple[bool, List[str]]:
        """
        Special validation for Arduino response format
        Ensures the code returns the exact JSON structure Arduino expects
        """
        errors = []
        
        # Check if ArduinoResponse is used correctly
        arduino_response_pattern = r'ArduinoResponse\(\)'
        if arduino_response_pattern not in code:
            errors.append("Code must create ArduinoResponse() instances")
        
        # Check for required fields in response
        required_fields = [
            '"registered"', '"brightness"', '"location_used"',
            '"wave_height_m"', '"wave_period_s"', '"wind_speed_mps"',
            '"wind_deg"', '"error"'
        ]
        
        for field in required_fields:
            if field not in code:
                errors.append(f"Missing required Arduino response field: {field}")
        
        return len(errors) == 0, errors
    
    def get_required_interfaces(self, file_path: str) -> List[str]:
        """
        Determine which interfaces a file should implement based on its path
        """
        interfaces = []
        
        if 'lamp_repository.py' in file_path:
            interfaces.append('ILampRepository')
        elif 'user_repository.py' in file_path:
            interfaces.append('IUserRepository')
        elif 'activity_logger.py' in file_path:
            interfaces.append('IActivityLogger')
        elif 'cache_manager.py' in file_path:
            interfaces.append('ICacheManager')
        elif 'lamp_control_service.py' in file_path:
            interfaces.append('ILampControlService')
        elif 'background_scheduler.py' in file_path:
            interfaces.append('IBackgroundScheduler')
        elif 'surf_data_provider.py' in file_path:
            interfaces.append('ISurfDataProvider')
        elif 'password_security.py' in file_path:
            interfaces.append('IPasswordSecurity')
        elif 'input_validator.py' in file_path:
            interfaces.append('IInputValidator')
        
        return interfaces
    
    def generate_interface_stub(self, interface_name: str) -> str:
        """
        Generate a stub implementation for an interface as fallback
        """
        if interface_name not in self.interfaces:
            return ""
        
        methods = self.interfaces[interface_name]
        
        stub = f"""from shared.contracts import {interface_name}
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class Concrete{interface_name[1:]}({interface_name}):
    \"\"\"Concrete implementation of {interface_name}\"\"\"
    
    def __init__(self):
        # Initialize as needed
        pass
"""
        
        for method in methods:
            async_str = "async " if method['is_async'] else ""
            params_str = ", ".join(["self"] + [f"{p}: Any" for p in method['params']])
            
            stub += f"""
    {async_str}def {method['name']}({params_str}):
        \"\"\"Implementation of {method['name']}\"\"\"
        # TODO: Implement this method
        raise NotImplementedError("Method {method['name']} not yet implemented")
"""
        
        return stub
