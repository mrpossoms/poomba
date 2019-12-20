MY_PIP=$(shell which pip)

.deps:
	@echo "my pwd $(shell pwd)"
	@echo "using pip '$(MY_PIP)'"
	$(MY_PIP) install -r requirements.txt
	touch .deps


/var/pood/ds:
	sudo mkdir -p $@

/etc/pood/model:
	sudo mkdir -p $@

.PHONY: install
install: /var/pood/ds /etc/pood/model
	sudo chown -R $(USER) /var/pood
	sudo chown -R $(USER) /etc/pood
	
	@echo "pood installed"
	
