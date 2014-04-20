from webapp2_extras.routes import RedirectRoute
from web.handlers import sitehandlers, adminhandlers, userhandlers, apihandlers, bloghandlers, appliancehandlers, grouphandlers, cloudhandlers

secure_scheme = 'https'

_routes = [
    # mail processing
    RedirectRoute('/taskqueue-send-email/', sitehandlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # admin
    RedirectRoute('/admin/', adminhandlers.AdminHandler, name='admin', strict_slash=True),
    RedirectRoute('/admin/users/', adminhandlers.UsersHandler, name='admin-users', strict_slash=True),
    RedirectRoute('/admin/flavors/', adminhandlers.FlavorsListHandler, name='admin-flavors', strict_slash=True),
    RedirectRoute('/admin/flavors/<flavor_id>/', adminhandlers.FlavorsActionsHandler, name='admin-flavors-action', strict_slash=True),
    RedirectRoute('/admin/images/', adminhandlers.ImagesListHandler, name='admin-images', strict_slash=True),
    RedirectRoute('/admin/images/<image_id>/', adminhandlers.ImagesActionsHandler, name='admin-images-action', strict_slash=True),
    RedirectRoute('/admin/groups/', adminhandlers.GroupsHandler, name='admin-groups', strict_slash=True),

    # website
    RedirectRoute('/', sitehandlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/about/', sitehandlers.AboutHandler, name='about', strict_slash=True),
    RedirectRoute('/pricing/', sitehandlers.PricingHandler, name='pricing', strict_slash=True),
    RedirectRoute('/features/', sitehandlers.FeaturesHandler, name='features', strict_slash=True),

    # users
    RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/login/complete', userhandlers.CallbackLoginHandler, name='login-complete', strict_slash=True),
    RedirectRoute('/login/tfa', userhandlers.TwoFactorLoginHandler, name='login-tfa', strict_slash=True),
    RedirectRoute('/account/', userhandlers.AccountHandler, name='account', strict_slash=True),
    RedirectRoute('/settings/', userhandlers.SettingsHandler, name='account-settings', strict_slash=True),
    RedirectRoute('/settings/tfa', userhandlers.TwoFactorSettingsHandler, name='account-tfa', strict_slash=True),
    
    # appliances
    RedirectRoute('/appliances/', appliancehandlers.ApplianceHandler, name='account-appliances', strict_slash=True),
    RedirectRoute('/appliances/new/', appliancehandlers.NewApplianceHandler, name='account-appliances-new', strict_slash=True),
    RedirectRoute('/appliances/groups/', appliancehandlers.ApplianceGroupHandler, name='account-appliances-groups', strict_slash=True),
    RedirectRoute('/appliances/<appliance_id>/', appliancehandlers.ApplianceDetailHandler, name='account-appliances-detail', strict_slash=True),

    # clouds
    RedirectRoute('/clouds/', cloudhandlers.CloudHandler, name='account-clouds', strict_slash=True),

    # api
    RedirectRoute('/api/v1/groups', grouphandlers.GroupHandler, name='api-groups', strict_slash=False),
    RedirectRoute('/api/v1/authorization', apihandlers.TokenValidate, name='api-token-validate', strict_slash=False),
    RedirectRoute('/api/v1/track', apihandlers.TrackingPingHandler, name='api-track', strict_slash=False),
    RedirectRoute('/api/v1/images', apihandlers.ImagesHandler, name='api-images', strict_slash=False),
    RedirectRoute('/api/v1/flavors', apihandlers.FlavorsHandler, name='api-flavors', strict_slash=False),
    
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
