import asyncio
import sys
import os
import getpass

# Add project root to path
sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    print("Create Admin User")
    print("-----------------")
    username = input("Enter username: ")
    if not username:
        print("Username cannot be empty.")
        return

    password = getpass.getpass("Enter password: ")
    if not password:
        print("Password cannot be empty.")
        return

    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("Passwords do not match.")
        return

    try:
        async with AsyncSessionLocal() as session:
            # Check if exists
            result = await session.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                print(f"Error: User '{username}' already exists.")
                return

            hashed_password = get_password_hash(password)
            user = User(
                username=username,
                hashed_password=hashed_password,
                is_superuser=True,
                is_active=True
            )
            session.add(user)
            await session.commit()
            print(f"Success: Admin user '{username}' created.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
