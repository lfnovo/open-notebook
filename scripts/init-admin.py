#!/usr/bin/env python3
"""
Initialize or reset the admin user for Lumina.

Creates the admin user if it doesn't exist, or resets the password if it
already exists. Uses the same bcrypt hashing as the application.

Usage:
    uv run scripts/init-admin.py [--username admin] [--password admin]

Environment variables:
    LUMINA_ADMIN_USERNAME   default: admin
    LUMINA_ADMIN_PASSWORD   default: admin (change in production!)

The script reads the SurrealDB connection from the same environment
variables used by the app (SURREAL_URL, SURREAL_NAMESPACE, etc.).
"""

import argparse
import os
import sys

import bcrypt

# Add project root to path so we can import open_notebook modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from open_notebook.database.repository import db_connection, ensure_record_id, parse_record_ids


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def main():
    parser = argparse.ArgumentParser(description="Initialize Lumina admin user")
    parser.add_argument(
        "--username",
        default=os.environ.get("LUMINA_ADMIN_USERNAME", "admin"),
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("LUMINA_ADMIN_PASSWORD", "admin"),
        help="Admin password (default: admin)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force password reset even if user already exists with a password",
    )
    args = parser.parse_args()

    if len(args.password) < 4:
        print("ERROR: Password must be at least 4 characters long.")
        sys.exit(1)

    hashed = hash_password(args.password)

    async with db_connection() as conn:
        # Check if admin user already exists
        existing = parse_record_ids(
            await conn.query(
                "SELECT id, username, hashed_password FROM app_user WHERE username = $username",
                {"username": args.username},
            )
        )

        if existing:
            user = existing[0]
            user_id = user["id"]
            current_hash = user.get("hashed_password", "")

            if current_hash and not args.force:
                print(
                    f"Admin user '{args.username}' already exists ({user_id}).\n"
                    f"Use --force to reset the password."
                )
            else:
                await conn.query(
                    """
                    UPDATE $uid SET
                        hashed_password = $hashed,
                        display_name = display_name ?? $username,
                        role = 'admin',
                        status = 'active',
                        password_changed_at = time::now(),
                        updated = time::now()
                    """,
                    {
                        "uid": ensure_record_id(user_id),
                        "username": args.username,
                        "hashed": hashed,
                    },
                )
                print(f"✅ Password reset for admin user '{args.username}' ({user_id}).")
        else:
            result = parse_record_ids(
                await conn.query(
                    """
                    CREATE app_user SET
                        username = $username,
                        display_name = $username,
                        role = 'admin',
                        status = 'active',
                        hashed_password = $hashed,
                        password_changed_at = time::now(),
                        created = time::now(),
                        updated = time::now()
                    """,
                    {"username": args.username, "hashed": hashed},
                )
            )
            user_id = result[0]["id"] if result else "unknown"
            print(f"✅ Admin user '{args.username}' created ({user_id}).")

    print(f"\n   Username: {args.username}")
    print(f"   Password: {args.password}")
    print(f"\nLogin at:  http://localhost:3000/login")


if __name__ == "__main__":
    asyncio.run(main())
