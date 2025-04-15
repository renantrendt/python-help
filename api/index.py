from flask import Flask, request, jsonify, render_template
import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic

# Add the parent directory to sys.path so we can import from app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the analyzer class from the main app
from app import PythonHabitAnalyzer

# Load environment variables from .env file
load_dotenv()

# Initialize Anthropic client
anthropicClient = None
try:
    # Get API key directly from environment
    # First try with ANTHROPIC_API_KEY (standard)
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    # If not found, try with VERCEL_ANTHROPIC_API_KEY (for Vercel)
    if not api_key:
        api_key = os.environ.get('VERCEL_ANTHROPIC_API_KEY')
        if api_key:
            print("Using VERCEL_ANTHROPIC_API_KEY instead of ANTHROPIC_API_KEY")
    
    print(f"API key available: {bool(api_key)}")
    
    if not api_key:
        print("No API key found in environment variables")
        print("Checked both ANTHROPIC_API_KEY and VERCEL_ANTHROPIC_API_KEY")
    else:
        # Initialize with direct API key parameter
        anthropicClient = Anthropic(api_key=api_key.strip())
        print("Anthropic client initialized successfully")
        
        # Test the client with a simple request to verify it works
        try:
            response = anthropicClient.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            print("Anthropic client test successful")
        except Exception as test_error:
            print(f"Anthropic client test failed: {str(test_error)}")
            anthropicClient = None
except Exception as e:
    print(f"Failed to initialize Anthropic client: {str(e)}")
    print("AI explanations will not be available.")

app = Flask(__name__)
app.template_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
app.static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

# Add ProxyFix middleware for proper request handling in Vercel
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        code = data.get('code', '')
        
        # Split code into lines for context
        code_lines = code.split('\n')
        
        # Initialize feedback array
        feedback = []
        defined_vars = set()
        defined_functions = set()
        
        # First pass: check for syntax errors
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            feedback.append({
                'line': e.lineno,
                'message': f'SyntaxError: {e.msg}',
                'category': 'syntax_error',
                'source': 'analyzer'
            })
        
        # If no syntax errors, continue with other checks
        if not feedback:
            try:
                # Try using the original analyzer if available
                analyzer = PythonHabitAnalyzer()
                feedback = analyzer.analyze(code)
            except Exception as e:
                print(f"Error using main analyzer: {e}")
                # If the main analyzer fails, use our fallback implementation
                try:
                    # Parse the code
                    import ast
                    tree = ast.parse(code)
                    
                    # First pass: collect defined variables and functions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    defined_vars.add(target.id)
                        elif isinstance(node, ast.FunctionDef):
                            defined_functions.add(node.name)
                    
                    # Second pass: check for issues
                    for node in ast.walk(tree):
                        # Check for undefined variables
                        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                            var_name = node.id
                            # Skip built-ins and common functions
                            builtins = ['print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'sum', 'min', 'max', 'open', 'type']
                            if var_name not in defined_vars and var_name not in defined_functions and var_name not in builtins and not var_name.startswith('__'):
                                feedback.append({
                                    'line': node.lineno,
                                    'message': f'Undefined variable \'{var_name}\'',
                                    'category': 'runtime_error',
                                    'source': 'analyzer'
                                })
                        # Check for attribute errors
                        elif isinstance(node, ast.Attribute):
                            if isinstance(node.value, ast.Name):
                                obj_name = node.value.id
                                attr_name = node.attr
                                # If we can't find the object in defined vars, it might be an attribute error
                                if obj_name not in defined_vars and obj_name not in builtins:
                                    feedback.append({
                                        'line': node.lineno,
                                        'message': f'Instance of \'{obj_name}\' has no \'{attr_name}\' member',
                                        'category': 'runtime_error',
                                        'source': 'analyzer'
                                    })
                        # Check for potential infinite loops
                        elif isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value == True:
                            feedback.append({
                                'line': node.lineno,
                                'message': 'Infinite loop detected',
                                'category': 'fatal_error',
                                'source': 'analyzer'
                            })
                        # Check for catching all exceptions
                        elif isinstance(node, ast.ExceptHandler) and node.type is None:
                            feedback.append({
                                'line': node.lineno,
                                'message': 'Catching all exceptions (bare except) is a bad practice',
                                'category': 'bad_habit',
                                'source': 'analyzer'
                            })
                        # Check for mutable default arguments
                        elif isinstance(node, ast.FunctionDef):
                            for default in node.args.defaults:
                                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                    feedback.append({
                                        'line': node.lineno,
                                        'message': f'Using mutable default argument in function \'{node.name}\'',
                                        'category': 'potential_error',
                                        'source': 'analyzer'
                                    })
                except Exception as ast_error:
                    print(f"Error in AST analysis: {str(ast_error)}")
                    feedback.append({
                        'line': 1,
                        'message': f'Error analyzing code: {str(ast_error)}',
                        'category': 'runtime_error',
                        'source': 'system'
                    })
        
        # Generate explanations for each issue if AI is available
        if anthropicClient:
            print("Anthropic client is available, generating explanations...")
            try:
                for issue in feedback:
                    # Only generate explanations for actual issues (not system messages)
                    if issue.get('source') != 'system':
                        print(f"Generating explanation for issue: {issue.get('message')}")
                        explanation_data = generate_explanation(issue, code_lines)
                        print(f"Explanation generated: {bool(explanation_data.get('explanation'))}")
                        issue['explanation'] = explanation_data['explanation']
                        issue['fix'] = explanation_data['fix']
            except Exception as explain_error:
                print(f"Error generating explanations: {str(explain_error)}")
                # Add an error message to the feedback
                feedback.append({
                    'line': 0,
                    'message': f'Error generating explanations: {str(explain_error)}',
                    'category': 'syntax_error',
                    'source': 'system',
                    'explanation': f'Failed to generate explanations: {str(explain_error)}',
                    'fix': None
                })
        else:
            print("Anthropic client not available, skipping explanations")
        
        # Ensure all feedback items have a category
        for item in feedback:
            # Convert old certainty levels to new categories if needed
            if 'certainty' in item and 'category' not in item:
                if item.get('certainty') == 'error':
                    if 'SyntaxError' in item.get('message', ''):
                        item['category'] = 'syntax_error'
                    elif any(fatal in item.get('message', '') for fatal in ['division by zero', 'index out of range', 'key error']):
                        item['category'] = 'fatal_error'
                    else:
                        item['category'] = 'runtime_error'
                elif item.get('certainty') == 'might_error':
                    item['category'] = 'potential_error'
                else:
                    item['category'] = 'bad_habit'
            elif 'category' not in item:
                # Default to runtime error if no category specified
                item['category'] = 'runtime_error'
        # Sort feedback by category priority and line number
        category_priority = {
            'syntax_error': 0,
            'fatal_error': 1,
            'runtime_error': 2,
            'potential_error': 3,
            'bad_habit': 4
        }
        
        # Ensure all error types are being detected
        print(f"Categories detected: {[item.get('category', 'unknown') for item in feedback]}")
        
        feedback.sort(key=lambda x: (category_priority.get(x.get('category', 'runtime_error'), 999), x.get('line', 0)))
        
        return jsonify({'feedback': feedback})
    except Exception as e:
        return jsonify({
            'error': str(e),
            'feedback': [{
                'line': 0,
                'message': f'Server error: {str(e)}',
                'category': 'syntax_error',
                'source': 'system'
            }]
        }), 500

# Function to generate explanations using Claude API
def generate_explanation(issue, code_lines=None):
    """Generate a user-friendly explanation and fix for an issue using Claude."""
    if not anthropicClient:
        print("Anthropic client not available. Cannot generate explanation.")
        return {
            "explanation": "AI explanations unavailable. Please set up the Anthropic API key in Vercel environment variables.",
            "fix": None
        }
    
    # Double-check API key before making request
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("API key missing when generating explanation")
        return {
            "explanation": "API key is missing. Please set the ANTHROPIC_API_KEY environment variable in Vercel.",
            "fix": None
        }
    
    try:
        # Extract relevant information from the issue
        category = issue.get('category', 'unknown')
        message = issue.get('message', '')
        line_num = issue.get('line', 0)
        
        print(f"Generating explanation for issue: {category} - {message} at line {line_num}")
        
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
        try:
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
            print(f"Claude API response received: {response_text[:100]}...")
            
            # Extract explanation and fix using the format markers
            explanation_match = response_text.split('Explanation:', 1)
            if len(explanation_match) > 1:
                explanation_text = explanation_match[1]
                fix_parts = explanation_text.split('Fix:', 1)
                explanation = fix_parts[0].strip()
                
                if len(fix_parts) > 1:
                    fix = fix_parts[1].strip()
                else:
                    fix = None
                    print("No 'Fix:' section found in Claude response")
            else:
                explanation = "Claude did not return an explanation in the expected format."
                fix = None
                print(f"Failed to parse explanation from Claude response: {response_text}")
            
            return {
                "explanation": explanation,
                "fix": fix
            }
            
        except Exception as api_error:
            print(f"Error calling Claude API: {str(api_error)}")
            return {
                "explanation": f"Error calling Claude API: {str(api_error)}",
                "fix": None
            }
            
    except Exception as e:
        print(f"Error in generate_explanation: {str(e)}")
        return {
            "explanation": f"Failed to generate explanation: {str(e)}",
            "fix": None
        }

# For Vercel
if __name__ == '__main__':
    app.run(debug=True)
