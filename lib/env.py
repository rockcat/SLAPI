
ENV_FILE = '.env'

env = {}

def read_env():
    # read SSID and PASSWORD from env.txt
    env_file = open(ENV_FILE, 'r')
    env_lines = env_file.readlines()    
    env_file.close()
    env ={}
    for line in env_lines:
        if (line.strip() == '') or (line.startswith('#')):
            continue
        key, value = line.strip().split('=', 1)
        env[key] = value
    return env

