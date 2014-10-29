# makefile

# listen ports
PORT=8079
ADMIN_PORT=8088

# app info
APP=$(shell grep 'application:' app.yaml | sed -e 's/^application:\s*//g')
BRANCH=master

serve:
	~/Code/google_appengine/dev_appserver.py --port=$(PORT) --admin_host=0.0.0.0 --admin_port=$(ADMIN_PORT) ./

install:
	./install.sh $(ADMIN_PORT)

push:
	git push

upload:
	appcfg.py update --skip_sdk_update_check ./
