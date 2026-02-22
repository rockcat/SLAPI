from env import read_env
from wifi import connect_wifi
from slapi import start_slapi

env = read_env()
connect_wifi(env.get('SSID',''),  env.get('PASSWORD',''))
start_slapi()
