from database import SessionLocal
from models import Activity


db = SessionLocal()

activities = db.query(Activity).all()

for activity in activities:
    print(
        activity.id,
        activity.name,
        activity.distance_km,
        activity.time_minutes,
        activity.average_heart_rate
    )

db.close()
