from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from database import Base


class Activity(Base):
    __tablename__ = "activities"

    # =========================================================
    # IDENTIFICAÇÃO DO ATLETA
    # =========================================================

    athlete_id = Column(
        Integer,
        ForeignKey("athletes.id"),
        index=True,
        nullable=False,
    )

    # =========================================================
    # IDENTIFICAÇÃO DA ATIVIDADE
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Strava activity IDs exceed 32-bit INTEGER range.
    strava_id = Column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False
    )

    # =========================================================
    # INFORMAÇÃO BÁSICA
    # =========================================================

    name = Column(
        String,
        nullable=False
    )

    sport_type = Column(
        String
    )

    # =========================================================
    # DISTÂNCIA E TEMPO
    # =========================================================

    distance_m = Column(
        Float
    )

    moving_time_s = Column(
        Integer
    )

    elapsed_time_s = Column(
        Integer
    )

    # =========================================================
    # ELEVAÇÃO
    # =========================================================

    elevation_gain_m = Column(
        Float
    )

    elev_high = Column(
        Float
    )

    elev_low = Column(
        Float
    )

    # =========================================================
    # VELOCIDADE
    # =========================================================

    average_speed_m_s = Column(
        Float
    )

    max_speed_m_s = Column(
        Float
    )

    # =========================================================
    # DATA
    # =========================================================

    start_date = Column(
        String
    )

    start_date_local = Column(
        String
    )

    timezone = Column(
        String
    )

    # =========================================================
    # DISPOSITIVO
    # =========================================================

    device_name = Column(
        String
    )

    # =========================================================
    # MÉTRICAS
    # =========================================================

    kudos_count = Column(
        Integer
    )

    achievement_count = Column(
        Integer
    )

    # =========================================================
    # TEMPERATURA
    # =========================================================

    average_temp = Column(
        Float
    )

    # =========================================================
    # FREQUÊNCIA CARDÍACA
    # =========================================================

    has_heartrate = Column(
        Boolean
    )

    # =========================================================
    # COORDENADAS
    # =========================================================

    start_lat = Column(
        Float
    )

    start_lng = Column(
        Float
    )

    end_lat = Column(
        Float
    )

    end_lng = Column(
        Float
    )

    # =========================================================
    # FEED MEDIA (Strava-hosted; no local object storage)
    # =========================================================

    summary_polyline = Column(
        Text,
        nullable=True,
    )

    photo_url = Column(
        Text,
        nullable=True,
    )

    photo_count = Column(
        Integer,
        nullable=True,
    )