#/u/GoldenSights
import praw # simple interface to the reddit API, also handles rate limiting of requests
import urllib.request
import time
import sqlite3
import os

'''USER CONFIGURATION'''

APP_ID = ""
APP_SECRET = ""
APP_URI = ""
APP_REFRESH = ""
# https://www.reddit.com/comments/3cm1p8/how_to_make_your_bot_use_oauth2/
USERAGENT = ""
#This is a short description of what the bot does. For example "/u/GoldenSights' Newsletter Bot".
SUBREDDIT = "imgur"
#This is the sub or list of subs to scan for new posts. For a single sub, use "sub1". For multiple subreddits, use "sub1+sub2+sub3+..."

DOMAINS = ["imgur.com"]
#Domains from which the bot will download images

FILENAME = "_counter_ _subreddit_ _redditid_"
#The name of the file
#Extension will be added automatically
#You may use these following injectors to create dynamic titles:
#_redditid_ = The 6 digit ID of the reddit post
#_imgurid_ = The 7 digit ID of the imgur image
#_subreddit_ = The name of the subreddit it was posted in
#_title_ = The title of the reddit post. Certain characters will be stripped for Windows reasons
#_counter_ = A counter which will tick upward by 1 every time.

FILEPATH = "Images"
#The path where images will be saved.
#If only a folder name is mentioned, the folder will be in the same directory as this .py file
#If you wish to hardcode a path, you must use double slashes; ex: "C:\\Users\\"
LEADINGZEROS = 3
#If you use the counter, you may want the number to have leading zeros.

ALBUMSUBFOLDERS = True
#When downloading an album, should all its images be put in a subfolder under the album's ID?

MAXPOSTS = 100
#This is how many posts you want to retrieve all at once. PRAW can download 100 at a time.
WAIT = 20
#This is how many seconds you will wait between cycles. The bot is completely inactive during this time.


'''All done!'''


WAITS = str(WAIT)
try:
    import bot
    USERAGENT = bot.aG
except ImportError:
    pass

sql = sqlite3.connect('sql.db')
print('Loaded SQL Database')
cur = sql.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS oldposts(NAME TEXT, ID TEXT)')
cur.execute('CREATE INDEX IF NOT EXISTS oldpost_index ON oldposts(id)')
print('Loaded Completed table')

sql.commit()

r = praw.Reddit(USERAGENT)
r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
r.refresh_access_information(APP_REFRESH)

if not os.path.exists(FILEPATH):
    print('Folder ' + FILEPATH + ' was not found and is being created.')
    os.makedirs(FILEPATH)

cur.execute('SELECT * FROM oldposts WHERE NAME=?', ['countervar'])
f = cur.fetchone()
if not f:
    print('SQL database is new. Setting Counter to 0')
    cur.execute('INSERT INTO oldposts VALUES(?,?)', ['countervar', '0'])
    COUNTER = 0
else:
    COUNTER = int(f[1])
    print('Counter = ' + str(COUNTER))

def determinefiletype(path):
    #I don't know what I'm doing.
    filea = open(path, 'rb')
    a = filea.read()
    filea.close()
    b = list(a[:4])
    if b[:3] == [255, 216, 255]:
        return '.jpg'
    if b[:4] == [137, 80, 78, 71]:
        return '.png'
    if b[:3] == [71, 73, 70]:
        return '.gif'
    else:
        return '.jpg'

def readalbum(pid, purl, subreddit, rtitle):
    #I DON'T KNOW WHAT I'M DOING
    l = []
    print('Reading HTML for album page')
    reada = urllib.request.urlopen(purl)
    a = reada.readlines()
    reada.close()
    for line in a:
        line = str(line, encoding='utf-8')
        if '#' not in purl:
            if 'view full resolution' in line.lower():
                l.append('http://i.imgur.com/' + line.strip().split('"')[1].split('/')[-1])
        else:
            if 'data-src' in line.lower():
                print('http://i.imgur.com/' + line.strip().split('"')[9].split('/')[-1].replace('s.', '.'))
                l.append('http://i.imgur.com/' + line.strip().split('"')[9].split('/')[-1].replace('s.', '.'))


    print('Found ' + str(len(l)) + ' items')
    name = purl.split('/')[-1].split('#')[0]
    for image in l:
        print('\tFound ' + image)
        downloadimage(pid, image, subreddit, False, rtitle, albumname=name)



def downloadimage(pid, purl, subreddit, mustrename, rtitle, albumname=""):
    global COUNTER
    fileextension = '.' + purl.split('.')[-1]
    imgurid = purl.split('/')[-1].replace(fileextension, '')
    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        rtitle = rtitle.replace(char, '')
    filename = FILENAME
    filename = filename.replace('_counter_', ("%0" + str(LEADINGZEROS+1) + "d") % COUNTER)
    filename = filename.replace('_redditid_', pid)
    filename = filename.replace('_imgurid_', imgurid)
    filename = filename.replace('_subreddit_', subreddit)
    filename = filename.replace('_title_', rtitle)

    if ALBUMSUBFOLDERS is True and albumname != "":
        if not os.path.exists(FILEPATH + '\\' + albumname):
            os.makedirs(FILEPATH + '\\' + albumname)
        filename = albumname + '\\' + filename

    fullpath = FILEPATH + "\\" +  filename + fileextension

    print('\tImgur ID:', imgurid, '|| Extension:', fileextension)
    print('\tDownloading image to', '"' + fullpath + '"\n')

    try:
        urllib.request.urlretrieve(purl, fullpath)
    except Exception as e:
        print('DOWNLOAD FAILED')
        print(e)

    if mustrename is True:
        fileextension = determinefiletype(fullpath)
        print('\tFixing filename to ' + fileextension)
        os.rename(fullpath, fullpath.replace('.jpg', fileextension))

    COUNTER +=1
    cur.execute('UPDATE oldposts SET ID=? WHERE NAME=?', [COUNTER, 'countervar'])
    #print('\tTicked Counter')
    sql.commit()


def scanSub():
    global COUNTER
    print('Searching '+ SUBREDDIT + '.')
    subreddit = r.get_subreddit(SUBREDDIT)
    posts = subreddit.get_new(limit=MAXPOSTS)
    for post in posts:
        pid = post.id
        cur.execute('SELECT * FROM oldposts WHERE ID=?', [pid])
        if not cur.fetchone():
            purl = post.url
            if any(domain.lower() in purl.lower() for domain in DOMAINS):
                print(pid, purl)
                mustrename = False

                if 'imgur' in purl and 'i.imgur' not in purl and 'imgur.com/a/' not in purl:
                    purl = purl.replace('imgur', 'i.imgur')
                    purl = purl.replace('gallery/', '') + '.jpg'
                    print('\tIndirect link. Assuming .jpg file format')
                    mustrename = True

                if 'imgur.com/a/' in purl:
                    readalbum(pid, purl, post.subreddit.display_name, post.title)

                else:
                    downloadimage(pid, purl, post.subreddit.display_name, mustrename, post.title)

            cur.execute('INSERT INTO oldposts VALUES(?,?)', ['post', pid])
        sql.commit()



while True:
    try:
        scanSub()
    except Exception as e:
        print('An error has occured: ', e)
    print('Running again in ' + WAITS + ' seconds \n')
    sql.commit()
    time.sleep(WAIT)