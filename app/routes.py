from app import app, login_manager, db
from api_functions import ApiFunc
import json
import requests
import random
from typing import Union
    

if __name__ == '__main__':
    app.run(debug=True)