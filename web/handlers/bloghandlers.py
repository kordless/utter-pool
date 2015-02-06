import os
import logging
import time
import datetime

import md5
import re
import urllib
import urllib2
import httplib2
import hashlib
import json

import bleach
import html5lib

from lib import markdown

from google.appengine.api import taskqueue
from google.appengine.api import channel
from google.appengine.ext import db

import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique

import config
import web.forms as forms
import web.models.models as models
from web.basehandler import BaseHandler
from web.basehandler import user_required, blogger_required
from lib import utils, httpagentparser


class BlogHandler(BaseHandler):
	def get(self):
		# load articles in from db and then stuff them in an array
		date_format = "%A, %d %b %Y"
		articles = models.Article.get_all()
		
		# http connection start
		http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
		
		blogposts = []

		# loop through articles
		for article in articles:
			# fetch the content from ourselves		
			uri = "http://%s/assets/blog/%s" % (self.request.host, article.filename)
			response, content = http.request(uri, method="GET", body=None, headers=None)

			if content:
				# create markdown and sanitize
				article_html = bleach.clean(markdown.markdown(unicode(content, 'utf-8')), config.bleach_tags, config.bleach_attributes)
				article_title = bleach.clean(article.title)

				# created when and by whom
				article_created = article.created.strftime(date_format)
				owner_info = models.User.get_by_id(article.owner.id())
				
				# load name
				try:
					if not owner_info.name:
						article_owner = owner_info.username
					else:
						article_owner = owner_info.name
				except:
						article_owner = "StackMonkey"

				# build gravatar URL
				try:
					gravatar_hash = md5.new(owner_info.email.lower().strip()).hexdigest()
				except:
					gravatar_hash = md5.new(config.app_email.strip()).hexdigest()
				article_gravatar_url = "https://www.gravatar.com/avatar/%s?s=100" % gravatar_hash

				# build entry
				entry = {
					'article_created': article_created,
					'article_id': article.key.id(),
					'article_title': article_title,
					'article_type': article.article_type, 
					'article_html': article_html,
					'article_slug': article.slug,
					'article_owner': article_owner,
					'article_gravatar_url': article_gravatar_url,
					'article_host': self.request.host,
				}
				
				# append article if it's a post and not a draft            
				if article.article_type == 'post' and not article.draft:
					blogposts.append(entry)
		
		# pack and stuff into template
		params = {'blogposts': blogposts}
		return self.render_template('blog/blog.html', **params)


# TODO: needs to be fixed to guarantee 10 items get spit out
class RSSHandler(BaseHandler):
	 def get(self):
		# load articles in from db and github, stuff them in an array
		date_format = "%a, %d %b %Y"

		blog_title = "The %s Blog" % config.app_name
		epoch_start = datetime.datetime(1970, 1, 1)
		blog_last_updated = epoch_start

		entries = []
		
		# fetch our articles
		articles = models.Article.get_all()
		
		for article in articles[0:10]:
			gist_content = github.get_gist_content(article.gist_id)

			if gist_content:
				# sanitize
				article_html = bleach.clean(gist_content, config.bleach_tags, config.bleach_attributes)
				article_title = bleach.clean(article.title)
				article_summary = bleach.clean(article.summary)

				# look up owner
				owner_info = models.User.get_by_id(article.owner.id())

				if article.updated > blog_last_updated:
					blog_last_updated = article.updated
				entry = {
					'slug': article.slug,
					'article_type': article.article_type,
					'created': article.created,
					'author_email': owner_info.email,
					'author_username': owner_info.username,
					'updated': article.updated,
					'title': article_title, 
					'summary': article_summary, 
					'html': article_html,
				}

				if not article.draft:
					entries.append(entry)

		# didn't get any matches in our loop
		date_format = "%a, %d %b %Y %H:%M:%S GMT"
		if blog_last_updated == epoch_start:
			blog_last_updated = datetime.datetime.utcnow().strftime(date_format) 
		else:
			blog_last_updated = blog_last_updated.strftime(date_format)

		params = {
			'blog_title': blog_title, 
			'blog_last_updated': blog_last_updated,
			'site_host': self.request.host,
			'entries': entries,
		}
		
		self.response.headers['Content-Type'] = 'application/xml'
		return self.render_template('blog/feed.xml', **params)


class ListHandler(BaseHandler):
	@user_required
	@blogger_required
	def get(self):
		# grab the user
		user_info = models.User.get_by_id(long(self.user_id))

		# look up user's articles
		articles = models.Article.get_by_user(user_info.key)

		# setup channel to do page refresh
		channel_token = user_info.key.urlsafe()
		refresh_channel = channel.create_channel(channel_token)
		params = {
			'articles': articles, 
			'refresh_channel': refresh_channel,
			'channel_token': channel_token 
		}
		return self.render_template('blog/manage.html', **params)

	@user_required
	@blogger_required
	def post(self):
		if not self.form.validate():          
			self.add_message("The form did not validate.", 'error')
			return self.get()

		# who's blogging this shizzle?
		user_info = models.User.get_by_id(long(self.user_id))
	
		# load values out of the form
		title = self.form.title.data.strip()
		summary = self.form.summary.data.strip()
		filename = self.form.filename.data.strip()
		article_type = self.form.article_type.data.strip()
		
		# when written?
		published_epoch_gmt = int(datetime.datetime.now().strftime("%s"))

		# prep the slug
		slug = utils.slugify(title)
		
		# save the article in our database            
		article = models.Article(
			title = title,
			summary = summary,
			created = datetime.datetime.fromtimestamp(published_epoch_gmt),
			filename = filename,
			owner = user_info.key,
			slug = slug,
			article_type = article_type,
		)
		article.put()

		# log to alert
		self.add_message(_('Article %s successfully created!' % title), 'success')

		# give it a few seconds to update db, then redirect
		time.sleep(2)
		return self.redirect_to('blog-article-list')


	@webapp2.cached_property
	def form(self):
		return forms.BlogArticleForm(self)


class ActionsHandler(BaseHandler):
	@user_required
	@blogger_required
	def delete(self, article_id = None):
		# delete the entry from the db
		article = models.Article.get_by_id(long(article_id))

		if article:
			article.key.delete()
			self.add_message(_('Article successfully deleted!'), 'success')
		else:
			self.add_message(_('Article was not deleted.  Something went horribly wrong somewhere!'), 'warning')

		# hang out for a second
		time.sleep(1)

		# use the channel to tell the browser we are done and reload
		channel_token = self.request.get('channel_token')
		channel.send_message(channel_token, 'reload')
		return

	# deal with draft or published status changes from slider
	@user_required
	@blogger_required
	def put(self, article_id = None):
		# slider returns 'true' for published and 'false' for draft
		draft = self.request.get('draft')

		if draft == 'false':
			draft = False
		else:
			draft = True

		# update the entry
		article = models.Article.get_by_id(long(article_id))
		if article:
			article.draft = draft
			article.put()

		return


class SlugHandler(BaseHandler):
	def get(self, slug = None):
		# look up the article
		article = models.Article.get_by_slug(slug)
		if not article:
			return self.render_template('errors/default_error.html')

		# fetch the content from ourselves		
		http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
		uri = "http://%s/assets/blog/%s" % (self.request.host, article.filename)
		response, content = http.request(uri, method="GET", body=None, headers=None)

		# if the article wasn't found
		if response['status'] == '404':
			return self.render_template('errors/default_error.html')

		# fetch the user's info who wrote the article
		owner_info = models.User.get_by_id(article.owner.id())
		if not owner_info.name:
			article_owner = owner_info.username
		else:
			article_owner = owner_info.name

		# build gravatar URL
		gravatar_hash = md5.new(owner_info.email.lower().strip()).hexdigest()
		article_gravatar_url = "https://www.gravatar.com/avatar/%s?s=100" % gravatar_hash

		# date format
		date_format = "%A, %d %b %Y"
		article_created = article.created.strftime(date_format)

		# create markdown and sanitize
		article_html = markdown.markdown(unicode(content, 'utf-8'))
		article_html = bleach.clean(article_html, config.bleach_tags, config.bleach_attributes)

		# load page content into params
		params = {
			'article_created': article_created,
			'article_html': article_html,
			'article_slug': article.slug,
			'article_title': article.title,
			'article_type': article.article_type,
			'article_owner': article_owner,
			'article_gravatar_url': article_gravatar_url,
			'article_host': self.request.host,
		}
		return self.render_template('blog/detail.html', **params)
	
