from sqlalchemy import create_engine

DATABASE_URL = "postgresql+psycopg://kss:kss@localhost:5432/kss"

engine = create_engine(DATABASE_URL)
