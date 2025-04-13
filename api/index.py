from flask import Flask, request, jsonify, render_template
import os
import sys

# Add the parent directory to sys.path so we can import from app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the analyzer class from the main app
from app import PythonHabitAnalyzer

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
        
        # Ensure all feedback items have a category
        for item in feedback:
            # Convert old certainty levels to new categories if needed
            if 'certainty' in item and 'category' not in item:
                if item.get('certainty') == 'might_error':
                    item['category'] = 'potential_error'
                else:
                    item['category'] = 'runtime_error'
        
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

# For Vercel
if __name__ == '__main__':
    app.run(debug=True)
