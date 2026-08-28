"""Smoke-test the FastAPI integration route without starting a server."""

from app.main import app
from fastapi.testclient import TestClient


def main() -> None:
    client = TestClient(app)

    health = client.get("/health")
    print("Health:", health.status_code, health.json())

    quote = client.post(
        "/api/quote",
        json={"letter_type": "standard", "country_code": "DE", "weight": 20},
    )
    print("Quote:", quote.status_code, quote.json())


if __name__ == "__main__":
    main()
