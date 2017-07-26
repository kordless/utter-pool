from webapp2_extras.routes import RedirectRoute
from web.handlers import sitehandlers, adminhandlers, userhandlers, bloghandlers, emailhandlers, taskhandlers
# from web.handlers import foo

secure_scheme = 'https'

_routes = [
	# website
	RedirectRoute('/', sitehandlers.HomeRequestHandler, name='home', strict_slash=True),
	RedirectRoute('/features/', sitehandlers.FeaturesHandler, name='features', strict_slash=True),
	RedirectRoute('/docs/', sitehandlers.DocsHandler, name='docs', strict_slash=True),
	RedirectRoute('/apis/', sitehandlers.APIsHandler, name='projects', strict_slash=True),
	RedirectRoute('/terms/', sitehandlers.TermsHandler, name='terms', strict_slash=True),
	RedirectRoute('/privacy/', sitehandlers.PrivacyHandler, name='privacy', strict_slash=True),
	RedirectRoute('/about/', sitehandlers.AboutHandler, name='privacy', strict_slash=True),
	
	# users
	RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
	RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
	RedirectRoute('/login/complete', userhandlers.CallbackLoginHandler, name='login-complete', strict_slash=True),
	RedirectRoute('/login/tfa', userhandlers.TwoFactorLoginHandler, name='login-tfa', strict_slash=True),
	RedirectRoute('/settings/', userhandlers.SettingsHandler, name='account-settings', strict_slash=True),
	RedirectRoute('/settings/tfa', userhandlers.TwoFactorSettingsHandler, name='account-tfa', strict_slash=True),
	RedirectRoute('/status/', userhandlers.StatusHandler, name='account-status', strict_slash=True),

	# tasks
	RedirectRoute('/tasks/sendinvite/', emailhandlers.SendEmailInviteHandler, name='tasks-sendinvite', strict_slash=True),
	RedirectRoute('/tasks/mail/', sitehandlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

	# admin
	RedirectRoute('/admin/', adminhandlers.AdminHandler, name='admin', strict_slash=True),
	RedirectRoute('/admin/users/', adminhandlers.UsersHandler, name='admin-users', strict_slash=True),
	RedirectRoute('/admin/users/export/', adminhandlers.UsersExportHandler, name='admin-users-export', strict_slash=True),

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
