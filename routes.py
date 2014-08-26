from webapp2_extras.routes import RedirectRoute
from web.handlers import sitehandlers, adminhandlers, userhandlers, apihandlers, bloghandlers, emailhandlers, taskhandlers
from web.handlers import statushandlers, appliancehandlers, grouphandlers, cloudhandlers, wisphandlers, labhandlers

secure_scheme = 'https'

_routes = [
		# tasks
		RedirectRoute('/tasks/sendinvite/', emailhandlers.SendEmailInviteHandler, name='tasks-sendinvite', strict_slash=True),
		RedirectRoute('/tasks/instances/', taskhandlers.InstancesHandler, name='tasks-instances', strict_slash=True),
		RedirectRoute('/tasks/instancebids/', taskhandlers.InstanceBidsHandler, name='tasks-instancebids', strict_slash=True),

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
		RedirectRoute('/settings/', userhandlers.SettingsHandler, name='account-settings', strict_slash=True),
		RedirectRoute('/settings/tfa', userhandlers.TwoFactorSettingsHandler, name='account-tfa', strict_slash=True),
		
		# status
		RedirectRoute('/status/', statushandlers.StatusHandler, name='account-status', strict_slash=True),

		# instances
		RedirectRoute('/launcher/', labhandlers.LauncherHandler, name='lab-launcher', strict_slash=True),
		RedirectRoute('/bids/', labhandlers.BidsHandler, name='lab-bids', strict_slash=True),
		RedirectRoute('/bids/<token>/', labhandlers.BidDetailHandler, name='lab-bid-detail', strict_slash=True),
		RedirectRoute('/instance/<token>/', labhandlers.InstanceDetailHandler, name='lab-instance-detail', strict_slash=True),

		# clouds, bids and wisps
		RedirectRoute('/clouds/', cloudhandlers.CloudHandler, name='account-clouds', strict_slash=True),
		RedirectRoute('/clouds/<cloud_id>/', cloudhandlers.CloudConfigureHandler, name='account-clouds-configure', strict_slash=True),
		RedirectRoute('/wisps/', wisphandlers.WispHandler, name='account-wisps', strict_slash=True),
		RedirectRoute('/wisps/new/', wisphandlers.WispNewHandler, name='account-wisps-new', strict_slash=True),
		RedirectRoute('/wisps/<wisp_id>/', wisphandlers.WispDetailHandler, name='account-wisps-detail', strict_slash=True),		

		# appliances and groups
		RedirectRoute('/appliances/', appliancehandlers.ApplianceHandler, name='account-appliances', strict_slash=True),
		RedirectRoute('/appliances/new/', appliancehandlers.ApplianceNewHandler, name='account-appliances-new', strict_slash=True),
		RedirectRoute('/appliances/<appliance_id>/', appliancehandlers.ApplianceConfigureHandler, name='account-appliances-configure', strict_slash=True),
		RedirectRoute('/appliances/<appliance_id>/status/', appliancehandlers.ApplianceStatusHandler, name='account-appliances-configure', strict_slash=True),
		RedirectRoute('/groups/', grouphandlers.GroupHandler, name='account-groups', strict_slash=True),
		RedirectRoute('/groups/<group_id>/', grouphandlers.GroupConfigureHandler, name='account-groups-configure', strict_slash=True),
		RedirectRoute('/groups/<group_id>/members/', grouphandlers.GroupMemberHandler, name='account-groups-members', strict_slash=True),
		RedirectRoute('/groups/<group_id>/members/<member_id>/', grouphandlers.GroupMemberConfigureHandler, name='account-groups-members-configure', strict_slash=True),
		RedirectRoute('/invites/', grouphandlers.GroupInviteHandler, name='account-groups-invites', strict_slash=True),

		# api
		RedirectRoute('/api/v1/authorization/', apihandlers.TokenValidate, name='api-token-validate', strict_slash=True),
		RedirectRoute('/api/v1/track/', apihandlers.TrackingPingHandler, name='api-track', strict_slash=True),
		RedirectRoute('/api/v1/images/', apihandlers.ImagesHandler, name='api-images', strict_slash=True),
		RedirectRoute('/api/v1/flavors/', apihandlers.FlavorsHandler, name='api-flavors', strict_slash=True),
		RedirectRoute('/api/v1/instances/', apihandlers.InstancesHandler, name='api-instances', strict_slash=True),
		RedirectRoute('/api/v1/broker/', apihandlers.BrokerHandler, name='api-broker', strict_slash=True),
		RedirectRoute('/api/v1/instances/', apihandlers.InstancesHandler, name='api-instances', strict_slash=True),
		RedirectRoute('/api/v1/instances/<instance_name>/', apihandlers.InstanceDetailHandler, name='api-instance-details', strict_slash=True),
		RedirectRoute('/api/v1/appliances/geopoints/', apihandlers.ApplianceGeoPoints, name='api-appliances-geopoints', strict_slash=True),
		RedirectRoute('/api/v1/bids/', apihandlers.BidsHandler, name='api-bids', strict_slash=True),
		RedirectRoute('/api/v1/bids/<token>/', apihandlers.BidsDetailHandler, name='api-bids-detail', strict_slash=True),
		
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
