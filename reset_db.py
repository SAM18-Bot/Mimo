import sys

# Load environment first
from dotenv import load_dotenv

load_dotenv()

from db.database import Base, engine


def reset_database():
    print(f"Connecting to database at {engine.url}...")
    
    # Require confirmation if not sqlite
    if not str(engine.url).startswith("sqlite"):
        if "--force" not in sys.argv:
            confirm = input("WARNING: This is not a local SQLite database (e.g. Neon/Postgres). Are you sure you want to DROP all tables? (y/N): ")
            if confirm.lower() != 'y':
                print("Aborted. Run with --force to bypass this prompt.")
                sys.exit(0)

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables from scratch...")
    Base.metadata.create_all(bind=engine)
    
    print("Database has been successfully reset! All users will need to register and onboard again.")

if __name__ == "__main__":
    reset_database()
