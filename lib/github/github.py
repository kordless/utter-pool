import time
import json
from urlparse import urlparse

from google.appengine.api import urlfetch

import config

# pull down the base info for the repo
def repo_base(url):
	try:
		# parse the url and build a normalized github URL
		parts = urlparse(url)
		url = "https://%s/%s" % (config.github_url.strip('/'), parts[2].strip('/'))
		
		# use the path to make an API GET for the repo JSON
		repo = json.loads(
			urlfetch.fetch("https://%s/%s/%s" % (
				config.github_api_url.strip('/'),
				'repos',
				parts[2].strip('/')
			), deadline=5).content
		)

		if 'name' not in repo:
			raise Exception("A valid Github repository was not found using that URL.")

		# build and return the response
		response = {'response': 'success', 'result': {'repo': repo}}
		return response

	except Exception as ex:
		# build and return the failure
		response = {'response': 'fail', 'result': {'message': "Project was not added. %s" % ex} }
		return response

def repo_sync_contents(project, url):
	try:
		# parse the url and build a normalized github URL
		parts = urlparse(url)
		url = "https://%s/%s" % (config.github_url.strip('/'), parts[2].strip('/'))
		
		# use the path to make an API GET for the repo JSON
		contents = json.loads(
			urlfetch.fetch("https://%s/%s/%s/%s/%s" % (
				config.github_api_url.strip('/'),
				'repos',
				parts[2].strip('/'), # repo name
				'contents',
				'utterio'
			), deadline=5).content
		)

		# check for required files
		check = {'README.md': 0, 'utterio.json': 0, 'install.sh': 0, 'icon.png': 0}
		for file in contents:
			if file['name'] == "README.md":
				project.readme_url = file['download_url']
				project.readme_link = file['html_url']
				check['README.md'] = 1
			if file['name'] == "utterio.json":
				project.json_url = file['download_url']
				project.json_link = file['html_url']
				check['utterio.json'] = 1
			if file['name'] == "install.sh":
				project.install_url = file['download_url']
				project.install_link = file['html_url']
				check['install.sh'] = 1
			if file['name'] == "icon.png":
				project.icon_url = file['download_url']
				project.icon_link = file['html_url']
				check['icon.png'] = 1

		# do a pass to build missing files string
		missing = ""
		for key,value in check.items():
			if not value:
				missing = "%s%s, " % (missing, key)
		missing = missing.strip(', ')

		# build the response object
		response = {'response': "success", 'result': {'message': ''}}

		# build the appropriate message			
		if missing == "":
			# build and return the response
			response['result']['message'] = "A complete Utter.io configuration was found!"
		else:
			response['response'] = "fail"
			response['result']['message'] = "The repository needs the following files added to the utterio directory: %s." % missing

		return response

	except Exception as ex:
		# build and return the failure
		response = {'response': "fail", 'result': {'message': "The repository doesn't contain an utterio configuration. %s" % ex} }
		return response


