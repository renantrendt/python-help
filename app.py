import os
import ast
import json
import tempfile
import subprocess
from flask import Flask, render_template, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize Anthropic client
# Note: You'll need to set the ANTHROPIC_API_KEY environment variable
anthropicClient = None
try:
    anthropicClient = Anthropic()
except Exception as e:
    print(f"Failed to initialize Anthropic client: {str(e)}")
    print("AI explanations will not be available.")

class PythonHabitAnalyzer:
    """Analyzes Python code for actual runtime issues and bugs with context awareness."""
    
    # Constants for issue categories
    SYNTAX_ERROR = 'syntax_error'       # Syntax errors that prevent code from running
    RUNTIME_ERROR = 'runtime_error'     # Errors that occur during execution
    FATAL_ERROR = 'fatal_error'         # Errors that will definitely crash the program
    BAD_HABIT = 'bad_habit'             # Not an error but a bad practice
    POTENTIAL_ERROR = 'potential_error' # Could become an error in certain conditions
    
    def __init__(self):
        self.feedback = []
        self.context = {}
        # Track variables, functions, and control flow for context analysis
        self.variables = {}
        self.functions = {}
        self.control_flow = []
    
    def analyze(self, code):
        """Run all analysis methods on the provided code with context awareness."""
        self.feedback = []
        self.context = {}
        self.variables = {}
        self.functions = {}
        self.control_flow = []
        
        # First pass: build context (variables, functions, control flow)
        try:
            tree = ast.parse(code)
            self._build_context(tree)
        except SyntaxError:
            # If syntax error, we'll catch it in the analysis phase
            pass
        
        # Second pass: run analysis with context awareness
        self._run_ast_analysis(code)
        
        # Run pylint analysis but filter for only serious issues
        self._run_pylint_analysis(code)
        
        return self.feedback
        
    def _build_context(self, tree):
        """Build context by analyzing the code structure first."""
        # Collect all variable assignments
        for node in ast.walk(tree):
            # Track variable assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        # Track if the variable is reassigned
                        self.variables[var_name] = self.variables.get(var_name, 0) + 1
            
            # Track function definitions and their usage
            elif isinstance(node, ast.FunctionDef):
                func_name = node.name
                self.functions[func_name] = {
                    'node': node,
                    'calls': 0,
                    'has_return': False,
                    'has_break': False,
                    'has_mutable_defaults': False,
                    'exception_handlers': []
                }
                
                # Check for returns in the function
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Return):
                        self.functions[func_name]['has_return'] = True
                    elif isinstance(subnode, ast.Break):
                        self.functions[func_name]['has_break'] = True
                    elif isinstance(subnode, ast.ExceptHandler):
                        self.functions[func_name]['exception_handlers'].append(subnode)
                
                # Check for mutable defaults
                for arg in node.args.defaults:
                    if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                        self.functions[func_name]['has_mutable_defaults'] = True
            
            # Track function calls
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.functions:
                    self.functions[func_name]['calls'] += 1
            
            # Track loops and conditionals for control flow analysis
            elif isinstance(node, (ast.For, ast.While, ast.If)):
                self.control_flow.append(node)
    
    def _run_pylint_analysis(self, code):
        """Run pylint on the code and extract only critical messages with uncertainty levels."""
        try:
            # Create a temporary file to store the code
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(code.encode('utf-8'))
            
            # Run pylint on the temporary file
            cmd = ['pylint', '--output-format=json', temp_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Process pylint output
            if result.stdout:
                try:
                    pylint_results = json.loads(result.stdout)
                    for msg in pylint_results:
                        message_type = msg.get('type', '').lower()
                        message = msg.get('message', '')
                        line = msg.get('line', 0)
                        symbol = msg.get('symbol', '')
                        
                        # Categorize issues by certainty
                        definite_error_symbols = [
                            'undefined-variable', 'used-before-assignment',
                            'no-member', 'not-callable', 'unexpected-keyword-arg',
                            'too-many-function-args', 'too-few-function-args',
                            'invalid-sequence-index', 'invalid-slice-index',
                            'attribute-error', 'import-error', 'no-name-in-module',
                            'return-outside-function', 'yield-outside-function',
                            'continue-outside-loop', 'break-outside-loop'
                        ]
                        
                        potential_error_symbols = [
                            'missing-kwoa', 'unsupported-assignment-operation', 
                            'unsupported-delete-operation', 'unsupported-membership-test', 
                            'unsubscriptable-object', 'undefined-loop-variable',
                            'return-arg-in-generator', 'nonlocal-without-binding'
                        ]
                        
                        # Determine certainty level based on context
                        # Determine category based on message type and symbol
                        if message_type == 'error' or symbol in definite_error_symbols:
                            category = self.RUNTIME_ERROR
                        elif symbol in potential_error_symbols:
                            # Check context to see if this might be intentional
                            # For example, if a variable is used in multiple places, it's less likely to be a typo
                            if symbol == 'undefined-variable':
                                var_name = message.split("'")
                                if len(var_name) > 1 and var_name[1] in self.variables:
                                    category = self.POTENTIAL_ERROR
                                else:
                                    category = self.RUNTIME_ERROR
                            else:
                                category = self.POTENTIAL_ERROR
                        else:
                            category = self.BAD_HABIT
                        
                        if message_type == 'error' or symbol in definite_error_symbols or symbol in potential_error_symbols:
                            self.feedback.append({
                                'line': line,
                                'message': message,
                                'is_bad_habit': True,
                                'category': category,
                                'source': 'pylint'
                            })
                except json.JSONDecodeError:
                    self.feedback.append({
                        'line': 0,
                        'message': 'Failed to parse pylint output',
                        'is_bad_habit': False,
                        'category': self.RUNTIME_ERROR,
                        'source': 'system'
                    })
        except Exception as e:
            self.feedback.append({
                'line': 0,
                'message': f'Error running pylint: {str(e)}',
                'is_bad_habit': False,
                'category': self.RUNTIME_ERROR,
                'source': 'system'
            })
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def _run_ast_analysis(self, code):
        """Analyze code using Python's AST module for critical runtime issues with context awareness."""
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Run various custom checks for actual runtime issues with context awareness
            self._check_mutable_defaults(tree)
            self._check_infinite_loops(tree)
            self._check_exception_handling(tree)
            self._check_resource_management(tree)
            self._check_unreachable_code(tree)
            self._check_shadowing_builtins(tree)
            
        except SyntaxError as e:
            self.feedback.append({
                'line': e.lineno if hasattr(e, 'lineno') else 0,
                'message': f'Syntax error: {str(e)}',
                'is_bad_habit': True,
                'category': self.SYNTAX_ERROR,
                'source': 'ast'
            })
        except Exception as e:
            self.feedback.append({
                'line': 0,
                'message': f'Error during AST analysis: {str(e)}',
                'is_bad_habit': False,
                'category': self.RUNTIME_ERROR,
                'source': 'system'
            })
    
    def _check_mutable_defaults(self, tree):
        """Check for functions with mutable default arguments which cause unexpected behavior."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                has_mutable_defaults = False
                for arg in node.args.defaults:
                    if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                        has_mutable_defaults = True
                        
                        # Check if this might be intentional by looking at function usage
                        category = self.RUNTIME_ERROR  # Default to runtime error
                        
                        # If the function is in our context and we have info about it
                        if func_name in self.functions:
                            func_info = self.functions[func_name]
                            
                            # If the function reassigns the mutable default, it might be intentional
                            reassigns_default = False
                            for i, arg_node in enumerate(node.args.args):
                                if i < len(node.args.defaults) and isinstance(arg_node, ast.arg):
                                    arg_name = arg_node.arg
                                    # Check if this argument is reassigned in the function body
                                    for subnode in ast.walk(node):
                                        if isinstance(subnode, ast.Assign):
                                            for target in subnode.targets:
                                                if isinstance(target, ast.Name) and target.id == arg_name:
                                                    reassigns_default = True
                                                    break
                            
                            # If the function is called multiple times or reassigns the default
                            if func_info['calls'] > 1 or reassigns_default:
                                category = self.POTENTIAL_ERROR
                            # If it's a common pattern but not causing issues yet
                            else:
                                category = self.BAD_HABIT
                                
                        self.feedback.append({
                            'line': node.lineno,
                            'message': f'Function "{node.name}" uses mutable default argument ([], {{}}, or set()). This will be shared across all function calls, causing unexpected behavior when modified.',
                            'is_bad_habit': True,
                            'category': category,
                            'source': 'ast'
                        })
    
    def _check_infinite_loops(self, tree):
        """Check for potential infinite loops with context awareness."""
        for node in ast.walk(tree):
            # Check for while loops with constant True condition
            if isinstance(node, ast.While) and isinstance(node.test, ast.Constant):
                if node.test.value is True:
                    # Check if there's a break statement in the loop body
                    has_break = False
                    has_return = False
                    has_raise = False
                    has_sys_exit = False
                    
                    for child in ast.walk(node):
                        if isinstance(child, ast.Break):
                            has_break = True
                            break
                        elif isinstance(child, ast.Return):
                            has_return = True
                            break
                        elif isinstance(child, ast.Raise):
                            has_raise = True
                            break
                        # Check for sys.exit() calls
                        elif (isinstance(child, ast.Call) and 
                              isinstance(child.func, ast.Attribute) and 
                              child.func.attr == 'exit'):
                            has_sys_exit = True
                            break
                    
                    # Determine category based on context
                    if not (has_break or has_return or has_raise or has_sys_exit):
                        # Check if there's any complex condition that might be an exit condition
                        has_complex_condition = False
                        for child in ast.walk(node):
                            if isinstance(child, ast.If):
                                has_complex_condition = True
                                break
                        
                        # If no exit condition is found, it's a fatal error
                        # If there's a complex condition, it might be intentional
                        category = self.POTENTIAL_ERROR if has_complex_condition else self.FATAL_ERROR
                        
                        self.feedback.append({
                            'line': node.lineno,
                            'message': 'Infinite loop detected (while True without break). This will cause your program to hang indefinitely.',
                            'is_bad_habit': True,
                            'category': category,
                            'source': 'ast'
                        })
    
    def _check_exception_handling(self, tree):
        """Check for overly broad exception handling with context awareness."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == 'Exception'):
                    # Check if the except block is just passing or too generic
                    is_just_pass = False
                    has_logging = False
                    has_print = False
                    has_reraise = False
                    
                    # Check the body of the except handler
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        is_just_pass = True
                    
                    # Look for logging, printing, or re-raising in the except block
                    for stmt in node.body:
                        # Check for logging calls
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            if (isinstance(stmt.value.func, ast.Attribute) and 
                                stmt.value.func.attr in ['debug', 'info', 'warning', 'error', 'critical', 'exception']):
                                has_logging = True
                            # Check for print calls
                            elif isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 'print':
                                has_print = True
                        # Check for re-raising
                        elif isinstance(stmt, ast.Raise):
                            has_reraise = True
                    
                    # Determine category based on context
                    if is_just_pass:
                        # Bare except with pass is always bad
                        category = self.RUNTIME_ERROR
                        
                        # If it's in a try-except-finally block with cleanup, might be intentional
                        parent = getattr(node, 'parent', None)
                        if parent and hasattr(parent, 'finalbody') and parent.finalbody:
                            category = self.BAD_HABIT
                            
                        self.feedback.append({
                            'line': node.lineno,
                            'message': 'Catching all exceptions with a bare except: pass will silence critical errors, making bugs extremely difficult to diagnose.',
                            'is_bad_habit': True,
                            'category': category,
                            'source': 'ast'
                        })
                    else:
                        # If there's logging, printing, or re-raising, it might be intentional
                        if has_logging or has_print or has_reraise:
                            category = self.BAD_HABIT
                        else:
                            # Generic exception handling without proper handling is a potential error
                            category = self.POTENTIAL_ERROR
                        
                        self.feedback.append({
                            'line': node.lineno,
                            'message': 'Catching all exceptions with a bare except or except Exception can mask critical errors. Catch specific exceptions instead.',
                            'is_bad_habit': True,
                            'category': category,
                            'source': 'ast'
                        })
    
    def _check_resource_management(self, tree):
        """Check for proper resource management (files, connections, etc.) with context awareness."""
        # Track file objects and their close calls
        file_vars = {}
        
        for node in ast.walk(tree):
            # Track assignments of open() calls to variables
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'open':
                    var_name = node.targets[0].id
                    file_vars[var_name] = {'node': node, 'closed': False}
            
            # Track close() calls on file variables
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'close':
                    if isinstance(node.value.func.value, ast.Name):
                        var_name = node.value.func.value.id
                        if var_name in file_vars:
                            file_vars[var_name]['closed'] = True
            
            # Check for file operations without context managers
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == 'open':
                    # Check if this open call is part of a with statement
                    is_in_with = False
                    parent = getattr(node, 'parent', None)
                    while parent:
                        if isinstance(parent, ast.With):
                            is_in_with = True
                            break
                        parent = getattr(parent, 'parent', None)
                    
                    # If not in a with statement and not directly assigned to a variable that's later closed
                    if not is_in_with and not (hasattr(node, 'parent') and 
                                              isinstance(node.parent, ast.Assign) and 
                                              len(node.parent.targets) == 1 and 
                                              isinstance(node.parent.targets[0], ast.Name) and
                                              node.parent.targets[0].id in file_vars and
                                              file_vars[node.parent.targets[0].id]['closed']):
                        
                        # Determine category based on context
                        category = self.RUNTIME_ERROR  # Default to runtime error
                        
                        # If it's in a function that has a try-finally, might be closed there
                        parent_func = None
                        parent = getattr(node, 'parent', None)
                        while parent:
                            if isinstance(parent, ast.FunctionDef):
                                parent_func = parent
                                break
                            parent = getattr(parent, 'parent', None)
                        
                        if parent_func:
                            for child in ast.walk(parent_func):
                                if isinstance(child, ast.Try) and child.finalbody:
                                    # If there's a try-finally, it's more likely a bad habit than an error
                                    category = self.BAD_HABIT
                                    break
                        else:
                            # If not in a function with try-finally, it's a potential resource leak
                            category = self.POTENTIAL_ERROR
                        
                        self.feedback.append({
                            'line': node.lineno,
                            'message': 'File opened without using a context manager (with statement). This can lead to resource leaks if the file is not properly closed.',
                            'is_bad_habit': True,
                            'category': category,
                            'source': 'ast'
                        })
    
    def _check_unreachable_code(self, tree):
        """Check for unreachable code after return/break/continue statements with context awareness."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.For, ast.While)):
                # Check for statements after return/break/continue
                has_unreachable = False
                has_return_break_continue = False
                unreachable_line = 0
                
                for i, stmt in enumerate(node.body):
                    if has_return_break_continue and i < len(node.body) - 1:
                        has_unreachable = True
                        unreachable_line = getattr(node.body[i], 'lineno', node.lineno)
                        break
                    
                    # Check if this statement is a return/break/continue
                    if isinstance(stmt, (ast.Return, ast.Break, ast.Continue)):
                        has_return_break_continue = True
                
                if has_unreachable:
                    # Default category - this is a bad habit but not necessarily an error
                    category = self.BAD_HABIT
                    
                    # Check what kind of unreachable code it is
                    unreachable_stmts = []
                    for i, stmt in enumerate(node.body):
                        if has_return_break_continue and i > node.body.index(stmt):
                            unreachable_stmts.append(stmt)
                    
                    # If the unreachable code contains important operations, it's more serious
                    for stmt in unreachable_stmts:
                        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Call)):
                            # Important operations that will never execute - potential error
                            category = self.POTENTIAL_ERROR
                            break
                        elif isinstance(stmt, ast.Return):
                            # Return statement that will never execute - runtime error
                            category = self.RUNTIME_ERROR
                            break
                    
                    self.feedback.append({
                        'line': unreachable_line,
                        'message': 'Unreachable code detected after return, break, or continue statement. This code will never execute.',
                        'is_bad_habit': True,
                        'category': category,
                        'source': 'ast'
                    })
    
    def _check_shadowing_builtins(self, tree):
        """Check for variable names that shadow Python built-ins with context awareness."""
        builtin_names = ['list', 'dict', 'set', 'tuple', 'int', 'float', 'str', 'bool', 'type',
                         'object', 'file', 'open', 'input', 'print', 'range', 'enumerate',
                         'len', 'max', 'min', 'sum', 'filter', 'map', 'zip']
        
        # Track usage of shadowed builtins
        shadowed_builtins = {}
        
        # First pass: collect all shadowing instances
        for node in ast.walk(tree):
            # Check assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in builtin_names:
                        if target.id not in shadowed_builtins:
                            shadowed_builtins[target.id] = []
                        shadowed_builtins[target.id].append({
                            'node': node,
                            'type': 'variable',
                            'uses': 0
                        })
            
            # Check function parameters
            elif isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if arg.arg in builtin_names:
                        if arg.arg not in shadowed_builtins:
                            shadowed_builtins[arg.arg] = []
                        shadowed_builtins[arg.arg].append({
                            'node': node,
                            'type': 'parameter',
                            'uses': 0
                        })
        
        # Second pass: check for usage of shadowed builtins
        for builtin_name, instances in shadowed_builtins.items():
            for instance in instances:
                node = instance['node']
                
                # Default to bad habit - shadowing is usually just a style issue
                category = self.BAD_HABIT
                
                # Check if the original builtin is used after shadowing, which would cause bugs
                tries_to_use_original = False
                scope_node = node
                if instance['type'] == 'parameter':
                    scope_node = node  # The function itself is the scope
                
                for subnode in ast.walk(scope_node):
                    if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name) and subnode.func.id == builtin_name:
                        tries_to_use_original = True
                        break
                
                # If trying to use the original after shadowing, it's a runtime error
                if tries_to_use_original:
                    category = self.RUNTIME_ERROR
                # If shadowing critical builtins like 'open', 'print', it's a potential error
                elif builtin_name in ['open', 'print', 'input', 'len', 'str', 'int', 'float']:
                    category = self.POTENTIAL_ERROR
                
                if instance['type'] == 'variable':
                    self.feedback.append({
                        'line': node.lineno,
                        'message': f'Variable name "{builtin_name}" shadows a Python built-in. This will prevent you from using the original built-in function in this scope.',
                        'is_bad_habit': True,
                        'category': category,
                        'source': 'ast'
                    })
                else:  # parameter
                    self.feedback.append({
                        'line': node.lineno,
                        'message': f'Function parameter "{builtin_name}" shadows a Python built-in. This will prevent you from using the original built-in function inside this function.',
                        'is_bad_habit': True,
                        'category': category,
                        'source': 'ast'
                    })

def generate_explanation(issue, code_lines=None):
    """Generate a user-friendly explanation and fix for an issue using Claude."""
    if not anthropicClient:
        return {
            "explanation": "AI explanations unavailable. Please set up the Anthropic API key.",
            "fix": None
        }
    
    try:
        # Extract relevant information from the issue
        category = issue.get('category', 'unknown')
        message = issue.get('message', '')
        line_num = issue.get('line', 0)
        
        # Get the relevant code snippet if code_lines is provided
        code_snippet = ""
        if code_lines and line_num > 0:
            # Get a few lines before and after the issue line for context
            start_line = max(0, line_num - 3)
            end_line = min(len(code_lines), line_num + 3)
            for i in range(start_line, end_line):
                if i < len(code_lines):
                    code_snippet += f"{i+1} {code_lines[i]}\n"
        
        # Create a prompt for Claude
        prompt = f"""You are a Python expert helping a programmer understand and fix an issue in their code.
        
        Issue Category: {category}
        Issue Message: {message}
        Line Number: {line_num}
        
        Here is the actual code with the issue:
        ```python
{code_snippet}
        ```
        
        Please provide:
        1. A very brief explanation (1-2 sentences max) of what this issue means in simple terms
        2. A direct, specific code fix with EXACT code examples showing:
           - The problematic code (labeled 'BEFORE:') with line numbers - USE THE EXACT CODE SHOWN ABOVE
           - The fixed code (labeled 'AFTER:') with line numbers - MODIFY ONLY WHAT NEEDS TO BE CHANGED
           - Show the EXACT code to replace, not just a description
           - Use the same variable names and structure as in the original code
        
        Format your response exactly like this:
        Explanation: [1-2 sentence explanation]
        
        Fix:
        BEFORE:
        ```python
        # Exact problematic code with line numbers
        ```
        
        AFTER:
        ```python
        # Exact fixed code with line numbers
        ```
        """
        
        # Call Claude API
        message = anthropicClient.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0,
            system="You are a helpful Python expert. Provide clear, concise explanations and fixes for Python code issues.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and parse the response
        response_text = message.content[0].text
        
        # Extract explanation and fix using the format markers
        explanation_match = response_text.split('Explanation:', 1)
        explanation = explanation_match[1].split('Fix:', 1)[0].strip() if len(explanation_match) > 1 else "Failed to parse explanation."
        
        fix_match = response_text.split('Fix:', 1)
        fix = fix_match[1].strip() if len(fix_match) > 1 else None
        
        return {
            "explanation": explanation,
            "fix": fix
        }
    except Exception as e:
        print(f"Error generating explanation: {str(e)}")
        return {
            "explanation": "Failed to generate explanation.",
            "fix": None
        }

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze the submitted Python code for runtime issues with context awareness."""
    data = request.get_json()
    code = data.get('code', '')
    
    # Split code into lines for context in explanations
    code_lines = code.split('\n')
    
    analyzer = PythonHabitAnalyzer()
    feedback = analyzer.analyze(code)
    
    # Generate explanations for each issue if AI is available
    if anthropicClient:
        for issue in feedback:
            # Only generate explanations for actual issues (not system messages)
            if issue.get('source') != 'system':
                explanation_data = generate_explanation(issue, code_lines)
                issue['explanation'] = explanation_data['explanation']
                issue['fix'] = explanation_data['fix']
    
    # Ensure all feedback items have a category
    for item in feedback:
        # Convert old certainty levels to new categories if needed
        if 'certainty' in item and 'category' not in item:
            if item['certainty'] == 'error':
                if 'SyntaxError' in item['message']:
                    item['category'] = analyzer.SYNTAX_ERROR
                elif any(fatal in item['message'] for fatal in ['division by zero', 'index out of range', 'key error']):
                    item['category'] = analyzer.FATAL_ERROR
                else:
                    item['category'] = analyzer.RUNTIME_ERROR
            elif item['certainty'] == 'might_error':
                item['category'] = analyzer.POTENTIAL_ERROR
            else:
                item['category'] = analyzer.BAD_HABIT
        elif 'category' not in item:
            # Default to runtime error if no category specified
            item['category'] = analyzer.RUNTIME_ERROR
    
    # Sort feedback by category priority and line number
    category_priority = {
        analyzer.SYNTAX_ERROR: 0,
        analyzer.FATAL_ERROR: 1,
        analyzer.RUNTIME_ERROR: 2,
        analyzer.POTENTIAL_ERROR: 3,
        analyzer.BAD_HABIT: 4
    }
    
    feedback.sort(key=lambda x: (category_priority.get(x['category'], 999), x['line']))
    
    return jsonify({'feedback': feedback})


# For local development
if __name__ == '__main__':
    app.run(debug=True)

# For Vercel deployment
app = app
