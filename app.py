"""
Main application entry point for Universal File Server
"""

import logging
import logging.config
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
from flask_caching import Cache

from config import Config
from controllers.routes import routes

# Configure logging
def setup_logging():
    """Setup application logging"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    logging.config.dictConfig(Config.LOGGING_CONFIG)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/stream/*": {"origins": "*"}
    })
    
    # Setup caching
    cache = Cache(app, config={'CACHE_TYPE': Config.CACHE_TYPE})
    
    # Register blueprints
    app.register_blueprint(routes)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', 
                             error_code=404,
                             error_message="The requested page was not found."), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html',
                             error_code=500,
                             error_message="An internal server error occurred."), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template('error.html',
                             error_code=413,
                             error_message="File too large."), 413
    
    # Global context processors
    @app.context_processor
    def inject_globals():
        return {
            'year': datetime.now().year,
            'app_name': 'Universal File Server',
            'version': '1.0.0',
            'Config': Config
        }
    
    # Before request handlers
    @app.before_request
    def before_request():
        # Log request
        app.logger.info(f"{request.remote_addr} - {request.method} {request.path}")
        
        # Security headers
        response_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
        }
        
        if not Config.DEBUG:
            response_headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Set headers
        for header, value in response_headers.items():
            request.environ[header] = value
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'universal-file-server',
            'version': '1.0.0'
        }
    
    # Favicon
    @app.route('/favicon.ico')
    def favicon():
        return redirect(url_for('static', filename='favicon.ico'), code=302)
    
    return app, cache

# Create application
app, cache = create_app()

if __name__ == '__main__':
    # Setup logging
    setup_logging()
    
    # Log startup information
    app.logger.info("=" * 50)
    app.logger.info("Starting Universal File Server")
    app.logger.info(f"Version: 1.0.0")
    app.logger.info(f"Debug Mode: {Config.DEBUG}")
    app.logger.info(f"Root Drive: {Config.ROOT_DRIVE}")
    app.logger.info(f"Host: {Config.HOST}")
    app.logger.info(f"Port: {Config.PORT}")
    app.logger.info("=" * 50)
    
    # Run application
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True
    )