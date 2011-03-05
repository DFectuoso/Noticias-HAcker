from gaesessions import SessionMiddleware
import keys

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key=keys.cookie_key)
    return app
