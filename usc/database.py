import logging

import pandas as pd
import sqlalchemy
from sqlalchemy import Column, create_engine, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.types import Integer, String, Float
from sqlalchemy_utils import database_exists, create_database

Base = declarative_base()

DB_FILENAME = "sqlite:///db/checkins.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def auto_str(cls):
    """Decorator to a nice str representation to sqlalchemy objects"""

    def __str__(self):
        name = type(self).__name__
        items = ", ".join([f"{key}={value}" for key, value in vars(self).items()])
        return f"{name}({items})"

    cls.__str__ = __str__
    return cls


@auto_str
class Checkin(Base):
    __tablename__ = "checkin"

    day = Column("day", Integer, primary_key=True)
    month = Column("month", Integer, primary_key=True)
    year = Column("year", Integer, primary_key=True)
    weekday = Column("weekday", Integer)
    sport = Column("sport", String)
    venue = Column("venue", String, primary_key=True)
    checkin_limit = Column("checkin_limit", Integer)
    cost = Column("cost", Float)


def db_url() -> sqlalchemy.engine.url.URL:
    return sqlalchemy.engine.url.make_url(DB_FILENAME)


def create_pg_tables_if_needed(db_connection: str | sqlalchemy.engine.url.URL):
    """Creates the PostgreSQL database and tables. Drops all Foreign Key constraints after creating the tables, since
    Beam cannot guarantee that FK Constraints can be met with parallelism."""
    if database_exists(db_connection):
        logger.info("Database and tables already exist!")
        return

    engine = sqlalchemy.create_engine(db_connection, echo=False)
    create_database(engine.url)
    logger.info(f"Created DB database {engine.url}")

    Base.metadata.create_all(engine)  # create all tables
    logger.info(f"Created DB tables {list(Base.metadata.tables.keys())}")
    return


def write_checkins_to_db(checkins: pd.DataFrame):
    records = list(checkins.T.to_dict().values())
    insert_stmt = insert(Checkin).values(records)
    primary_keys = [col for col in Checkin.__table__.primary_key]
    records = {pk.name: getattr(insert_stmt.excluded, pk.name) for pk in primary_keys}
    upsert_stmt = insert_stmt.on_conflict_do_update(index_elements=primary_keys, set_=records)

    with sqlalchemy.create_engine(db_url(), echo=False).begin() as conn:
        conn.execute(upsert_stmt)
    logger.info(f"Wrote {len(checkins)} checkins to DB")


def get_attendance_per_month(year: int = None, month: int = None) -> pd.DataFrame:
    """Returns a dataframe with the attendance per venue for the given year and month.
    If no year or month is given, then the cumulative attendance is returned. Total cost
    for the timeframe is calculated.
    """
    assert not year or year >= 2018
    assert not month or month <= 12
    with Session(create_engine(db_url())) as session:
        query = session.query(Checkin, func.count(Checkin.venue).label("count"))
        query = _filter_by_date(query, month, year)
        query = query.group_by(Checkin.venue)
        df = pd.read_sql(query.statement, query.session.bind)

    df["cost"] = df["cost"] * df["count"]
    return df


def get_sport_per_month(year: int = None, month: int = None) -> pd.DataFrame:
    """Returns a dataframe with the sport counts for the given year and month.
    If no year or month is given, then the cumulative returned.
    """
    assert not year or year >= 2018
    assert not month or month <= 12
    with Session(create_engine(db_url())) as session:
        query = session.query(Checkin.sport, func.count(Checkin.sport).label("count"))
        query = _filter_by_date(query, month, year)
        query = query.group_by(Checkin.sport)
        df = pd.read_sql(query.statement, query.session.bind)

    df["sport"].replace({"Bouldern": "Bouldering", "bouldern": "Bouldering"}, inplace=True)
    df = df.groupby("sport").sum().sort_values("count", ascending=False)

    return df


def _filter_by_date(query: sqlalchemy.orm.query.Query, month: int | None, year: int | None) -> sqlalchemy.orm.query.Query:
    if year:
        query = query.filter(Checkin.year == year)
    if month:
        query = query.filter(Checkin.month == month)
    return query


if __name__ == "__main__":
    create_pg_tables_if_needed(db_url())
