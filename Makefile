# makefile

# listen ports
PORT=8079
ADMIN_PORT=8088

# pylint
PYLINTS = $(wildcard *.py \
	libs/*.py \
	)
PYLINTFILES = $(patsubst %.py,.%.lint,$(notdir $(PYLINTS)))
PYLINT = $(join $(dir $(PYLINTS)),$(PYLINTFILES))

# python path
PYTHONPATH=$(GAEPATH):$(GAEPATH)/lib/yaml/lib:$(GAEPATH)/lib/webob:$(GAEPATH)/lib/webapp2:$(GAEPATH)/lib/jinja2:.

# app info
APP=$(shell grep 'application:' app.yaml | sed -e 's/^application:\s*//g')
BRANCH=master

serve:
	dev_appserver.py --port=$(PORT) --admin_host=0.0.0.0 --admin_port=$(ADMIN_PORT) ./


.%.lint: %.py
	@PYTHONPATH=$(PYTHONPATH) pychecker --only --no-miximport --no-override -Z __website__,__author__,__all__,__version__ $?
	@touch $@


install:
	./install.sh $(ADMIN_PORT)

	
lint: $(PYLINT)


clean:
	-rm ${PYLINT}


push: lint
	git push origin $(BRANCH)


upload:
	appcfg.py update --skip_sdk_update_check ./


push-and-upload: push upload


python:
	PYTHONPATH=$(PYTHONPATH) python


.PHONY: run lint clean push upload push-and-upload python
