"""Database commands. Run from the backend folder:

    python -m app.manage init-db                 create missing tables and sync roles
    python -m app.manage reset-db --yes          DROP every FixFlow table, then recreate (data is lost)
    python -m app.manage create-company "Name" admin@company.com "Admin Name"
                                                 create a company and its System Administrator
                                                 (asks for the password)
"""
import argparse
import getpass
import sys

from sqlalchemy import MetaData, select, text

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .enums import Role
from .models import User
from .security import password_problem
from .services.org_setup import create_organization, role_id, sync_rbac


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        sync_rbac(db)
    print("Tables are ready and roles are synced.")


def reset_db() -> None:
    # Reflect what is really there, so tables from older versions are removed too.
    existing = MetaData()
    existing.reflect(bind=engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for table in existing.sorted_tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE'))
    else:
        existing.drop_all(bind=engine)
    print(f"Dropped {len(existing.tables)} table(s).")
    init_db()


def create_company(name: str, email: str, admin_name: str) -> None:
    password = getpass.getpass("Password for the administrator: ")
    problem = password_problem(password)
    if problem:
        sys.exit(problem)
    from .routers.auth import set_password

    init_db()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email.lower())):
            sys.exit("A user with that email already exists.")
        org = create_organization(db, name)
        admin = User(organization_id=org.id, role_id=role_id(db, Role.ADMIN), name=admin_name, email=email.lower())
        set_password(admin, password)
        db.add(admin)
        db.commit()
        print(f"Created '{org.name}'. Join code for employees: {org.join_code}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.manage", description="FixFlow database commands")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    reset = sub.add_parser("reset-db")
    reset.add_argument("--yes", action="store_true", help="confirm that all data will be deleted")
    company = sub.add_parser("create-company")
    company.add_argument("name")
    company.add_argument("email")
    company.add_argument("admin_name")
    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "reset-db":
        if not args.yes:
            sys.exit("This deletes ALL FixFlow data. Run again with --yes to confirm.")
        reset_db()
    elif args.command == "create-company":
        create_company(args.name, args.email, args.admin_name)


if __name__ == "__main__":
    main()
