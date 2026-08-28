from database import SessionLocal
from models import Activity

db = SessionLocal()

db.query(Activity).filter(Activity.name == "Evening Run").delete()

db.commit()
db.close()

print("Dados de teste removidos.")