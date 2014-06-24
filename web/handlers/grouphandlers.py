import time

import webapp2

from google.appengine.api import channel

import config
import web.forms as forms
from web.models.models import User, Appliance, Group, GroupMembers
from web.basehandler import BaseHandler
from web.basehandler import user_required

class GroupHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up user's groups
		groups = GroupMembers.get_user_groups(user_info.key)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'groups': groups,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/groups.html', **params)

	@user_required
	def post(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# check if we have it already
		if Group.get_by_name(name):
			self.add_message("A group with that name already exists!", "error")
			return self.redirect_to('account-groups')

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The new group form did not validate.", "error")
			return self.get()

		# create the group
		group = Group(
			name = name,
			description = description,
			owner = user_info.key,
		)
		group.put()

		# create the group member entry
		groupmember = GroupMembers(
			group = group.key,
			member = user_info.key,
			invitor = user_info.key, # same same
			active = True
		)
		groupmember.put()
		
		# log to alert
		self.add_message("Group %s successfully created!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		return self.redirect_to('account-groups-configure', group_id = group.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.GroupForm(self)

class GroupConfigureHandler(BaseHandler):
	@user_required
	def get(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the cloud in question
		group = Group.get_by_id(long(group_id))

		# scan for this user
		is_member = GroupMembers.is_member(user_info.key, group.key)

		# bail if cloud doesn't exist user isn't in the membership list
		if not group or not is_member:
			return self.redirect_to('account-groups')

		# get the members
		members = GroupMembers.get_group_users(group.key)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'group': group,
			'members': members,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/group_manage.html', **params)

	@user_required
	def post(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the cloud in question
		group = Group.get_by_id(long(group_id))

		# bail if cloud doesn't exist user isn't in the membership list
		if not group or group.owner != user_info.key:
			return self.redirect_to('account-groups')

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The %s group was not updated." % group.name, "info")
			return self.redirect_to('account-groups')

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# save the new group            
		group.name = name
		group.description = description
		group.put()

		# log to alert
		self.add_message("Group %s updated!" % name, "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		
		return self.redirect_to('account-groups')

	@user_required
	def delete(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# find the the entry
		group = Group.get_by_id(long(group_id))

		# this member's membership
		membership = GroupMembers.get_by_userid_groupid(user_info.key, group.key)

		# bail if group doesn't exist or not owned by this user
		if not group or group.owner != user_info.key:
			self.add_message('Group was not deleted.', 'warning')
			return self.redirect_to('account-groups')

		# list of users that have the group enabled
		members = GroupMembers.get_group_users(group.key)

		# delete the groupmember's entry (members still contains result)
		membership.key.delete()

		# was there more than just this member?
		if len(members) > 1:
			# find the next user by date and assign them as owner
			pass # TODO
		else:
			# no more members, so delete the group
			group.key.delete()
			self.add_message('Group successfully deleted!', 'success')

			# remove group from appliances
			appliances = Appliance.get_by_group(group.key)
			for appliance in appliances:
				appliance.group = None # public group
				appliance.put()

		# hangout for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	@webapp2.cached_property
	def form(self):
		return forms.GroupForm(self)