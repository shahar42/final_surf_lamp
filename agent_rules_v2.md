#!/usr/bin/env python3
"""
Interface Contract Generator and Validator
==========================================

Utilities for working with the immutable interface contracts system.
Validates generated code follows contracts and provides debugging tools.

Author: Multi-Agent Architecture Team
Version: 2.0+
"""

import os
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import argparse
import json


class ContractAnalyzer:
    """Analyzes and validates interface contracts"""
    
    def __init__(self, contracts_path: str = "shared/contracts.py"):
        self.contracts_path = contracts_path
        self.interfaces = {}
        self.error_types = {}
        self.data_types = {}
        
    def load_contracts(self) -> bool:
        """Load and parse interface contracts"""
        
        if not os.path.exists(self.contracts_path):
            print(f"❌ Contracts file not found: {self.contracts_path}")
            return False
        
        try:
            # Parse the contracts file as AST
            with open(self.contracts_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name.startswith('I') and len(node.name) > 1:
                        # This is an interface
                        self.interfaces[node.name] = self._extract_interface_methods(node)
                    elif 'Error' in node.name:
                        # This is an error type
                        self.error_types[node.name] = True
                    elif node.name in ['ArduinoResponse', 'SurfData', 'LampConfig']:
                        # This is a data type
                        self.data_types[node.name] = True
            
            print(f"✅ Loaded {len(self.interfaces)} interfaces, {len(self.error_types)} error types")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing contracts: {e}")
            return False
    
    def _extract_interface_methods(self, class_node: ast.ClassDef) -> Dict[str, Dict[str, Any]]:
        """Extract method signatures from interface class"""
        
        methods = {}
        
        for node in class_node.body:
            if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):  # Skip private methods
                    methods[node.name] = {
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'args': [arg.arg for arg in node.args.args if arg.arg != 'self'],
                        'returns': ast.unparse(node.returns) if node.returns else None,
                        'decorators': [ast.unparse(dec) for dec in node.decorator_list]
                    }
        
        return methods
    
    def get_interface_summary(self) -> str:
        """Generate human-readable interface summary"""
        
        summary = "📋 INTERFACE CONTRACT SUMMARY\n"
        summary += "=" * 50 + "\n\n"
        
        for interface_name, methods in self.interfaces.items():
            summary += f"🔌 {interface_name}\n"
            summary += "-" * len(interface_name) + "\n"
            
            for method_name, details in methods.items():
                async_prefix = "async " if details['is_async'] else ""
                args_str = ", ".join(details['args'])
                returns_str = f" -> {details['returns']}" if details['returns'] else ""
                
                summary += f"  {async_prefix}def {method_name}({args_str}){returns_str}\n"
            
            summary += "\n"
        
        summary += f"🚨 Error Types: {', '.join(self.error_types.keys())}\n"
        summary += f"📦 Data Types: {', '.join(self.data_types.keys())}\n"
        
        return summary


class CodeValidator:
    """Validates generated code against contracts"""
    
    def __init__(self, contracts_analyzer: ContractAnalyzer):
        self.analyzer = contracts_analyzer
        self.violations = []
    
    def validate_directory(self, directory: str) -> bool:
        """Validate all Python files in directory against contracts"""
        
        print(f"🔍 Validating code in: {directory}")
        self.violations = []
        
        if not os.path.exists(directory):
            print(f"❌ Directory not found: {directory}")
            return False
        
        python_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    python_files.append(os.path.join(root, file))
        
        print(f"   Found {len(python_files)} Python files to validate")
        
        all_valid = True
        for file_path in python_files:
            if not self._validate_file(file_path):
                all_valid = False
        
        self._print_validation_report()
        return all_valid
    
    def _validate_file(self, file_path: str) -> bool:
        """Validate single Python file"""
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Check for contract imports
            has_contract_import = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and 'shared.contracts' in node.module:
                        has_contract_import = True
                        break
            
            # Find class definitions that might implement interfaces
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._validate_class_implements_interface(node, file_path, has_contract_import)
            
            return True
            
        except Exception as e:
            self.violations.append({
                'file': file_path,
                'type': 'parse_error',
                'message': f"Failed to parse file: {e}"
            })
            return False
    
    def _validate_class_implements_interface(self, class_node: ast.ClassDef, file_path: str, has_contract_import: bool):
        """Check if class properly implements an interface"""
        
        # Check if class inherits from an interface
        interface_bases = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                if base.id in self.analyzer.interfaces:
                    interface_bases.append(base.id)
        
        if not interface_bases:
            return  # Not implementing an interface
        
        if not has_contract_import:
            self.violations.append({
                'file': file_path,
                'type': 'missing_import',
                'message': f"Class {class_node.name} implements interface but missing 'from shared.contracts import'"
            })
        
        # Validate each interface implementation
        for interface_name in interface_bases:
            self._validate_interface_implementation(class_node, interface_name, file_path)
    
    def _validate_interface_implementation(self, class_node: ast.ClassDef, interface_name: str, file_path: str):
        """Validate that class properly implements interface methods"""
        
        interface_methods = self.analyzer.interfaces.get(interface_name, {})
        implemented_methods = {}
        
        # Extract implemented methods
        for node in class_node.body:
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                if not node.name.startswith('_'):  # Skip private methods
                    implemented_methods[node.name] = {
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'args': [arg.arg for arg in node.args.args if arg.arg != 'self']
                    }
        
        # Check for missing methods
        for method_name, method_details in interface_methods.items():
            if method_name not in implemented_methods:
                self.violations.append({
                    'file': file_path,
                    'type': 'missing_method',
                    'message': f"Class {class_node.name} missing required method: {method_name}"
                })
                continue
            
            # Check method signature
            impl_method = implemented_methods[method_name]
            
            if method_details['is_async'] != impl_method['is_async']:
                async_expected = "async " if method_details['is_async'] else "sync "
                async_actual = "async " if impl_method['is_async'] else "sync "
                self.violations.append({
                    'file': file_path,
                    'type': 'wrong_signature',
                    'message': f"Method {class_node.name}.{method_name} should be {async_expected}but is {async_actual}"
                })
            
            if method_details['args'] != impl_method['args']:
                self.violations.append({
                    'file': file_path,
                    'type': 'wrong_signature', 
                    'message': f"Method {class_node.name}.{method_name} has wrong arguments. Expected: {method_details['args']}, Got: {impl_method['args']}"
                })
    
    def _print_validation_report(self):
        """Print validation results"""
        
        if not self.violations:
            print("✅ All code validates against contracts!")
            return
        
        print(f"\n❌ Found {len(self.violations)} contract violations:")
        print("-" * 50)
        
        by_type = {}
        for violation in self.violations:
            v_type = violation['type']
            if v_type not in by_type:
                by_type[v_type] = []
            by_type[v_type].append(violation)
        
        for v_type, violations in by_type.items():
            print(f"\n🚨 {v_type.upper()} ({len(violations)} issues):")
            for violation in violations:
                print(f"   📁 {violation['file']}")
                print(f"      {violation['message']}")


class ArduinoValidator:
    """Specialized validator for Arduino response format"""
    
    def validate_response_format(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Arduino response format"""
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        required_keys = {
            "registered", "brightness", "location_used",
            "wave_height_m", "wave_period_s", "wind_speed_mps",
            "wind_deg", "error"
        }
        
        # Check required keys
        missing_keys = required_keys - set(response_data.keys())
        if missing_keys:
            results['valid'] = False
            results['errors'].append(f"Missing required keys: {missing_keys}")
        
        extra_keys = set(response_data.keys()) - required_keys
        if extra_keys:
            results['warnings'].append(f"Extra keys (Arduino will ignore): {extra_keys}")
        
        # Type validation
        type_checks = [
            ('registered', bool),
            ('brightness', int),
            ('location_used', str),
            ('error', (str, type(None)))
        ]
        
        for key, expected_type in type_checks:
            if key in response_data:
                if not isinstance(response_data[key], expected_type):
                    results['valid'] = False
                    results['errors'].append(f"Key '{key}' should be {expected_type}, got {type(response_data[key])}")
        
        # Numeric fields can be None or float/int
        numeric_fields = ['wave_height_m', 'wave_period_s', 'wind_speed_mps']
        for field in numeric_fields:
            if field in response_data and response_data[field] is not None:
                if not isinstance(response_data[field], (int, float)):
                    results['valid'] = False
                    results['errors'].append(f"Field '{field}' should be numeric or None, got {type(response_data[field])}")
        
        # wind_deg should be int or None
        if 'wind_deg' in response_data and response_data['wind_deg'] is not None:
            if not isinstance(response_data['wind_deg'], int):
                results['valid'] = False
                results['errors'].append(f"Field 'wind_deg' should be int or None, got {type(response_data['wind_deg'])}")
        
        return results


def main():
    """Command-line interface for contract validation"""
    
    parser = argparse.ArgumentParser(description="Interface Contract Validation Tool")
    parser.add_argument('--validate', '-v', metavar='DIR', 
                       help='Validate code in directory against contracts')
    parser.add_argument('--summary', '-s', action='store_true',
                       help='Show interface summary')
    parser.add_argument('--arduino-test', '-a', action='store_true',
                       help='Test Arduino response format validation')
    parser.add_argument('--contracts', '-c', default='shared/contracts.py',
                       help='Path to contracts file')
    
    args = parser.parse_args()
    
    if not any([args.validate, args.summary, args.arduino_test]):
        parser.print_help()
        return
    
    # Load contracts
    analyzer = ContractAnalyzer(args.contracts)
    if not analyzer.load_contracts():
        sys.exit(1)
    
    if args.summary:
        print(analyzer.get_interface_summary())
    
    if args.validate:
        validator = CodeValidator(analyzer)
        is_valid = validator.validate_directory(args.validate)
        sys.exit(0 if is_valid else 1)
    
    if args.arduino_test:
        arduino_validator = ArduinoValidator()
        
        # Test valid response
        valid_response = {
            "registered": True,
            "brightness": 100,
            "location_used": "San Diego", 
            "wave_height_m": 1.5,
            "wave_period_s": 8.0,
            "wind_speed_mps": 12.0,
            "wind_deg": 45,
            "error": None
        }
        
        print("🧪 Testing valid Arduino response:")
        results = arduino_validator.validate_response_format(valid_response)
        if results['valid']:
            print("✅ Valid Arduino response format")
        else:
            print("❌ Invalid Arduino response:")
            for error in results['errors']:
                print(f"   {error}")
        
        # Test invalid response
        invalid_response = {
            "status": "ok",  # Wrong key
            "brightness": "100",  # Wrong type
            "location_used": "San Diego"
            # Missing required keys
        }
        
        print("\n🧪 Testing invalid Arduino response:")
        results = arduino_validator.validate_response_format(invalid_response)
        if not results['valid']:
            print("✅ Correctly identified invalid response:")
            for error in results['errors']:
                print(f"   ❌ {error}")
        else:
            print("❌ Failed to catch invalid response!")


if __name__ == "__main__":
    main()
