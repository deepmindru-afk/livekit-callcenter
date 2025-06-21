import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Application settings
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
APP_NAME = os.getenv('APP_NAME', 'Call Center API')

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'replacethiswithyoursecretkey')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '480'))

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./callcenter.db')

# LiveKit settings
LIVEKIT_API_KEY = os.getenv('LIVEKIT_API_KEY', 'replacewithyourapikey')
LIVEKIT_API_SECRET = os.getenv('LIVEKIT_API_SECRET', 'replacewithyourapisecret')
LIVEKIT_URL = os.getenv('LIVEKIT_URL', 'http://localhost:7880')

# If a separate WebSocket URL is provided, use it; otherwise, derive from LIVEKIT_URL
# If LIVEKIT_URL already starts with ws:// or wss://, use it as is
if os.getenv('LIVEKIT_WS_URL'):
    LIVEKIT_WS_URL = os.getenv('LIVEKIT_WS_URL')
elif LIVEKIT_URL.startswith(('ws://', 'wss://')):
    LIVEKIT_WS_URL = LIVEKIT_URL
else:
    # Convert http:// to ws:// and https:// to wss://
    LIVEKIT_WS_URL = LIVEKIT_URL.replace('http://', 'ws://').replace('https://', 'wss://')

LIVEKIT_SIP_TRUNK_ID = os.getenv('LIVEKIT_SIP_TRUNK_ID', 'ST_n7M4h5eh3ypR')
# LIVEKIT_SIP_TRUNK_ID = os.getenv('LIVEKIT_SIP_TRUNK_ID', 'ST_uQh2fSqVd487')

# Logger setup - can be expanded in the future
import logging

logger = logging.getLogger("call_center")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO if not DEBUG else logging.DEBUG) 