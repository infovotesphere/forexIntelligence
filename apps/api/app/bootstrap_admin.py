import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main() -> int:
    from app.core.config import get_settings

    settings = get_settings()
    email = settings.bootstrap_admin_email.strip().lower()
    password = settings.bootstrap_admin_password
    if not email and not password:
        with SessionLocal() as db:
            has_existing_user = db.scalar(select(User.id).limit(1)) is not None
        if has_existing_user:
            print("Admin bootstrap skipped: existing user accounts are present.")
            return 0
        print("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD to provision the first administrator.", file=sys.stderr)
        return 1
    if not email or not password:
        print("Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD.", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            print(f"Admin account {email} already exists; no changes made.")
            return 0
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role="administrator",
                is_active=True,
            )
        )
        db.commit()
    print(f"Created administrator account {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
