#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/home/psylogic/maxapibotnew')

from src.max.repository import MaxService

asyncio.run(MaxService.delete_non_today_messages())