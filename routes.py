from webapp2_extras.routes import RedirectRoute
from web import handlers
from web.users import userhandlers
from web.api import apihandlers
from web.blog import bloghandlers

secure_scheme = 'https'

_routes = [
    # mail processing
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # website
    RedirectRoute('/', handlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/about/', handlers.AboutHandler, name='company', strict_slash=True),
    RedirectRoute('/pricing/', handlers.PricingHandler, name='pricing', strict_slash=True),
    RedirectRoute('/features/', handlers.TourHandler, name='features', strict_slash=True),
    RedirectRoute('/contact/', handlers.ContactHandler, name='contact', strict_slash=True),
    RedirectRoute('/forums/', handlers.ForumHandler, name='forums', strict_slash=True),

    # users
    RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/login/complete', userhandlers.CallbackLoginHandler, name='login-complete', strict_slash=True),
    RedirectRoute('/account/', userhandlers.AccountHandler, name='account', strict_slash=True),
    RedirectRoute('/account/twofactor/', userhandlers.TwoFactorHandler, name='account-twofactor', strict_slash=True),

    # api
    RedirectRoute('/api/<public_method>', apihandlers.APIPublicHandler, name='api_public', strict_slash=True),

    # blog handlers
    RedirectRoute('/blog/', bloghandlers.PublicBlogHandler, name='blog', strict_slash=True),
    RedirectRoute('/blog/feed/rss/', bloghandlers.PublicBlogRSSHandler, name='blog-rss', strict_slash=True),
    RedirectRoute('/blog/articles/new/', bloghandlers.BlogArticleCreateHandler, name='blog-article-create', strict_slash=True),
    RedirectRoute('/blog/articles/', bloghandlers.BlogArticleListHandler, name='blog-article-list', strict_slash=True),
    RedirectRoute('/blog/<slug>', bloghandlers.BlogArticleSlugHandler, name='blog-article-slug', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
