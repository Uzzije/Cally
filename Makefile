VENV_PYTHON := ~/DEVELOPMENT/virtualenv/t-cal-env/bin/python
PIP := ~/DEVELOPMENT/virtualenv/t-cal-env/bin/pip
MANAGE := $(VENV_PYTHON) backend/manage.py
COMPOSE := docker compose

.PHONY: backend-install
backend-install:
	$(PIP) install -r backend/requirements.txt

.PHONY: check
check:
	$(MANAGE) check

.PHONY: makemigrations
makemigrations:
	$(MANAGE) makemigrations

.PHONY: migrate
migrate:
	$(MANAGE) migrate

.PHONY: test
test:
	$(MANAGE) test apps.accounts.tests apps.calendars.tests apps.core_agent.tests apps.chat.tests apps.bff.tests

.PHONY: backend-test
backend-test:
	$(MANAGE) test apps.accounts.tests apps.calendars.tests apps.core_agent.tests apps.chat.tests apps.bff.tests

.PHONY: backend-eval-test
backend-eval-test:
	$(MANAGE) test apps.chat.tests.services.test_chat_eval_suite

.PHONY: frontend-test
frontend-test:
	cd frontend && . ~/.nvm/nvm.sh && nvm use 20 >/dev/null && npm test

.PHONY: frontend-lint
frontend-lint:
	cd frontend && . ~/.nvm/nvm.sh && nvm use 20 >/dev/null && npm run lint

.PHONY: frontend-build
frontend-build:
	cd frontend && . ~/.nvm/nvm.sh && nvm use 20 >/dev/null && npm run build

.PHONY: test-all
test-all: backend-test frontend-test

.PHONY: runserver
runserver:
	$(MANAGE) runserver

.PHONY: docker-build
docker-build:
	$(COMPOSE) build backend frontend

.PHONY: docker-up
docker-up:
	$(COMPOSE) up --build -d

.PHONY: up
up:
	$(COMPOSE) up --build -d

.PHONY: docker-down
docker-down:
	$(COMPOSE) down

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: restart
restart:
	$(COMPOSE) down
	$(COMPOSE) up --build -d

.PHONY: docker-logs
docker-logs:
	$(COMPOSE) logs -f frontend backend

.PHONY: logs
logs:
	$(COMPOSE) logs -f frontend backend

.PHONY: backend-logs
backend-logs:
	$(COMPOSE) logs -f backend

.PHONY: frontend-logs
frontend-logs:
	$(COMPOSE) logs -f frontend

.PHONY: db-logs
db-logs:
	$(COMPOSE) logs -f db

.PHONY: docker-shell
docker-shell:
	$(COMPOSE) exec backend sh

.PHONY: frontend-shell
frontend-shell:
	$(COMPOSE) exec frontend sh

.PHONY: runserver-debug
runserver-debug:
	LOG_LEVEL=DEBUG $(MANAGE) runserver

.PHONY: docker-migrate
docker-migrate:
	$(COMPOSE) exec backend python manage.py migrate

# Interactive: requires backend container running (`make up` or `make docker-up`)
.PHONY: createsuper docker-createsuperuser
createsuper docker-createsuperuser:
	$(COMPOSE) exec backend python manage.py createsuperuser

.PHONY: docker-test
docker-test:
	$(COMPOSE) exec backend python manage.py test apps.accounts.tests apps.calendars.tests apps.core_agent.tests apps.chat.tests apps.bff.tests
