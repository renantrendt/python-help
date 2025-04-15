import os
import sys
import logging

# Configure logging for Vercel environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path so we can import from app.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
logger.info(f"Added parent directory to sys.path: {parent_dir}")

# Import the Flask app and other components from the main app file
from app import app, PythonHabitAnalyzer, anthropicClient, generate_explanation

# Log the status of the Anthropic client
logger.info(f"Anthropic client available in index.py: {anthropicClient is not None}")

# Configure template and static folders for Vercel environment
app.template_folder = os.path.join(parent_dir, 'templates')
app.static_folder = os.path.join(parent_dir, 'static')
logger.info(f"Set template folder to: {app.template_folder}")
logger.info(f"Set static folder to: {app.static_folder}")

# Add ProxyFix middleware for proper request handling in Vercel
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
logger.info("Applied ProxyFix middleware to Flask app")

# Routes are imported from app.py
# This file only serves as an entry point for Vercel

# Log that the index.py file has been loaded
logger.info("index.py loaded and ready to serve requests")
# For Vercel
if __name__ == '__main__':
    # Log that the server is starting
    logger.info("Starting Flask server in index.py")
    app.run(debug=True)
