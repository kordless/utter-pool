from webapp2_extras.routes import RedirectRoute
from web.site import handlers
from web.users import userhandlers
from web.api import apihandlers
from web.blog import bloghandlers

secure_scheme = 'https'

_routes = [
    # mail processing
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # website
    RedirectRoute('/', handlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/about/', handlers.AboutHandler, name='about', strict_slash=True),
    RedirectRoute('/pricing/', handlers.PricingHandler, name='pricing', strict_slash=True),
    RedirectRoute('/features/', handlers.FeaturesHandler, name='features', strict_slash=True),

    # users
    RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/login/complete', userhandlers.CallbackLoginHandler, name='login-complete', strict_slash=True),
    RedirectRoute('/login/tfa', userhandlers.TwoFactorLoginHandler, name='login-tfa', strict_slash=True),
    RedirectRoute('/account/', userhandlers.AccountHandler, name='account', strict_slash=True),
    RedirectRoute('/clouds/', userhandlers.CloudHandler, name='account-clouds', strict_slash=True),
    RedirectRoute('/settings/', userhandlers.SettingsHandler, name='account-settings', strict_slash=True),
    RedirectRoute('/settings/tfa', userhandlers.TwoFactorSettingsHandler, name='account-tfa', strict_slash=True),
    RedirectRoute('/appliances/', userhandlers.ApplianceHandler, name='account-appliances', strict_slash=True),

    # api
    RedirectRoute('/api/<public_method>', apihandlers.APIPublicHandler, name='api_public', strict_slash=True),

    # blog handlers
    RedirectRoute('/blog/', bloghandlers.BlogHandler, name='blog', strict_slash=True),
    RedirectRoute('/blog/feed/rss/', bloghandlers.RSSHandler, name='blog-rss', strict_slash=True),
    RedirectRoute('/blog/articles/', bloghandlers.ListHandler, name='blog-article-list', strict_slash=True),
    RedirectRoute('/blog/actions/<article_id>/', bloghandlers.ActionsHandler, name='blog-article-action', strict_slash=True),
    RedirectRoute('/blog/<slug>/', bloghandlers.SlugHandler, name='blog-article-slug', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
