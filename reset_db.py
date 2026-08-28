print("RESET DB A COMEÇAR")

from database import engine, Base
from models import Activity
from strava_auth import StravaAuth

print("A apagar tabelas antigas...")

Base.metadata.drop_all(bind=engine)

print("A criar tabelas novas...")

Base.metadata.create_all(bind=engine)

print("Base de dados atualizada com sucesso!")