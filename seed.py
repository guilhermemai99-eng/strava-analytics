from database import SessionLocal
from models import Activity


db = SessionLocal()

activities = [
    Activity(
        name="Morning Run",
        distance_km=10.2,
        time_minutes=48.5,
        average_heart_rate=151
    ),
    Activity(
        name="Easy Run",
        distance_km=7.4,
        time_minutes=42.1,
        average_heart_rate=142
    ),
    Activity(
        name="Long Run",
        distance_km=16.8,
        time_minutes=82.3,
        average_heart_rate=148
    )
]

db.add_all(activities)
db.commit()

db.close()

print("Atividades inseridas com sucesso!")
