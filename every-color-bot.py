# This bot posts all 16.8 million 24-bit colours to Mastodon, 
# 1 per hour, potentially for 1914 years starting 2023.
#
# Author: https://mastodon.social/@dig
# 
# It copies the concept from https://twitter.com/everycolorbot
# by https://mastodon.social/@vogon but reuses no code.
#
# Rather than use a Linear Feedback Shift Register from the original
# we use numpy to create a deterministic permuted set of 2^24 colors.
#
# The script is designed to be run every day from a GitHub action,
# maintaining a schedule of pre-submitted posts.

import numpy as np
import os
from datetime import datetime, timedelta
from PIL import Image
from mastodon import Mastodon
import pytz

API_BASE_URL = 'https://mastodon.bot/'
VISIBILITY = 'public' # post visibility
WINDOW = 14 # number of hourly posts to schedule

# functions to permutate the 24 bit color space

def generate_permutation(space, seed):
    rng = np.random.default_rng(seed) 
    permutation = np.arange(space)
    rng.shuffle(permutation)
    return permutation, generate_permutation_index_map(permutation)

def generate_permutation_index_map(permutation):
    index_map = np.empty_like(permutation)
    index_map[permutation] = np.arange(permutation.size)
    return index_map

def perm_inv(permutation_index_map, element):
    return permutation_index_map[element]

# lambda functions to map colors and indices

int_to_hex = lambda x: hex(x)[2:].rjust(6, '0')
hex_to_int = lambda x: int(x, 16)
hex_to_rgb = lambda x: tuple(int(x[i:i+2], 16) for i in (0, 2, 4))
idx_to_col = lambda x: int_to_hex(perm[x])
col_to_idx = lambda x: perm_inv(index_map, hex_to_int(x))
next_color = lambda x: idx_to_col(col_to_idx(x)+1)
save_image = lambda x: Image.new("RGB", (600,300), hex_to_rgb(x)).save(f"/tmp/{x}.webp",format="webp",lossless=True)

# lambda functions to manipulate datetimes

dt_to_hours_from_now = lambda x: round((x.replace(tzinfo=pytz.UTC)-datetime.utcnow().replace(tzinfo=pytz.UTC)).total_seconds()/3600)
hours_to_schedule = lambda x: WINDOW-min(WINDOW,max(0,dt_to_hours_from_now(x)))
schedule_from = lambda x: max(datetime.utcnow()-timedelta(minutes=45),x)

# mastodon functions

def login_to_mastodon():
    return Mastodon(    
        client_id=os.environ.get("CLIENT_ID", "<unknown"), 
        client_secret=os.environ.get("CLIENT_SECRET", "<unknown"), 
        access_token=os.environ.get("ACCESS_TOKEN", "<unknown"),
        api_base_url=API_BASE_URL,
        ratelimit_method='throw',
        user_agent='everycolorbot')       

def get_latest_scheduled_post_details(m):
    
    latest_dt = datetime.utcnow().replace(tzinfo=pytz.UTC)
    latest_idx = 0
    n = m.scheduled_statuses()
    while n:
        this_latest = sorted(n, key=lambda i: i["scheduled_at"], reverse=True)[0]
        if this_latest['scheduled_at'] > latest_dt:
            latest_dt = this_latest['scheduled_at']
            latest_idx = col_to_idx(this_latest['params']['text'])            
        n = m.fetch_next(n)
    return latest_dt, latest_idx

def get_latest_post_details(m):

    n = m.account_statuses(id=m.me()['id'], only_media=True, exclude_replies=True, exclude_reblogs=True, limit=40)
    
    if len(n)>0:
        return col_to_idx(sorted(n, key=lambda i: i["created_at"], reverse=True)[0]['content'][3:-4])
    return None

def schedule_post(m, sch_dt, idx):
 
    col = idx_to_col(idx)

    print(f'Scheduling {idx} = {col} for {sch_dt}')
    
    save_image(col)
    
    fn = f"/tmp/{col}.webp"
    media_id = m.media_post(fn, description=col,mime_type='image/webp',file_name=fn)

    if media_id:
        m.status_post(col, scheduled_at=sch_dt, media_ids=media_id, visibility=VISIBILITY)

def schedule_posts(m):
    d,c = get_latest_scheduled_post_details(m)
    if d<datetime.utcnow().replace(tzinfo=pytz.UTC):
        print('No scheduled posts')
        c = get_latest_post_details(m)
        d = datetime.utcnow()+timedelta(minutes=15)
        if c is None:
            print('No posts ever. Starting from the beginning.')
            c = 0
            schedule_post(m, d, c)

    num_to_sched = hours_to_schedule(d)
    if num_to_sched>0: print(f'Scheduling {num_to_sched} items starting {d+timedelta(hours=1)} from colour id {int(c)+1}')

    for i in range(1,num_to_sched+1):
        schedule_post(m, d+timedelta(hours=i), int(c)+i)
    
# run the bot once

perm, index_map = generate_permutation(2**24, 42**2)

m=login_to_mastodon()

schedule_posts(m)
