from webapp2_extras.routes import RedirectRoute
from web.handlers import sitehandlers, adminhandlers, userhandlers, apihandlers, bloghandlers, emailhandlers, taskhandlers
from web.handlers import projecthandlers, appliancehandlers, grouphandlers, cloudhandlers, wisphandlers, labhandlers

secure_scheme = 'https'

_routes = [
		# website
		RedirectRoute('/', sitehandlers.HomeRequestHandler, name='home', strict_slash=True),
		RedirectRoute('/about/', sitehandlers.AboutHandler, name='about', strict_slash=True),
		RedirectRoute('/sponsor/', sitehandlers.SponsorHandler, name='sponsor', strict_slash=True),
		RedirectRoute('/features/', sitehandlers.FeaturesHandler, name='features', strict_slash=True),
		RedirectRoute('/docs/', sitehandlers.DocsHandler, name='docs', strict_slash=True),
		RedirectRoute('/projects/', projecthandlers.ProjectsHandler, name='projects', strict_slash=True),
		RedirectRoute('/terms/', sitehandlers.TermsHandler, name='terms', strict_slash=True),
		RedirectRoute('/privacy/', sitehandlers.PrivacyHandler, name='privacy', strict_slash=True),
		
		# users
		RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
		RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
		RedirectRoute('/login/complete', userhandlers.CallbackLoginHandler, name='login-complete', strict_slash=True),
		RedirectRoute('/login/tfa', userhandlers.TwoFactorLoginHandler, name='login-tfa', strict_slash=True),
		RedirectRoute('/settings/', userhandlers.SettingsHandler, name='account-settings', strict_slash=True),
		RedirectRoute('/settings/tfa', userhandlers.TwoFactorSettingsHandler, name='account-tfa', strict_slash=True),
		RedirectRoute('/status/', userhandlers.StatusHandler, name='account-status', strict_slash=True),

		# instances
		RedirectRoute('/launcher/', labhandlers.LauncherHandler, name='lab-launcher', strict_slash=True),
		RedirectRoute('/bids/', labhandlers.BidsHandler, name='lab-bids', strict_slash=True),
		RedirectRoute('/bids/<token>/', labhandlers.BidDetailHandler, name='lab-bid-detail', strict_slash=True),
		RedirectRoute('/instances/<token>/', labhandlers.InstanceDetailHandler, name='lab-instance-detail', strict_slash=True),

		# projects
		RedirectRoute('/projects/list/', projecthandlers.ProjectListHandler, name='account-projects', strict_slash=True),
		RedirectRoute('/projects/new/', projecthandlers.ProjectNewHandler, name='account-projects-new', strict_slash=True),
		RedirectRoute('/projects/<project_id>/', projecthandlers.ProjectViewHandler, name='account-projects-view', strict_slash=True),
		RedirectRoute('/projects/bid/<token>/', projecthandlers.ProjectBidHandler, name='account-projects-bid', strict_slash=True),
		RedirectRoute('/projects/<project_id>/edit/', projecthandlers.ProjectEditHandler, name='account-projects-detail', strict_slash=True),
		RedirectRoute('/projects/<project_id>/<action>/', projecthandlers.ProjectMethodHandler, name='account-projects-method', strict_slash=True),

		# clouds
		RedirectRoute('/clouds/list/', cloudhandlers.CloudListHandler, name='account-clouds', strict_slash=True),
		RedirectRoute('/clouds/<cloud_id>/edit/', cloudhandlers.CloudEditHandler, name='account-clouds-configure', strict_slash=True),
		RedirectRoute('/clouds/<cloud_id>/instances/<instance_id>/', cloudhandlers.CloudInstanceHandler, name='clouds-remove-instance', strict_slash=True),
		
		# wisps
		RedirectRoute('/wisps/list/', wisphandlers.WispListHandler, name='account-wisps', strict_slash=True),
		RedirectRoute('/wisps/new/', wisphandlers.WispNewHandler, name='account-wisps-new', strict_slash=True),
		RedirectRoute('/wisps/<wisp_id>/edit/', wisphandlers.WispEditHandler, name='account-wisps-detail', strict_slash=True),		
		RedirectRoute('/wisps/<wisp_id>/<file>', wisphandlers.WispProjectFilesHandler, name='account-wisp-project-files', strict_slash=False),
		
		# appliances
		RedirectRoute('/appliances/list/', appliancehandlers.ApplianceListHandler, name='account-appliances', strict_slash=True),
		RedirectRoute('/appliances/new/', appliancehandlers.ApplianceNewHandler, name='account-appliances-new', strict_slash=True),
		RedirectRoute('/appliances/<appliance_id>/', appliancehandlers.ApplianceViewHandler, name='account-appliances-view', strict_slash=True),
		RedirectRoute('/appliances/<appliance_id>/edit/', appliancehandlers.ApplianceEditHandler, name='account-appliances-configure', strict_slash=True),
		
		# groups
		RedirectRoute('/groups/list/', grouphandlers.GroupListHandler, name='account-groups', strict_slash=True),
		RedirectRoute('/groups/<group_id>/edit/', grouphandlers.GroupEditHandler, name='account-groups-configure', strict_slash=True),
		RedirectRoute('/groups/<group_id>/edit/members/', grouphandlers.GroupMemberHandler, name='account-groups-members', strict_slash=True),
		RedirectRoute('/groups/<group_id>/edit/members/<member_id>/', grouphandlers.GroupMemberEditHandler, name='account-groups-members-configure', strict_slash=True),
		RedirectRoute('/invites/', grouphandlers.GroupInviteHandler, name='account-groups-invites', strict_slash=True),

		# api
		RedirectRoute('/api/v1/authorization/', apihandlers.TokenValidate, name='api-token-validate', strict_slash=True),
		RedirectRoute('/api/v1/track/', apihandlers.TrackingPingHandler, name='api-track', strict_slash=True),
		RedirectRoute('/api/v1/images/', apihandlers.ImagesHandler, name='api-images', strict_slash=True),
		RedirectRoute('/api/v1/flavors/<action:.*>', apihandlers.FlavorsHandler, name='api-flavors', strict_slash=True),
		RedirectRoute('/api/v1/wisp/', apihandlers.WispHandler, name='api-wisp', strict_slash=True),
		RedirectRoute('/api/v1/wisp/<token>/', apihandlers.WispViewHandler, name='api-view-wisp', strict_slash=True),
		RedirectRoute('/api/v1/broker/', apihandlers.BrokerHandler, name='api-broker', strict_slash=True),
		RedirectRoute('/api/v1/instances/', apihandlers.InstancesHandler, name='api-instances', strict_slash=True),
		RedirectRoute('/api/v1/instances/<instance_name>/', apihandlers.InstanceDetailHandler, name='api-instance-details', strict_slash=True),
		RedirectRoute('/api/v1/instances/<token>/', apihandlers.BidsDetailHandler, name='api-bids-detail', strict_slash=True),
		RedirectRoute('/api/v1/appliances/', apihandlers.ApplianceListHandler, name='api-appliances', strict_slash=True),
		RedirectRoute('/api/v1/appliances/geopoints/', apihandlers.ApplianceGeoPoints, name='api-appliances-geopoints', strict_slash=True),
		RedirectRoute('/api/v1/bids/', apihandlers.BidsHandler, name='api-bids', strict_slash=True),
		RedirectRoute('/api/v1/bids/<token>/', apihandlers.BidsDetailHandler, name='api-bids-detail', strict_slash=True),

		# tasks
		RedirectRoute('/tasks/sendinvite/', emailhandlers.SendEmailInviteHandler, name='tasks-sendinvite', strict_slash=True),
		RedirectRoute('/tasks/instances/', taskhandlers.InstancesHandler, name='tasks-instances', strict_slash=True),
		RedirectRoute('/tasks/instancebids/', taskhandlers.InstanceBidsHandler, name='tasks-instancebids', strict_slash=True),
		RedirectRoute('/tasks/appliances/', taskhandlers.AppliancesHandler, name='tasks-appliances', strict_slash=True),
		RedirectRoute('/tasks/wisps/', taskhandlers.AnonymousWispHandler, name='tasks-anonymous-wisps', strict_slash=True),
	    RedirectRoute('/tasks/mail/', sitehandlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

		# admin
		RedirectRoute('/admin/', adminhandlers.AdminHandler, name='admin', strict_slash=True),
		RedirectRoute('/admin/users/', adminhandlers.UsersHandler, name='admin-users', strict_slash=True),
		RedirectRoute('/admin/users/export/', adminhandlers.UsersExportHandler, name='admin-users-export', strict_slash=True),
		RedirectRoute('/admin/flavors/', adminhandlers.FlavorsListHandler, name='admin-flavors', strict_slash=True),
		RedirectRoute('/admin/flavors/<flavor_id>/', adminhandlers.FlavorsActionsHandler, name='admin-flavors-action', strict_slash=True),
		RedirectRoute('/admin/images/', adminhandlers.ImagesListHandler, name='admin-images', strict_slash=True),
		RedirectRoute('/admin/images/<image_id>/', adminhandlers.ImagesActionsHandler, name='admin-images-action', strict_slash=True),
		RedirectRoute('/admin/groups/', adminhandlers.GroupsHandler, name='admin-groups', strict_slash=True),

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
