VENV_PYTHON := ~/DEVELOPMENT/virtualenv/t-cal-env/bin/python
PIP := ~/DEVELOPMENT/virtualenv/t-cal-env/bin/pip
MANAGE := $(VENV_PYTHON) backend/manage.py
COMPOSE := docker compose
BACKEND_BLACK_PATHS := backend
BACKEND_MYPY_PACKAGES := -p apps.analytics.models -p apps.analytics.services -p apps.accounts.services -p apps.bff.api.routers -p apps.bff.api.schemas -p apps.chat.services -p apps.calendars.services -p apps.core_agent.models -p apps.core_agent.providers -p apps.core_agent.services -p apps.core_agent.decorators -p apps.core_agent.apps -p apps.preferences.services -p apps.accounts.tests.models -p apps.accounts.tests.services -p apps.bff.tests.api -p apps.calendars.tests.models -p apps.calendars.tests.services -p apps.chat.tests.models -p apps.chat.tests.services -p apps.core.tests -p apps.core_agent.tests -p apps.preferences.tests.inngest -p apps.preferences.tests.models -p apps.preferences.tests.services

.PHONY: backend-install
backend-install:
	$(PIP) install -r backend/requirements.txt

.PHONY: backend-install-dev
backend-install-dev:
	$(PIP) install -r backend/requirements-dev.txt

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
	$(MANAGE) test apps.accounts.tests apps.analytics.tests apps.bff.tests apps.calendars.tests apps.chat.tests apps.core.tests apps.core_agent.tests apps.preferences.tests

.PHONY: backend-format
backend-format:
	$(VENV_PYTHON) -m black $(BACKEND_BLACK_PATHS)

.PHONY: backend-format-check
backend-format-check:
	$(VENV_PYTHON) -m black --check $(BACKEND_BLACK_PATHS)

.PHONY: backend-typecheck
backend-typecheck:
	cd backend && $(VENV_PYTHON) -m mypy $(BACKEND_MYPY_PACKAGES)

.PHONY: backend-quality
backend-quality: backend-format-check backend-typecheck check

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
test-all: test frontend-test

.PHONY: runserver
runserver:
	$(MANAGE) runserver

.PHONY: docker-build
docker-build:
	$(COMPOSE) build backend frontend

.PHONY: up
up:
	$(COMPOSE) up --build -d

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: restart
restart:
	$(COMPOSE) down
	$(COMPOSE) up --build -d

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

# Interactive: requires backend container running (`make up`)
.PHONY: createsuper
createsuper:
	$(COMPOSE) exec backend python manage.py createsuperuser

.PHONY: docker-test
docker-test:
	$(COMPOSE) exec backend python manage.py test apps.accounts.tests apps.analytics.tests apps.bff.tests apps.calendars.tests apps.chat.tests apps.core.tests apps.core_agent.tests apps.preferences.tests
