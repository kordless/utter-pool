import time
import json

import webapp2

from google.appengine.api import channel

from lib.github import github

import config

import web.forms as forms
from web.models.models import User, Project, Image
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
			url = self.request.GET['url']
		elif self.request.referer:
			if config.github_url in self.request.referer:
				url = self.request.referer

		# if we have a URL, we deal with it
		if url:
			project = App.get_by_user_url(user_info.key, url)
			if not project:
				# create a new project for this user
				self.form.url.data = url
				return self.post()
			else:
				# go to the existing project
				return self.redirect_to('account-project-detail', project_id = project.key.id())

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
		if Project.get_by_user_url(user_info.key, url):
			self.add_message("A project with that URL already exists.", "error")
			return self.redirect_to('account-projects')		

		# get the basic repo data
		response = github.repo_base(url)
		if response['response'] == 'success':
			repo = response['result']['repo']
		else:
			self.add_message(response['result']['message'], 'error')

		# save the new project in our database
		project = Project()           
		project.url = url
		project.name = repo['name'] # this one is editable later
		project.repo_name = repo['name'] # this one is not
		project.address = None
		project.amount = 0
		project.description = repo['description']
		project.owner = user_info.key
		project.public = False
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
class ProjectDetailHandler(BaseHandler):
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
		self.form.mem.data = project.mem
		self.form.disk.data = project.disk
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

		return self.render_template('project/manage.html', **params)
	
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
		mem = self.form.mem.data
		project.mem = int(mem)
		disk = self.form.disk.data
		project.disk = int(disk)
		image = self.form.image.data

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

		# if we found it and own it, delete
		if project and project.owner == user_info.key:
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

"""
Old methods for showing demo bid launches

class DemosBidHandler(BaseHandler):
	def get(self, demo_name = None, token = None):
		# lookup up bid
		bid = InstanceBid.get_by_token(token)
		if not bid:
			self.add_message("Instance reservation token %s has expired." % token, 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# grab the instance
		instance = Instance.get_by_token(token)
		if not instance:
			self.add_message("All available instance reservations are in use. Please try again in a few minutes.", 'error')
			return self.redirect_to('demos', demo_name=demo_name)

		# setup channel to do page refresh
		channel_token = token
		refresh_channel = channel.create_channel(channel_token)

		params = {
			'instance': instance,
			'bid': bid,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('site/demos/%s_bid.html' % demo_name, **params)


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

"""
