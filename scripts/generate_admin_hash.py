#!/usr/bin/env python3
import getpass
import bcrypt

def main():
    print("Generate Admin Password Hash")
    print("----------------------------")
    password = getpass.getpass("Enter admin password: ")
    confirm = getpass.getpass("Confirm admin password: ")

    if password != confirm:
        print("Error: Passwords do not match.")
        return

    # Generate hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

    print("\nSuccess! Set the following environment variable in Railway:")
    print(f"ADMIN_PASSWORD_HASH={hashed.decode('utf-8')}")

if __name__ == "__main__":
    main()
