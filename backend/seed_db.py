# C:\Users\akshay\Desktop\Aarchaya AI\backend\seed_db.py

from sqlmodel import Session, select
from auth import engine, get_password_hash, Worker, create_db_and_tables

def seed_database():
    print("Seeding database...")
    
    # Create tables (just in case they don't exist)
    # This function is also imported from auth.py
    create_db_and_tables()

    with Session(engine) as session:
        # Check if the worker already exists
        existing_worker = session.exec(
            select(Worker).where(Worker.username == "healthworker")
        ).first()

        if not existing_worker:
            # Create the default worker
            default_worker = Worker(
                username="healthworker",
                hashed_password=get_password_hash("securepass")
            )
            session.add(default_worker)
            session.commit()
            print("Default health worker created successfully.")
        else:
            print("Default health worker already exists.")

if __name__ == "__main__":
    seed_database()