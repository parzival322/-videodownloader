from datetime import datetime
from fastapi import FastAPI
from api_functions import ApiFunc

# инициализация приложения, БД, миграции и логин-менеджера

app = FastAPI()


from app import database
from app import routes
