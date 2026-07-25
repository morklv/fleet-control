.PHONY: test backend frontend

test:
	python3 -m pytest backend/tests -q
	cd frontend && npm run build

backend:
	python3 -m uvicorn fleet_control.api.app:app --app-dir backend --reload --port 8100

frontend:
	cd frontend && npm run dev
