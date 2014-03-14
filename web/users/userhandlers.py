import os
import logging

import urllib
import urllib2
import httplib2
import hashlib
import json

from datetime import datetime
from StringIO import StringIO

import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.appengine.auth.models import Unique

from google.appengine.api import taskqueue
from google.appengine.api import users

import config
import web.forms as forms
from web.models.models import User
from web.models.models import LogVisit
from web.basehandler import BaseHandler
from web.basehandler import user_required
from lib import utils, httpagentparser
from lib import pyotp

# user logout
class LogoutHandler(BaseHandler):

    def get(self):
        if self.user:
            message = "You have been logged out."
            self.add_message(message, 'info')

        self.auth.unset_session()
        self.redirect_to('home')


# user login w/google
class LoginHandler(BaseHandler):
    
    def get(self):
        callback_url = "%s/login/complete" % (self.request.host_url)
        continue_url = self.request.get('continue_url')
        
        if continue_url:
            dest_url=self.uri_for('login-complete', continue_url=continue_url)
        else:
            dest_url=self.uri_for('login-complete')
        
        try:
            login_url = users.create_login_url(federated_identity='gmail.com', dest_url=dest_url)
            self.redirect(login_url)
        except users.NotAllowedError:
            self.add_message("The pool operator must enable Federated Login for this application before you can login.", "error")
            self.redirect_to('login')


# google auth callback
class CallbackLoginHandler(BaseHandler):

    def get(self):
        # get info from Google login
        current_user = users.get_current_user()

        # handle old and new users
        try:
            uid = current_user.user_id()

            # see if user is in database
            user = User.get_by_uid(uid)

            # create association if user doesn't exist
            if user is None:
                user = User(
                    last_login = datetime.now(),
                    uid = str(uid),
                    username = current_user.email().split("@")[0],
                    email = current_user.email(),
                    activated = True
                )
                user.put()
                log_message = "new user registered"

            else:
                user.last_login = datetime.now()
                user.put()
                log_message = "user login"

            # set the user's session
            self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
            
            # log visit
            log = LogVisit(
                user = user.key,
                message = log_message,
                uastring = self.request.user_agent,
                ip = self.request.remote_addr
            )
            log.put()

            # take user to the account page
            return self.redirect_to('account')

        except:
            message = "No user authentication information received from Google."            
            self.add_message(message, 'error')
            return self.redirect_to('home')


class AccountHandler(BaseHandler):
    @user_required
    def get(self):
        current_user = users.get_current_user()
        uid = current_user.user_id()
        user = User.get_by_uid(uid)

        # force user to setup 2FA
        if user.tfenabled == False:
            pass
            # return self.redirect_to('account-twofactor')
        params = {}
        return self.render_template('user/dash.html', **params)


class TwoFactorHandler(BaseHandler):
    @user_required
    def get(self):
        current_user = users.get_current_user()
        uid = current_user.user_id()
        user = User.get_by_uid(uid)
        
        # force user to setup 2FA
        if user.tfenabled == False:
            key = pyotp.random_base32()
            
            # update the user's key
            user.tfkey = key
            user.put()

            code = pyotp.TOTP()
        steve = pyotp.random_base32()
        t = pyotp.TOTP(steve)
        qrcode = t.provisioning_uri(user.email)

        pass

class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {}

        if self.user:
            logging.info("logged in")
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            self.form.last_name.data = user_info.last_name
            self.form.country.data = user_info.country
            providers_info = user_info.get_social_providers_info()
            params['used_providers'] = providers_info['used']
            params['unused_providers'] = providers_info['unused']
            params['country'] = user_info.country
            params['company'] = user_info.company

        return self.render_template('user/edit_profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        country = self.form.country.data

        try:
            user_info = models.User.get_by_id(long(self.user_id))

            try:
                message=''
                # update username if it has changed and it isn't already taken
                if username != user_info.username:
                    user_info.unique_properties = ['username','email']
                    uniques = [
                               'User.username:%s' % username,
                               'User.auth_id:own:%s' % username,
                               ]
                    # Create the unique username and auth_id.
                    success, existing = Unique.create_multi(uniques)
                    if success:
                        # free old uniques
                        Unique.delete_multi(['User.username:%s' % user_info.username, 'User.auth_id:own:%s' % user_info.username])
                        # The unique values were created, so we can save the user.
                        user_info.username=username
                        user_info.auth_ids[0]='own:%s' % username
                        message+= 'Your new username is %s' % '<strong>{0:>s}</strong>'.format(username)

                    else:
                        message+= 'The username %s is already taken. Please choose another.' \
                                % '<strong>{0:>s}</strong>'.format(username)
                        # At least one of the values is not unique.
                        self.add_message(message, 'error')
                        return self.get()
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                message+= " " + 'Your settings have been saved.  You may now dance.'
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating profile: ' + e)
                message = 'Unable to update profile. Please try again later.'
                self.add_message(message, 'error')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = 'Sorry you are not logged in.'
            self.add_message(login_error_message, 'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditProfileForm(self)


