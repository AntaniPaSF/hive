SHELL := /bin/bash

.PHONY: setup start verify stop clean package

setup:
	./scripts/setup.sh

start:
	./scripts/start.sh

verify:
	./scripts/verify.sh

stop:
	docker compose down

clean:
	docker compose down -v || true
	docker image rm hive-assistant:local || true
	rm -rf dist

package:
	./scripts/package.sh
