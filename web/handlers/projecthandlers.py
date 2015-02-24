import time
import json
import re
import urllib2
import bleach
import html5lib
import webapp2

from lib import markdown

from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.api import urlfetch

from lib.github import github

import config

import web.forms as forms
from web.models.models import User, Project, Image, Instance, Appliance, Group, Flavor, Wisp, InstanceBid
from web.basehandler import BaseHandler
from web.basehandler import user_required


# user list of managed projects
class ProjectListHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up projects
		projects = Project.get_by_user(user_info.key)

		# redirect if we don't have any projects
		if not projects:
			return self.redirect_to('account-projects-new')

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'projects': projects,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('project/list.html', **params)

# handle new projects
class ProjectNewHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# check for url param or referer
		url = ""
		if 'url' in self.request.GET:
			url = urllib2.unquote(self.request.GET['url'])

		# if we have a URL, we deal with it
		if url:
			project = Project.get_by_url(url)
			if not project:
				# create a new project for this user
				self.form.url.data = url
				return self.post()
			else:
				# go to the existing project
				return self.redirect_to('account-projects-detail', project_id = project.key.id())

		# params build out
		params = {
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('project/new.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# check what was returned from form validates     
		if not self.form.validate():
			for key, value in self.form.errors.iteritems():
				self.add_message("Fix the %s. %s" % (key, value[0]), "error")
			return self.get()

		# load form values
		url = self.form.url.data.strip()
		
		# check if we have it already
		if Project.get_by_url(url):
			self.add_message("A project with that URL already exists.", "error")
			return self.redirect_to('account-projects')		

		# get the basic repo data
		response = github.repo_base(url)
		if response['response'] == 'success':
			repo = response['result']['repo']
		else:
			repo = None
			self.add_message(response['result']['message'], 'error')
			return self.redirect_to('projects')

		# save the new project in our database
		project = Project()           
		project.url = url.lower().strip('/')
		project.name = repo['name'] # this one is editable later
		project.repo_name = repo['name'] # this one is not
		project.address = None
		project.amount = 0
		project.description = repo['description']
		project.owner = user_info.key
		project.public = False
		project.port = 80
		project.put()

		# give it a second
		time.sleep(1)

		# check if the repo has the utterio directory
		response = project.sync()

		# log to alert
		if response['response'] == "success":
			self.add_message("Project %s successfully added!" % project.name, "success")
		else:
			self.add_message("%s" % response['result']['message'], "fail")

		# redirect
		return self.redirect_to('account-projects-detail', project_id = project.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.NewProjectForm(self)


# provide editing for projects		
class ProjectEditHandler(BaseHandler):
	@user_required
	def get(self, project_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# get the project in question
		project = Project.get_by_id(long(project_id))

		# bail if project doesn't exist or not owned by this user
		if not project or project.owner != user_info.key:
			return self.redirect_to('account-projects')

		# load form values
		self.form.name.data = project.name
		self.form.description.data = project.description
		self.form.address.data = project.address
		self.form.amount.data = project.amount
		self.form.vpus.data = project.vpus
		self.form.memory.data = project.memory
		self.form.disk.data = project.disk
		self.form.port.data = project.port
		self.form.dynamic_image_url.data = project.dynamic_image_url

		# insert images into list
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'project': project,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('project/edit.html', **params)
	
	@user_required
	def post(self, project_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# load the project in question
		project = Project.get_by_id(long(project_id))
		
		# bail if project doesn't exist or not owned by this user
		if not project or project.owner != user_info.key:
			return self.redirect_to('account-projects')

		# insert images into list for wisp
		self.form.image.choices=[('custom', "Dynamic Image URL")]
		images = Image.get_all()
		for image in images:
			self.form.image.choices.insert(0, (str(image.key.id()), image.description))

		# check what was returned from form validates
		if not self.form.validate():
			for key, value in self.form.errors.iteritems():
				self.add_message("Fix the %s. %s." % (key, value[0].strip('. ')), "error")

		# stuff to set that might have errors
		if not self.form.name.errors:
			name = self.form.name.data.strip()
			project.name = name
		if not self.form.description.errors:
			description = self.form.description.data.strip()
			project.description = description
		if not self.form.address.errors:
			address = self.form.address.data.strip()
			project.address = address
		if not self.form.amount.errors:
			amount = self.form.amount.data
			project.amount = int(amount)
		if not self.form.dynamic_image_url.errors:
			dynamic_image_url = self.form.dynamic_image_url.data.strip()
			project.dynamic_image_url = dynamic_image_url

		# handle a custom image setting
		if self.form.image.data.strip() == "custom":
			image = None
		else:
			image = Image.get_by_id(int(self.form.image.data.strip())).key
		project.image = image

		# pulldowns (no errors)
		vpus = self.form.vpus.data
		project.vpus = int(vpus)
		memory = self.form.memory.data
		project.memory = int(memory)
		disk = self.form.disk.data
		project.disk = int(disk)
		image = self.form.image.data
		port = self.form.port.data

		# save the new project in our database
		project.put()

		# log to alert
		self.add_message("Project %s updated!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		
		return self.get(project_id = project.key.id())

	def delete(self, project_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# pull the entry from the db
		project = Project.get_by_id(long(project_id))

		# if we found it and own it
		if project and project.owner == user_info.key:
			# patch all wisps using project to stock
			Wisp.patch_to_stock(project.key)

			# delete the project
			project.key.delete()

			self.add_message('Project successfully deleted!', 'success')
		else:
			self.add_message('Project was not deleted.  Something went horribly wrong somewhere!', 'warning')

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	@webapp2.cached_property
	def form(self):
		return forms.ProjectForm(self)

# provide editing for projects		
class ProjectMethodHandler(BaseHandler):
	@user_required
	def get(self, project_id = None, action = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# load the project in question
		project = Project.get_by_id(long(project_id))

		# deny if not owner
		if project.owner != user_info.key:
			return

		# refresh
		if action == 'refresh':
			# sync if project exists and the user is owner
			if project and project.owner == user_info.key:
				response = project.sync()
				time.sleep(1)

			# log to alert
			if response['response'] == "success":
				self.add_message("Project %s successfully synced!" % project.name, "success")
			else:
				self.add_message("%s" % response['result']['message'], "fail")

		# publish status
		if action == 'private':
			project.public = False
			project.put()
		if action == 'public':
			project.public = True
			project.put()

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return


# returns list of public projects or auto-navigates to project if coming from github
class ProjectsHandler(BaseHandler):
	def get(self):
		# check for referer (only works SSL to SSL site) or parameter in URL (for custom page)
		url = ""
		if 'url' in self.request.GET:
			url = urllib2.unquote(self.request.GET['url'])
		elif self.request.referer:
			if config.github_url in self.request.referer:
				url = urllib2.unquote(self.request.referer)

		# lowercase url and strip slashes
		url = url.lower().strip('/')

		# run regex to get base URL
		match = re.search('https://github.com/([\w]*)/([\w]*)', url)
		if match:
			# pull out the match
			url = match.group()

			# if we have a URL, we look it up
			if url:
				project = Project.get_by_url(url)

				if project:
					# go to the existing project
					return self.redirect_to('account-projects-view', project_id = project.key.id())
				else:
					# if user is logged in, redirect to the new page
					if self.user_id:
						params = {'url': url}
						return self.redirect_to('account-projects-new', **params)

		# load all public projects
		projects = Project.get_public()

		# params build out
		params = {
			'projects': projects
		}

		return self.render_template('site/projects.html', **params)


# provides launches for projects
class ProjectViewHandler(BaseHandler):
	def get(self, project_id = None):
		project = Project.get_by_id(long(project_id))
		# if no project
		if not project:
			return self.redirect_to('projects')

		# assume this user is not owner
		owner = False

		# print self.render_url(project.json_url, {})

		# determine if we can show the project
		if not project.public:
			# see if we have a user
			try:
				user_info = User.get_by_id(long(self.user_id))
				if user_info.key != project.owner:
					raise Exception
				else:
					owner = True

			except:
				self.add_message("You must be the owner to do this.", "fail")
				return self.redirect_to('projects')
		else:
			try:
				user_info = User.get_by_id(long(self.user_id))
				if user_info.key == project.owner:
					owner = True

			except:
				user_info = None

		# define minimum specifications for the instance
		specs = {
			'vpus': project.vpus,
			'memory': project.memory,
			'disk': project.disk
		}

		# empty forms
		self.form.provider.choices = []
		self.form.flavor.choices = []

		# plenty?
		plenty = False

		# dict of providers
		providers = {}

		# find the all public provider's appliances and add to providers object
		appliances = Appliance.get_by_group(None)
		for appliance in appliances:
			providers[appliance.key.id()] = {
				'name': "%s (Public)" % appliance.name,
				'location': [appliance.location.lat, appliance.location.lon],
				'flavors': []
			}

		# if there is a user, find his groups and do the same with appliances in those groups
		if user_info:
			groups = Group.get_by_owner(user_info.key)
			for group in groups:
				appliances = Appliance.get_by_group(group.key)
				for appliance in appliances:
					providers[str(appliance.key.id())] = {
						'name': "%s of %s (Hybrid Group)" % (appliance.name, group.name),
						'location': [appliance.location.lat, appliance.location.lon],
						'flavors': []
					}

		# iterate over the dictionary of providers
		for provider in providers:
			# find the list of flavors for this provider which support this project
			flavors = Flavor.flavors_with_min_specs_by_appliance_on_sale(
				specs, 
				ndb.Key('Appliance', long(provider))
			)

			# add provider to the form and the flavors to provider object if flavors exist
			if flavors:
				plenty = True
				# insert this provider's appliance into the form
				self.form.provider.choices.insert(0, (provider, providers[provider]['name']))

				# insert flavors into object
				for flavor in flavors:
					providers[provider]['flavors'].append(
						{
							'id': str(flavor.key.id()),
							'name': flavor.name,
							'description': flavor.description
						}
					)

		# setup channel to do page refresh
		channel_token = 'changeme'
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'project': project,
			'providers': json.dumps(providers),
			'plenty': plenty,
			'owner': owner,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('project/view.html', **params)

	@webapp2.cached_property
	def form(self):
		return forms.LaunchProjectForm(self)


class ProjectBidHandler(BaseHandler):
	def get(self, token = None):
		# lookup up bid
		bid = InstanceBid.get_by_token(token)
		if not bid:
			self.add_message("Instance reservation token %s has expired." % token, 'error')
			return self.redirect_to('projects')

		# grab the project from the bid
		project = Project.get_by_id(bid.wisp.get().project.id())

		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("All available instance reservations are in use. Please try again in a few minutes.", 'error')
			return self.redirect_to('projects')

		# grab and render the README.md file
		content = urlfetch.fetch('http://10.0.1.80:8079/wisps/6048757061779456/README.md').content

		readme_html = bleach.clean(
			markdown.markdown(
				unicode(content, 'utf-8')
			), 
			config.bleach_tags,
			config.bleach_attributes
		)	

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		params = {
			'instance': instance,
			'bid': bid,
			'project': project,
			'readme_html': readme_html,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('project/bid.html', **params)


class DemosInstanceHandler(BaseHandler):
	def get(self, demo_name = None, token = None):
		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("That instance cannot be found.", 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		# hack in time max for timer
		instance.data_max = int(instance.expires - int(instance.started.strftime('%s')))

		# dict the meta
		if instance.meta:
			instance.meta_dict = json.loads(instance.meta)
		else:
			instance.meta_dict = {}

		params = {
			'instance': instance,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('site/demos/%s_instance.html' % demo_name, **params)


