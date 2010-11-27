import os
import hashlib
import json

import datetime
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Text, DateTime, MetaData, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relation
from sqlalchemy.ext.declarative import declarative_base

#Session = sessionmaker(autocommit=True)
Session = sessionmaker(autocommit=False)
session = None
metadata = MetaData()

class _Base(object):

    @classmethod
    def new(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        session.add(obj)
        session.commit()
        return obj

    @classmethod
    def by_id(cls, id):
        return session.query(cls).get(id)

    @classmethod
    def _select(cls, *filters):
        q = session.query(cls)
        for f in filters:
            q = q.filter(f)
        return q

    @classmethod
    def select(cls, *filters):
        return list(cls._select(*filters))

    @classmethod
    def select_one(cls, *filters):
        return cls._select(*filters).first()

Base = declarative_base(metadata=metadata, cls=_Base)

def connect(path=None, create_all=True):
    global session

    engine_path = path or 'sqlite:///dev.sqlite'
    engine = sqlalchemy.create_engine(engine_path)
    if create_all:
        metadata.bind = engine
        metadata.create_all()
    Session.configure(bind=engine)
    session = Session()

#####################
# TABLE DEFINITIONS
#####################

class User(Base):

    __tablename__ = 'user'

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False) # the username
    password = Column(String, nullable=False)

    @staticmethod
    def _hash_password(salt, raw_password):
        sha = hashlib.sha1()
        sha.update(salt[:4])
        sha.update(str(raw_password))
        sha.update(salt[4:])
        return sha.digest()

    @classmethod
    def create(cls, name, password):
        # the name cannot already exist
        existing = session.query(cls).filter(cls.name == name).count()
        if existing:
            return None

        # hash the password
        salt = os.urandom(8)
        pw_hash = cls._hash_password(salt, password)

        # tada, a new user
        return cls.new(name=name, password=(salt + pw_hash).encode('hex'))

    @classmethod
    def authenticate(cls, name, password):
        """Load a user based on the user_id and password. If the password is
        incorrect, or the user does not exist, None will be returned.
        """
        user = cls.select_one(cls.name == name)
        if user:
            raw_password = user.password.decode('hex')
            salt, pw_hash = raw_password[:8], raw_password[8:]
            input_hash = cls._hash_password(salt, password)
            if input_hash == pw_hash:
                return user
        return None

