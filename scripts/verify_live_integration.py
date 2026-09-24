import sys
import os
sys.path.insert(0, os.path.abspath("."))

# Set environment to development to use Supabase VPS PostgreSQL
os.environ["APP_ENV"] = "development"

from fastapi.testclient import TestClient
from app import app
from backend.database import SessionLocal
from backend import models

client = TestClient(app)

print("--- Testing /api/health ---")
resp = client.get("/api/health")
print("Health response:", resp.status_code, resp.json())
assert resp.status_code == 200

print("\n--- Verifying Database Connection directly via SessionLocal ---")
db = SessionLocal()
try:
    user = db.query(models.User).filter_by(email="augustobussvitor@gmail.com").first()
    assert user is not None, "User not found!"
    print(f"Found User in Supabase '3dprintcalc': id={user.id}, email={user.email}, name='{user.full_name}', company='{user.company_name}'")
    
    printers = db.query(models.Printer).filter_by(user_id=user.id).all()
    print(f"Found {len(printers)} printers: {[p.name for p in printers]}")
    assert len(printers) >= 1
    
    filaments = db.query(models.Filament).filter_by(user_id=user.id).all()
    print(f"Found {len(filaments)} filaments: {[f.name for f in filaments[:4]]}...")
    assert len(filaments) >= 10
    
    projects = db.query(models.Project).filter_by(user_id=user.id).all()
    print(f"Found {len(projects)} projects: {[p.name for p in projects[:3]]}...")
    assert len(projects) >= 50
finally:
    db.close()

print("\n--- Testing API Endpoints with JWT Token for Restored User ---")
from backend.auth import create_access_token
token = create_access_token({"sub": str(user.id)})
headers = {"Authorization": f"Bearer {token}"}

# Test /api/auth/me
me_resp = client.get("/api/auth/me", headers=headers)
print("/api/auth/me:", me_resp.status_code, me_resp.json().get("email"), me_resp.json().get("full_name"))
assert me_resp.status_code == 200
assert me_resp.json()["email"] == "augustobussvitor@gmail.com"

# Test /api/printers
printers_resp = client.get("/api/printers", headers=headers)
print(f"/api/printers: {printers_resp.status_code}, returned {len(printers_resp.json())} printers")
assert printers_resp.status_code == 200
assert len(printers_resp.json()) >= 1

# Test /api/filaments
filaments_resp = client.get("/api/filaments", headers=headers)
print(f"/api/filaments: {filaments_resp.status_code}, returned {len(filaments_resp.json())} filaments")
assert filaments_resp.status_code == 200
assert len(filaments_resp.json()) >= 10

# Test /api/projects
projects_resp = client.get("/api/projects", headers=headers)
print(f"/api/projects: {projects_resp.status_code}, returned {len(projects_resp.json())} projects")
assert projects_resp.status_code == 200
assert len(projects_resp.json()) >= 50

print("\nALL INTEGRATION CHECKS PASSED SUCCESSFULLY WITH 3DPRINTCALC SCHEMA!")
