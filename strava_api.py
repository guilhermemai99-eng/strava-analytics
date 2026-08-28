from sqlalchemy import Column, Integer, String, Float, Boolean

from database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação Strava
    strava_id = Column(Integer, unique=True, index=True, nullable=False)

    # Informação básica
    name = Column(String, nullable=False)
    sport_type = Column(String)

    # Distância e tempo
    distance_m = Column(Float)
    moving_time_s = Column(Integer)
    elapsed_time_s = Column(Integer)

    # Elevação
    elevation_gain_m = Column(Float)
    elev_high = Column(Float)
    elev_low = Column(Float)

    # Velocidade
    average_speed_m_s = Column(Float)
    max_speed_m_s = Column(Float)

    # Data
    start_date = Column(String)
    start_date_local = Column(String)
    timezone = Column(String)

    # Dispositivo
    device_name = Column(String)

    # Métricas sociais
    kudos_count = Column(Integer)
    achievement_count = Column(Integer)

    # Temperatura
    average_temp = Column(Float)

    # Frequência cardíaca
    has_heartrate = Column(Boolean)

    # Coordenadas inicial/final
    start_lat = Column(Float)
    start_lng = Column(Float)
    end_lat = Column(Float)
    end_lng = Column(Float)