import time
from datetime import datetime

import webapp2

from google.appengine.api import channel
from google.appengine.api import taskqueue

import config
import web.forms as forms
from web.models.models import User, Appliance, Group, GroupMembers
from web.basehandler import BaseHandler
from web.basehandler import user_required

class GroupListHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# look up user's groups
		groups = GroupMembers.get_user_groups(user_info.key)

		# create an object with group_id and member counts
		group_count = {}
		for group in groups:
			# get the member counts
			count = GroupMembers.get_group_user_count(group.key)
			group_count[group.key.id()] = count

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out
		params = {
			'groups': groups,
			'group_count': group_count,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/list.html', **params)

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

# http://example.com/groups/5645717330722816/edit/
class GroupEditHandler(BaseHandler):
	@user_required
	def get(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the group in question
		group = Group.get_by_id(long(group_id))

		# scan if this user is a member and/or admin
		if group.owner == user_info.key:
			is_admin = True
			is_member = True # obvious
		else:
			is_admin = False
			is_member = GroupMembers.is_member(user_info.key, group.key)

		# bail if group doesn't exist or user isn't in the membership list
		if not group or not is_member:
			return self.redirect_to('account-groups')

		# get the members
		members = GroupMembers.get_group_users(group.key)

		# create an object with appliance counts per user
		appliance_count = {}
		for member in members:
			# get the appliance counts per user for this group
			count = Appliance.get_appliance_count_by_user_group(member.key, group.key)
			appliance_count[member.key.id()] = count

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)

		# params build out - ugly cause instructions/admin stuff
		params = {
			'is_admin': is_admin,
			'is_member': is_member,
			'group': group,
			'members': members,
			'appliance_count': appliance_count,
			'num_members': len(members),
			'gmform': self.gmform,
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}

		return self.render_template('groups/edit.html', **params)

	@user_required
	def post(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the group in question
		group = Group.get_by_id(long(group_id))

		# bail if group doesn't exist user isn't the owner/admin
		if not group or group.owner != user_info.key:
			return self.redirect_to('account-groups')

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The %s group was not updated." % group.name, "info")
			return self.redirect_to('account-groups')

		# load form values
		name = self.form.name.data.strip()
		description = self.form.description.data.strip()

		# check if we have a group named that already
		if Group.get_by_name(name):
			self.add_message("A group with that name already exists!", "error")
			return self.redirect_to('account-groups')
			
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

		# list of users that have the group enabled
		members = GroupMembers.get_group_users(group.key)

		# remove this user's membership
		membership.key.delete()
		
		# if this user is not the group owner, we simply notify we are done
		if not group or group.owner != user_info.key:
			# use the channel to tell the browser we are done and reload
			self.add_message('Group was removed from account.', 'success')
			channel_token = self.request.get('channel_token')
			channel.send_message(channel_token, 'reload')
			return

		# was there more than just this member?
		if len(members) > 1:
			# find the next user by date and assign them as owner
			entry = GroupMembers.get_new_owner(user_info.key, group.key)
			print "new owner is %s" % entry.member
			new_owner = entry.member
			group.owner = new_owner
			group.put()
		
			# find member's appliances that match this group and remove
			appliances = Appliance.get_by_user_group(user_info.key, group.key)
			for appliance in appliances:
				appliance.group = None # public group
				appliance.put()
		
		else:
			# no more members, so delete the group
			group.key.delete()
			self.add_message('Group successfully deleted!', 'success')

			# remove group from any and all appliances (heavy handed)
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

	@webapp2.cached_property
	def gmform(self):
		return forms.GroupMemberForm(self)

# email an invite to the group
# http://example.com/groups/5645717330722816/members/
class GroupMemberHandler(BaseHandler):
	@user_required
	def post(self, group_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the group in question
		group = Group.get_by_id(long(group_id))

		# get this user's membership
		is_member	= GroupMembers.is_member(user_info.key, group.key)

		# bail if group doesn't exist or user not a member
		if not group or not is_member:
			return self.redirect_to('account-groups')

		# check what was returned from form validates
		if not self.form.validate():          
			self.add_message("The email form did not validate.", "error")
			return self.redirect_to('account-groups-configure', group_id = group.key.id())

		# load form values
		email = self.form.email.data.strip()

		# create the invite
		member = GroupMembers.invite(email, group.key, user_info.key)
		
		time.sleep(1)

		# build an invite URL, load the email_url, and then execute the task to send invite
		invite_url = "%s%s?token=%s" % (self.request.host_url, self.uri_for('account-groups-invites'), member.token)
		email_url = self.uri_for('tasks-sendinvite')
		taskqueue.add(url = email_url, params={
				'to': str(email),
				'group_id': group.key.id(),
				'invitor_id' : user_info.key.id(),
				'invite_url' : invite_url
		})

		# log to alert
		self.add_message("User invited to group!", "success")
		
		return self.redirect_to('account-groups-configure', group_id = group.key.id())

	@webapp2.cached_property
	def form(self):
		return forms.GroupMemberForm(self)

# handle removal of users from the group
# http://example.com/groups/5645717330722816/members/6428569609699328/
class GroupMemberEditHandler(BaseHandler):
	@user_required
	def delete(self, group_id = None, member_id = None):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))
		
		# get the group in question
		group = Group.get_by_id(long(group_id))
		member = User.get_by_id(long(member_id))

		# get this user's admin rights
		is_admin = False
		if group.owner == user_info.key:
			is_admin = True

		# bail if group doesn't exist or user is not admin
		if not group or not is_admin:
			# log to alert
			self.add_message("You may not remove this user from group.", "error")
		else:	
			# look up the other user's group membership
			membership = GroupMembers.get_by_userid_groupid(member.key, group.key)

			# kill the membership
			membership.key.delete()

			# find member's appliances that match that group and remove
			appliances = Appliance.get_by_user_group(member.key, group.key)
			for appliance in appliances:
				appliance.group = None # public group
				appliance.put()

			# log to alert
			self.add_message("User removed from group!", "success")
			
		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return


# handle the invite request from the emailed URL
# http://example.com/invites/?token=aixv62utat0bi3gt
class GroupInviteHandler(BaseHandler):
	@user_required
	def get(self):
		# lookup user's auth info
		user_info = User.get_by_id(long(self.user_id))

		# load token and produce form page or show instructions
		if self.request.get('token'):
			invite_token = self.request.get('token')
		else:
			self.add_message("Invite key not found.", "info")
			return self.redirect_to('account-groups')
		
		# lookup the invite
		invite = GroupMembers.get_by_token(invite_token)

		if not invite:
			# log to alert
			self.add_message("Invite key not found.", "info")
			return self.redirect_to('account-groups')

		# check if the user is already a member of the group
		entry = GroupMembers.get_by_userid_groupid(user_info.key, invite.group.get().key)

		if entry:
			# log to alert
			self.add_message("You are already a member of this group!", "info")
		else:
			# modify the invite to place this user in the member group
			invite.token = None
			invite.active = True
			invite.member = user_info.key
			invite.updated = datetime.now()
			invite.put()

			# log to alert
			self.add_message("Welcome to the group!", "success")

		# give it a few seconds to update db, then redirect
		time.sleep(1)
		
		return self.redirect_to('account-groups-configure', group_id = invite.group.get().key.id())






























# hello you.
# why no tests?  because I am alone.
# fuck tests then.
# time is short.
# life is shorter.
# but.
# time passed.
# you are here now.
# because insane funding.
# come to my office.
# i may be taking a nap.
# but.
# i'm going to give you $5K for finding this.
# there is always a catch, isn't there?
# going make you write tests tomorrow!