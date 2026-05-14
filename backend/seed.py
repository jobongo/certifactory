from app.database import SessionLocal, engine, Base
from app.models import User, UserRole
from app.services.auth_service import AuthService

Base.metadata.create_all(bind=engine)

auth = AuthService()
db = SessionLocal()

existing = db.query(User).filter(User.username == "admin").first()
if not existing:
    admin = User(
        username="admin",
        email="admin@pki.local",
        password_hash=auth.hash_password("admin"),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
    print("Admin user created (username: admin, password: admin)")
else:
    print("Admin user already exists")

db.close()
