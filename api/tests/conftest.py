import os, pytest
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app import app, db

@pytest.fixture
def client():
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

@pytest.fixture
def seeded_client(client):
    from app import seed_centres
    seed_centres()
    return client