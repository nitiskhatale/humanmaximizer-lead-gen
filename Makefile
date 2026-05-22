.PHONY: install ingest seed test demo pdf up down logs

install:
	cd backend && pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs api -f

ingest:
	docker compose exec api python scripts/ingest.py

ingest-refresh:
	docker compose exec api python scripts/ingest.py --refresh

seed:
	docker compose exec api python scripts/seed_demo_leads.py

test:
	cd backend && pytest tests/ -v

demo:
	@echo "Demo running at: http://localhost:8000/docs"
	@echo "Steps:"
	@echo "  1. POST /api/v1/search"
	@echo "  2. GET  /api/v1/leads/{lead_id}"
	@echo "  3. POST /api/v1/outreach/generate"
	@echo "  4. GET  /api/v1/rag/query?q=payroll+compliance"

pdf:
	python scripts/generate_architecture_pdf.py
