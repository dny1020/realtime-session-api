from getpass import getpass
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.auth.jwt import get_password_hash


def main():
    db: Session = SessionLocal()  # type: ignore
    try:
        username = input("Username: ").strip()
        email = input("Email (optional): ").strip() or None
        full_name = input("Full name (optional): ").strip() or None
        password = getpass("Password: ")
        confirm = getpass("Confirm Password: ")
        if password != confirm:
            print("Passwords do not match")
            return

        if db.query(User).filter(User.username == username).first():
            print("User already exists")
            return

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print("User created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
