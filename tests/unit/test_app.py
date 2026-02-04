"""
Unit tests for app configuration and startup
"""

class TestAppConfiguration:
    """Tests for app configuration and initialization"""
    
    def test_app_creation(self):
        """Test that app can be created"""
        from app import create_app
        
        app, cache = create_app()
        
        assert app is not None
        assert cache is not None
        assert app.name == 'app'
        assert hasattr(app, 'config')
    
    def test_app_configuration(self):
        """Test app configuration"""
        from app import create_app
        from config import Config
        
        app, _ = create_app()
        
        # Test some config values
        assert app.config['TESTING'] is False
        assert 'SECRET_KEY' in app.config
        assert app.config['MAX_CONTENT_LENGTH'] == Config.MAX_CONTENT_LENGTH
        
        # Test that Config values are loaded
        assert app.config['ROOT_DRIVE'] == Config.ROOT_DRIVE
    
    def test_app_blueprints(self):
        """Test that blueprints are registered"""
        from app import create_app
        
        app, _ = create_app()
        
        # Check routes blueprint is registered
        blueprints = app.blueprints
        assert 'routes' in blueprints
        
        # Check some routes exist
        url_map = list(app.url_map.iter_rules())
        routes = [str(rule) for rule in url_map]
        
        # Should have basic routes
        assert any('/' in route for route in routes)
        assert any('/browse/' in route for route in routes)
        assert any('/search' in route for route in routes)
    
    def test_app_error_handlers(self):
        """Test error handlers are registered"""
        from app import create_app
        
        app, _ = create_app()
        
        # Check error handlers
        error_handlers = app.error_handler_spec
        
        # Should have handlers for common errors
        assert 404 in error_handlers.get(None, {})
        assert 500 in error_handlers.get(None, {})
        assert 413 in error_handlers.get(None, {})
    
    def test_app_context_processor(self):
        """Test context processor injects globals"""
        from app import create_app
        from flask import template_rendered
        
        app, _ = create_app()
        
        captured = []
        
        def record(sender, template, context, **extra):
            captured.append((template, context))
        
        template_rendered.connect(record, app)
        
        with app.test_client() as client:
            client.get('/')  # Trigger template render
        
        # Check context has injected globals
        if captured:
            _, context = captured[0]
            assert 'year' in context
            assert 'app_name' in context
            assert 'version' in context
    
    def test_app_logging_config(self):
        """Test logging configuration"""
        from app import create_app
        
        app, _ = create_app()
        
        # Check logger exists
        assert hasattr(app, 'logger')
        assert app.logger is not None
        
        # Check log directory
        from config import Config
        import logging.config
        logging_config = Config.LOGGING_CONFIG
        
        assert 'handlers' in logging_config
        assert 'file' in logging_config['handlers']
        assert 'filename' in logging_config['handlers']['file']