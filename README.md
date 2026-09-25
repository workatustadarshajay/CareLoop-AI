# CareLoop AI

The foundation flow accepts a doctor's note, uses a Gemini tool-calling agent to save each actionable item as a card in Postgres, and displays all saved cards in the frontend.

## Run locally

1. Start Postgres:

	```bash
	docker compose up -d --wait
	```

2. Configure the backend:

	```bash
	cp Backend/.env.example Backend/.env
	```

	Add your Gemini key to `Backend/.env` as `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

3. Apply the database migration and start the API:

	```bash
	cd Backend
	uv run --system-certs alembic upgrade head
	uv run --system-certs uvicorn app.main:app --reload --port 8000
	```

4. Start the frontend in a second terminal:

	```bash
	cd Frontend
	npm run dev
	```

Open the Vite URL shown in the terminal. The API is available at `http://localhost:8000` and its OpenAPI docs are at `/docs`.
