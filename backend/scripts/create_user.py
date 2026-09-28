"""Cria um utilizador (não há registo público: os utilizadores criam-se aqui).

Uso (dentro do contentor da API):
    docker compose exec api python -m scripts.create_user ana@empresa.pt "Ana Silva"
    docker compose exec api python -m scripts.create_user --admin chefe@empresa.pt "Chefe"

Sem --admin o utilizador é `analyst`. Cria pelo menos um --admin: só admins gerem utilizadores.

A password é pedida no terminal (não aparece no ecrã nem no histórico da shell).
"""

import argparse
import getpass
import sys

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.services.users import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a user")
    parser.add_argument("email")
    parser.add_argument("full_name")
    parser.add_argument("--admin", action="store_true", help="give the administrator role")
    args = parser.parse_args()

    password = getpass.getpass("Password (min. 12 characters): ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")

    with SessionLocal() as db:
        try:
            role = UserRole.admin if args.admin else UserRole.analyst
            user = create_user(db, args.email, args.full_name, password, role=role)
        except ValueError as error:
            sys.exit(str(error))
    print(f"Created {user.role.value} {user.email} (id {user.id}).")


if __name__ == "__main__":
    main()
