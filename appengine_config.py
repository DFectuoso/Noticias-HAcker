from gaesessions import SessionMiddleware
def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key="VepaR94rE2u2ucHU6Efrapucabruc2wrewrebAcayuSubufuwe3Ta7uYEzaTeY7f")
    return app
