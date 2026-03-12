from flask import Flask, redirect, request, url_for
from flask import Response

import requests

from flask import request
from flask import Flask, render_template

from jinja2 import Template
import secrets

import base64
import json
import os


from flask import session


app = Flask(__name__)

app.secret_key = secrets.token_hex() 


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, ForeignKey, String

from logging.config import dictConfig


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    },
     'file.handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'weatherportal.log',
            'maxBytes': 10000000,
            'backupCount': 5,
            'level': 'DEBUG',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file.handler']
    }
})

# Not required for assignment3
in_mem_cities = []
in_mem_user_cities = {}


# SQLite Database creation
Base = declarative_base()
engine = create_engine("sqlite:///weatherportal.db", echo=True, future=True)
DBSession = sessionmaker(bind=engine)


@app.before_first_request
def create_tables():
    Base.metadata.create_all(engine)


class Admin(Base):
    __tablename__ = 'admin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<Admin(name='%s')>" % (self.name)

    # Ref: https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class City(Base):
    __tablename__ = 'city'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    url = Column(String)
    adminid = Column(Integer, ForeignKey('admin.id'))

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class UserCity(Base):
    __tablename__ = 'usercity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cityId = Column(Integer, ForeignKey('city.id'))
    userId = Column(Integer, ForeignKey('user.id'))
    month = Column(String)
    year = Column(String)
    weather_params = Column(String)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


## This is the Admin REST API
@app.route("/admin", methods=['POST'])
def add_admin():
    app.logger.info("Inside add_admin")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    name = data['name']
    password = data['password']

    admin = Admin(name=name, password=password)

    session = DBSession()
    session.add(admin)
    session.commit()

    return admin.as_dict()


@app.route("/admin")
def get_admins():
    app.logger.info("Inside get_admins")
    ret_obj = {}

    session = DBSession()
    admins = session.query(Admin)
    admin_list = []
    for admin in admins:
        admin_list.append(admin.as_dict())

    ret_obj['admins'] = admin_list
    return ret_obj


@app.route("/admin/<id>")
def get_admin_by_id(id):
    app.logger.info("Inside get_admin_by_id %s\n", id)

    session = DBSession()
    admin = session.get(Admin, id)

    app.logger.info("Found admin:%s\n", str(admin))
    if admin == None:
        status = ("Admin with id {id} not found\n").format(id=id)
        return Response(status, status=404)
    else:
        return admin.as_dict()


@app.route("/admin/<id>", methods=['DELETE'])
def delete_admin_by_id(id):
    app.logger.info("Inside delete_admin_by_id %s\n", id)

    session = DBSession()
    admin = session.query(Admin).filter_by(id=id).first()

    app.logger.info("Found admin:%s\n", str(admin))
    if admin == None:
        status = ("Admin with id {id} not found!\n").format(id=id)
        return Response(status, status=404)
    else:
        session.delete(admin)
        session.commit()
        status = ("Admin with id {id} deleted! \n").format(id=id)
        return Response(status, status=200)


## This is the User REST API
@app.route("/users", methods=['POST'])
def add_user():
    data = request.json
    name = data['name']
    password = data['password']
    session = DBSession()
    existing = session.query(User).filter_by(name=name).first()
    if existing:
        return Response(f"Sorry, user with {name} already exists :(", status=400)
    user = User(name=name, password=password)
    session.add(user)
    session.commit()
    return user.as_dict()

@app.route("/users")
def get_users():
    session = DBSession()
    users = session.query(User).all()
    return {"users": [u.as_dict() for u in users]}

@app.route("/users/<id>")
def get_user_by_id(id):
    session = DBSession()
    user = session.get(User, id)
    if user is None:
        return Response(f"Sorry, person with id {id} not found.", status=404)
    return user.as_dict()

@app.route("/users/<id>", methods=['DELETE'])
def delete_user_by_id(id):
    session = DBSession()
    user = session.query(User).filter_by(id=id).first()
    if user is None:
        return Response(f"Sorry, user with id {id} not found.", status=404)
    session.delete(user)
    session.commit()
    return Response(f"Sorry, person with {id} deleted.", status=200)


## This is the City REST API
@app.route("/admin/<admin_id>/cities", methods=['POST'])
def add_city(admin_id):
    session = DBSession()
    admin = session.get(Admin, admin_id)
    if admin is None:
        return Response(f"Sorry, admin with id {admin_id} not found", status=404)
    data = request.json
    city = City(name=data['name'], url=data['url'], adminid=admin_id)
    session.add(city)
    session.commit()
    return city.as_dict()

@app.route("/admin/<admin_id>/cities")
def get_cities(admin_id):
    session = DBSession()
    admin = session.get(Admin, admin_id)
    if admin is None:
        return Response(f"Sorry, admin with id {admin_id} not found.", status=404)
    cities = session.query(City).filter_by(adminid=admin_id).all()
    return {"cities": [c.as_dict() for c in cities]}

@app.route("/admin/<admin_id>/cities/<city_id>")
def get_city_by_id(admin_id, city_id):
    session = DBSession()
    if session.get(Admin, admin_id) is None:
        return Response(f"Admin with id {admin_id} not found.", status=404)
    city = session.get(City, city_id)
    if city is None:
        return Response(f"City with id {city_id} not found.", status=404)
    return city.as_dict()

@app.route("/admin/<admin_id>/cities/<city_id>", methods=['DELETE'])
def delete_city_by_id(admin_id, city_id):
    session = DBSession()
    if session.get(Admin, admin_id) is None:
        return Response(f"Admin with id {admin_id} not found.", status=404)
    city = session.query(City).filter_by(id=city_id).first()
    if city is None:
        return Response(f"City with id {city_id} not found.", status=404)
    session.delete(city)
    session.commit()
    return Response(f"City with {city_id} deleted.", status=200)


## This is the UserCity REST API
@app.route("/users/<user_id>/cities", methods=['POST'])
def add_user_city(user_id):
    session = DBSession()
    user = session.get(User, user_id)
    if user is None:
        return Response(f"User with id {user_id} not found.", status=404)
    data = request.json
    if len(str(data['year'])) != 4:
        return Response("Please make sure the year is exactly four digits.", status=400)
    city = session.query(City).filter_by(name=data['name']).first()
    if city is None:
        return Response(f"Sorry, city with name {data['name']} not found.", status=404)
    user_city = UserCity(cityId=city.id, userId=user_id, month=data['month'], year=data['year'], weather_params=data['params'])
    session.add(user_city)
    session.commit()
    return user_city.as_dict()

@app.route("/users/<user_id>/cities")
def get_user_cities(user_id):
    session = DBSession()
    user = session.get(User, user_id)
    if user is None:
        return Response(f"Sorry, user with id {user_id} not found.", status=404)
    city_name = request.args.get('name')
    if city_name:
        city_name = city_name.strip('"')
        city = session.query(City).filter_by(name=city_name).first()
        if city is None:
            return Response(f"Sorry, city with name {city_name} not found.", status=404)
        uc = session.query(UserCity).filter_by(userId=user_id, cityId=city.id).first()
        if uc is None:
            return Response(f"No, city with name {city_name} not being tracked by user {user.name}.", status=404)
        return {"name": city.name, "month": uc.month, "year": str(uc.year), "weather_params": uc.weather_params}
    user_cities = session.query(UserCity).filter_by(userId=user_id).all()
    return {"usercities": [uc.as_dict() for uc in user_cities]}


@app.route("/logout",methods=['GET'])
def logout():
    app.logger.info("Logout called.")
    session.pop('username', None)
    app.logger.info("Before returning...")
    return render_template('index.html')


@app.route("/login", methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    my_cities = []
    if username in in_mem_user_cities:
        my_cities = in_mem_user_cities[username]
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal",
            cities=my_cities,
            name=username,
            addButton_style="display:none;",
            addCityForm_style="display:none;",
            regButton_style="display:inline;",
            regForm_style="display:inline;",
            status_style="display:none;")


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/adminlogin", methods=['POST'])
def adminlogin():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    user_cities = in_mem_cities
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal - Admin Panel",
            cities=user_cities,
            name=username,
            addButton_style="display:inline;",
            addCityForm_style="display:inline;",
            regButton_style="display:none;",
            regForm_style="display:none;",
            status_style="display:none;")


@app.route("/admin")
def adminindex():
    return render_template('adminindex.html')


if __name__ == "__main__":

    app.debug = False
    app.logger.info('Portal started...')
    app.run(host='0.0.0.0', port=5009)