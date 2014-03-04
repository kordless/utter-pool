"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""

from webapp2_extras.routes import RedirectRoute
from web import handlers
from web.users import userhandlers
from web.api import apihandlers

secure_scheme = 'https'

_routes = [
    # mail processing
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # user logins
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/login/', userhandlers.LogoutHandler, name='login', strict_slash=True),
    RedirectRoute('/login/complete', userhandlers.CallbackSocialLoginHandler, name='social-login-complete', strict_slash=True),
    RedirectRoute('/login/delete', userhandlers.DeleteSocialProviderHandler, name='delete-social-provider', strict_slash=True),

    # user settings
    RedirectRoute('/settings/profile', userhandlers.EditProfileHandler, name='edit-profile', strict_slash=True),

    # website
    RedirectRoute('/', handlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/about/', handlers.AboutHandler, name='company', strict_slash=True),
    RedirectRoute('/pricing/', handlers.PricingHandler, name='pricing', strict_slash=True),
    RedirectRoute('/features/', handlers.TourHandler, name='features', strict_slash=True),
    RedirectRoute('/contact/', handlers.ContactHandler, name='contact', strict_slash=True),
    RedirectRoute('/forums/', handlers.ForumHandler, name='forums', strict_slash=True),

    # api
    RedirectRoute('/api/<public_method>', apihandlers.APIPublicHandler, name='api_public', strict_slash=True)
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
