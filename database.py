# from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

# class User(Base):
#     __tablename__ = 'users'

#     id = Column(Integer, primary_key=True)
#     fullname = Column(String)
#     username = Column(String)
#     password = Column(String)

# def create_database():
#     engine = create_engine('sqlite:///users.db', echo=True)
#     Base.metadata.create_all(bind=engine)
#     return engine

# def add_user(fullname,username, password):
#     engine = create_database()
#     Session = sessionmaker(bind=engine)
#     session = Session()

#     user = User(fullname=fullname,username=username, password=password)
#     session.add(user)
#     session.commit()
#     session.close()

# def get_user(username):
#     engine = create_database()
#     Session = sessionmaker(bind=engine)
#     session = Session()

#     user = session.query(User).filter_by(username=username).first()
#     session.close()

#     return user

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    fullname = Column(String)
    username = Column(String)
    password = Column(String)
    search_history = relationship("SearchHistory", back_populates="user")
    user_ratings = relationship("UserRating", back_populates="user")

class SearchHistory(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    movie_id = Column(Integer) 
    movie_title = Column(String)
    user = relationship("User", back_populates="search_history")

    def __repr__(self):
        return f"SearchHistory(user_id={self.user_id}, movie_id={self.movie_id}, movie_title='{self.movie_title}')"
        
class UserRating(Base):
    __tablename__ = 'user_ratings'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    movie_id = Column(Integer)
    movie_title = Column(String)
    rating = Column(Integer)
    user = relationship("User", back_populates="user_ratings")

    def __repr__(self):
        return f"UserRating(user_id={self.user_id}, movie_id={self.movie_id}, movie_title='{self.movie_title}', rating={self.rating})"


def create_database():
    engine = create_engine('sqlite:///users.db', echo=True)
    Base.metadata.create_all(bind=engine)
    return engine

def add_user(fullname, username, password):
    engine = create_database()
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(fullname=fullname, username=username, password=password)
    session.add(user)
    session.commit()
    session.close()

def get_user(username):
    engine = create_database()
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    return user