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
    # Check if API key is available
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    print(f"API key available: {bool(api_key)}")
    if api_key:
        print(f"API key length: {len(api_key)}")
        print(f"API key starts with: {api_key[:10]}...")
        # Set the API key explicitly
        os.environ['ANTHROPIC_API_KEY'] = api_key.strip()
        anthropicClient = Anthropic(api_key=api_key.strip())
        print("Anthropic client initialized successfully with explicit API key")
    else:
        print("No API key found in environment variables")
        # Try initializing without explicit key (will use env var if available)
        anthropicClient = Anthropic()
        print("Anthropic client initialized successfully with default API key")
except Exception as e:
    print(f"Failed to initialize Anthropic client: {str(e)}")
    print("AI explanations will not be available.")

app = Flask(__name__)
app.template_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
app.static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

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
        
        analyzer = PythonHabitAnalyzer()
        feedback = analyzer.analyze(code)
        
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
                if item.get('certainty') == 'might_error':
                    item['category'] = 'potential_error'
                else:
                    item['category'] = 'runtime_error'
                    
        # Sort feedback by category priority and line number
        category_priority = {
            'syntax_error': 0,
            'fatal_error': 1,
            'runtime_error': 2,
            'potential_error': 3,
            'bad_habit': 4
        }
        
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
