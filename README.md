# Python Runtime Analyzer

A web application that analyzes Python code for potential runtime issues, categorizes them by severity, and provides AI-powered explanations and fixes.

## Features

- Paste Python code into a modern code editor with syntax highlighting and tab indentation
- Comprehensive static analysis using Pylint and Python's AST module
- Five distinct error categories: Syntax Error, Runtime Error, Fatal Error, Bad Habit, and Potential Error
- Context-aware analysis that understands code patterns and usage
- AI-powered explanations and specific code fixes using Claude API
- Syntax-highlighted code examples showing before/after fixes

## Project Structure

```
python-analyzer/
├── app.py                 # Flask application
├── requirements.txt       # Project dependencies
├── static/                # Static files
│   ├── css/
│   │   └── style.css      # CSS styles
│   └── js/
│       └── script.js      # JavaScript for frontend functionality
└── templates/
    └── index.html         # HTML template
```

## Setup Instructions

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Run the Flask application:

```bash
python app.py
```

3. Open your web browser and navigate to http://127.0.0.1:5000/

## How It Works

### Backend

The backend uses three main approaches for analyzing Python code:

1. **Pylint Analysis**: Uses the Pylint library to check for style issues, potential errors, and code smells.

2. **Custom AST Analysis**: Uses Python's Abstract Syntax Tree (AST) module to perform custom checks for:
   - Mutable default arguments
   - Infinite loops
   - Resource management issues
   - Exception handling problems
   - Unreachable code
   - Shadowing of built-in names

3. **AI-Powered Explanations**: Uses the Claude API to generate user-friendly explanations and specific code fixes for detected issues.

### Frontend

The frontend provides a modern interface where users can:

1. Write or paste Python code into a CodeMirror editor with syntax highlighting and tab indentation
2. Click the "Analyze Runtime Issues" button to send the code to the backend
3. View the analysis results, with issues categorized by severity and type
4. See a summary of issues by category (Syntax Error, Runtime Error, Fatal Error, etc.)
5. Get AI-generated explanations of each issue in plain language
6. Receive specific code fixes with syntax-highlighted before/after examples

## Example Issues Detected

- **Syntax Errors**: Issues that prevent code from running
- **Runtime Errors**: Issues that cause errors during execution
- **Fatal Errors**: Issues that will definitely crash the program (like infinite loops)
- **Bad Habits**: Practices that make code harder to maintain or understand
- **Potential Errors**: Code that might cause problems in certain conditions

## Future Enhancements

- Integration with additional static analysis tools
- Ability to save analysis history
- Support for analyzing entire Python projects/files
- Custom rule configuration
- Additional error categories and checks
- Support for more programming languages
