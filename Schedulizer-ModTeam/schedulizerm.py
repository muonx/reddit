#/u/GoldenSights
import traceback
from dateutil.parser import parse as dateparse
import string
import datetime
import time
import praw
import sqlite3
import re

""" USER CONFIG """

USERAGENT = "Schedules posts from a central subreddit to other subreddit. ~asianmovement"
#Describe the bot and what it does. Include your username
APP_ID = "nexusscheduler"
APP_SECRET = "k2ywQgk6PV6YOOacVPW0PMtsYvc"
APP_URI = "https://127.0.0.1:65010/authorize_callback"
APP_REFRESH = ""
# https://www.reddit.com/comments/3cm1p8/how_to_make_your_bot_use_oauth2/
SUBREDDIT = "Asianlife"
#This is the subreddit where the bot finds the schedules
#It should be private with only the team of moderators
TITLESEPARATOR = "||"
#This is what demarcates the timestamp from the sub from the title
#This should not be a naturally occuring part of any title
#Example: "15 December 2014 ||| GoldTesting ||| Welcome to the subreddit"
#          ^Time to post        ^Sub to post    ^Title of post
IGNORE_FLAG = "#"
#If this character is THE FIRST CHARACTER IN THE TITLE,
#The bot will ignore that post. Used for meta / discussion.

SCHEDULEDFLAIR_TEXT = "Scheduled!"
SCHEDULEDFLAIR_CSS = "scheduled"
#This flair will be assigned to the source when the source is scheduled
POSTEDFLAIR_TEXT = "Post made!"
POSTEDFLAIR_CSS = "posted"
#This flair will be assigned to the source when the post is made
MAXPOSTS = 3
#The number of items you want to get from /new. Recommended 100
ALLOWOTHEREDITS = False
#Are users allowed to edit other peoples' post schedules?
WAIT = 30
#How many seconds in between loop cycles. Completely inactive during this time.

ADMINS = ["asianmovement", "shadowsweep"]
#These are the people who will get tracebacks when the bot has problems.
TRACEBACK_SUBJECT = "SchedulizerM Error traceback"

POSTEDCOMMENT = "Your post to /r/%s has been created. %s"
#Made in the source when the post is made

FOOTER = """

_____

If any information is incorrect, reply to this comment with the incorrect key,
a colon, and new value. See the
[Bot code](https://github.com/voussoir/reddit/tree/master/Schedulizer-ModTeam)
page for examples. Only make 1 edit per line.


A foolproof time format is 
"DD Monthname YYYY HH:MM". All times are in UTC
([Timezone map](http://www.timeanddate.com/time/map/))

Deleting your post will cause it to be removed from the schedule.

If you think the bot is down, send it
[this message](http://www.reddit.com/message/compose?to=??????&subject=Ping&message=Ping).

""" # Don't forget to put your username in this message

SCHEDULECOMMENT = """

Your post has been scheduled. Please check that this information is correct:

"""
#Made in the source when the source is made

ERRORCOMMENT = """

Encountered the following errors:

%s

The post will use placeholder values until you correct the information

_______

"""

ERRORDISTINGUISHFAIL = "Attempted to distinguish post and failed."
ERRORSTICKYFAIL = "Attempted to sticky post and failed."
ERRORDATETIME = '!! DateTime: Could not understand time format, or date is invalid. You entered: `%s`'
ERRORTOOEARLY = '!! DateTime: The time you have entered is before present time. You entered `%s`'
ERRORTITLEFORM = '!! Title: Title expected 3 attributes separated by `' + TITLESEPARATOR + '`'
ERRORLONGTITLE = "!! Title: Your title is too long. Max 300 characters, you have %d"
ERRORSUBREDDIT = '!! Reddit: Subbreddit /r/%s could not be found'
ERRORNOTALLOWED = "!! Reddit: Bot is not allowed to submit to /r/%s."
ERRORUNKNOWNCOMMAND = "Did not understand the command: `%s`"
ERRORCRITICAL = '\n\nBecause of a critical post error, your chosen timestamp has been forfeited. You will need to edit it along with the other keys.\n\n'

IMPOSSIBLETIME = 2147483646
""" All done! """

try:
	import bot
	USERAGENT = bot.aG
except ImportError:
	pass

print('Loading database')
sql = sqlite3.connect('sql.db')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS schedules(ID TEXT, TIME INT, REDDIT TEXT, TITLE TEXT, DIST INT, STICKY INT, FLAIR TEXT, FLCSS TEXT, POST TEXT)')
#                                                   0         1          2            3          4         5           6           7           *
cur.execute('CREATE INDEX IF NOT EXISTS schedule_idindex ON schedules(id)')
cur.execute('CREATE INDEX IF NOT EXISTS schedule_postindex ON schedules(post)')
sql.commit()

print('Logging in')
r = praw.Reddit(USERAGENT)
r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
r.refresh_access_information(APP_REFRESH)


def getTime(bool):
	timeNow = datetime.datetime.now(datetime.timezone.utc)
	timeUnix = timeNow.timestamp()
	if bool is False:
		return timeNow
	else:
		return timeUnix

def processpost(inputpost):
	if isinstance(inputpost, str):
		if 't3_' not in inputpost:
			inputpost = 't3_' + inputpost
		inputpost = r.get_info(thing_id=inputpost)
	sourceid = inputpost.id
	print('Schedulizing post ' + sourceid)
	nowstamp = getTime(True)
	sourcetitle = inputpost.title
	sourcesplit = sourcetitle.split(TITLESEPARATOR)
	errors = []
	critical = False
	dosticky = 0
	dodist = 0
	try:
		posttime = "?"
		postsub = "?"
		posttitle = "?"
		postflair = ""
		postflcss = ""
		posttime = sourcesplit[0]
		postsub = sourcesplit[1]
		postsub = postsub.replace('/r/', '')
		if '[d]' in postsub.lower():
			dodist = 1
		if '[s]' in postsub.lower():
			dosticky = 1

		regex = re.search("\[f:[^\]]*\]", postsub, re.IGNORECASE)
		if regex:
			postflair = regex.group(0)
			postflair = postflair[3:-1]

		regex = re.search("\[fc:[^\]]*\]", postsub, re.IGNORECASE)
		if regex:
			postflcss = regex.group(0)
			postflcss = postflcss[4:-1]
		elif postflair != "":
			postflcss = removespecial(postflair)

		postsubsplit = postsub.split(' ')
		while '' in postsubsplit:
			postsubsplit.remove('')
		postsub = postsubsplit[0]
		posttitle = '||'.join(sourcesplit[2:])
	except IndexError:
		errors.append(ERRORTITLEFORM)
		critical = True

	try:
		posttimerender = dateparse(posttime)
		posttimerender = posttimerender.replace(tzinfo=datetime.timezone.utc)
		posttimestamp = posttimerender.timestamp()
		if posttimestamp < nowstamp:
			errors.append(ERRORTOOEARLY % posttime)
			critical = True
	except:
		#December 31, 2500
		posttimestamp = IMPOSSIBLETIME
		errors.append(ERRORDATETIME % posttime)
		critical = True

	try:
		validatesubreddit(postsub)
	except:
		errors.append(ERRORSUBREDDIT % postsub)
		critical = True

	#ID TEXT, TIME INT, REDDIT TEXT, TITLE TEXT, DIST INT, STICKY INT, FLAIR TEXT, FLCSS TEXT, POST TEXT
	#  0         1          2            3          4         5           6           7           8

	if critical:
		posttimestamp = IMPOSSIBLETIME
	datalist = [sourceid, posttimestamp, postsub, posttitle, dodist, dosticky, postflair, postflcss, "None"]
	cur.execute('SELECT * FROM schedules WHERE ID=?', [sourceid])
	fetch = cur.fetchone()
	if not fetch:
		cur.execute('INSERT INTO schedules VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)', datalist)
		sql.commit()

		schedulecomment = buildcomment(datalist, errors, critical)
		print('Writing comment')
		inputpost.add_comment(schedulecomment)
		inputpost.set_flair(flair_text=SCHEDULEDFLAIR_TEXT, flair_css_class=SCHEDULEDFLAIR_CSS)

def updatepost(comment):
	source = comment.submission
	print('Updating schedule for ' + source.id + ' via comment ' + comment.id)
	pauthor = source.author.name
	cauthor = comment.author.name
	if ALLOWOTHEREDITS or (pauthor == cauthor) or any(pauthor.lower() == admin.lower() for admin in ADMINS):
		cur.execute('SELECT * FROM schedules WHERE ID=?', [source.id])
		data=cur.fetchone()
		if data:
			data= list(data)
			errors = []
			commentsplit = comment.body.split('\n')
			while '' in commentsplit:
				commentsplit.remove('')
			for line in commentsplit:
				line = line.split(':')
				line[0] = line[0].replace(' ', '')
				command = line[0].lower()
				arg = ':'.join(line[1:])
				if command in ['time', 'timestamp']:
					try:
						posttimerender = dateparse(arg)
						posttimerender = posttimerender.replace(tzinfo=datetime.timezone.utc)
						posttimestamp = posttimerender.timestamp()
					except:
						#December 31, 2500
						posttimestamp = IMPOSSIBLETIME
						errors.append(ERRORDATETIME % posttime)
					data[1] = posttimestamp

				elif command in ['reddit', 'subreddit', 'sr']:
					try:
						arg = arg.replace(' ', '')
						arg=arg.replace('/r/', '')
						validatesubreddit(arg)
					except:
						#This will be errored in the upcoming `ispostvalid` line
						pass
					data[2] = arg
				elif command in ['title']:
					data[3] = arg
				elif command in ['distinguish', 'dist', 'd']:
					if arg.lower() in ['0', 'no', 'false', 'off']:
						arg = 0
					if arg.lower() in ['1', 'yes', 'true', 'on']:
						arg = 1
					data[4] = arg
				elif command in ['sticky', 's']:
					if arg.lower() in ['0', 'no', 'false', 'off']:
						arg = 0
					if arg.lower() in ['1', 'yes', 'true', 'on']:
						arg = 1
					data[5] = arg
				elif command in ['flair-text', 'flairtext', 'flair_text']:
					data[6] = arg
				elif command in ['flair-css', 'flaircss', 'flair_css']:
					data[7] = removespecial(arg)
				else:
					errors.append(ERRORUNKNOWNCOMMAND % command)

		print('\tChecking schedule validity')
		status = ispostvalid(data, errors)
		if status[0] is False:
			data[1] = IMPOSSIBLETIME
			critical = True
		else:
			critical = False
		schedulecomment = buildcomment(data[:], errors, critical)
		print('\tWriting comment')
		comment.reply(schedulecomment)
		cur.execute('DELETE FROM schedules WHERE ID=?', [source.id])
		cur.execute('INSERT INTO schedules VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
		sql.commit()
		print('\tDone.')
	else:
		print(cauthor + ' may not edit ' + pauthor + "'s post")

def validatesubreddit(sr):
	#This will intentionall crash if /r/sr does not exist
	sr = sr.replace('/r/', '')
	sr = sr.replace('r/', '')
	sr = sr.replace('/', '')
	r.get_subreddit(sr, fetch=True)

def ispostvalid(inputdata, errors):
	nowstamp = getTime(True)
	status = True
	if inputdata[1] < nowstamp:
		n = datetime.datetime.utcfromtimestamp(inputdata[1])
		n = datetime.datetime.strftime(n, "%B %d %Y %H:%M")
		errors.append(ERRORTOOEARLY % n)
		status = False
	try:
		validatesubreddit(inputdata[2])
	except:
		print('\tBad subreddit: ' + inputdata[2])
		errors.append(ERRORSUBREDDIT % inputdata[2])
		status = False
	if len(inputdata[3]) > 300:
		errors.append(ERRORLONGTITLE % len(inputdata[3]))
		status = False
	return [status, errors]

def buildcomment(datalist, errors, critical=False):
	schedulecomment = SCHEDULECOMMENT
	if len(errors) > 0:
		errors = "\n\n".join(errors)
		schedulecomment = ERRORCOMMENT % errors
	if critical:
		schedulecomment += ERRORCRITICAL
	schedulecomment += buildtable(datalist)
	schedulecomment += FOOTER
	return schedulecomment
#ID TEXT, TIME INT, REDDIT TEXT, TITLE TEXT, DIST INT, STICKY INT, FLAIR TEXT, FLCSS TEXT, POST TEXT
#  0         1          2            3          4         5           6           7           8
def buildtable(inputdata):
	print(inputdata[1], type(inputdata[1])) #Troubleshooting with Apex
	
	timeobj = datetime.datetime.utcfromtimestamp(inputdata[1])
	inputdata[1] = datetime.datetime.strftime(timeobj, "%B %d %Y %H:%M UTC")
	inputdata[2] = '/r/' + inputdata[2]
	inputdata[3] = '`' + inputdata[3] + '`'
	inputdata[4] = "True" if inputdata[4] == 1 else "False"
	inputdata[5] = "True" if inputdata[5] == 1 else "False"
	inputdata = inputdata[1:-1]
	table = """
	Key | Value
	:- | :-
	Time | {0}
	Subreddit | {1}
	Title | {2}
	Distinguish | {3}
	Sticky | {4}
	Flair-text | {5}
	Flair-CSS | {6}
	""".format(*inputdata)
	return table

def removespecial(inputstr):
	ok = string.ascii_letters + string.digits
	outstr = "".join([x for x in inputstr if x in ok])
	return outstr

def manage_new():
	print('Managing ' + SUBREDDIT + '/new')
	subreddit = r.get_subreddit(SUBREDDIT)
	new = list(subreddit.get_new(limit=MAXPOSTS))
	for post in new:
		pid = post.id
		cur.execute('SELECT * FROM schedules WHERE ID=?', [pid])
		if not cur.fetchone():
			if post.title[0] != IGNORE_FLAG:
					processpost(post)
			else:
				data = [post.id, 1, "", "", 0, 0, "", "", "meta"]
				cur.execute('INSERT INTO schedules VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)', data)
				sql.commit()

def manage_unread():
	print('Managing inbox')
	inbox = list(r.get_unread(limit=100))
	for message in inbox:
		if isinstance(message, praw.objects.Message):
			if "ping" in message.subject.lower():
				message.reply("Pong")
				print('Responding to ping')
			try:
				mauthor = message.author.name
				if any(mauthor.lower() == admin.lower() for admin in ADMINS):
					if "kill" in message.subject.lower():
						alertadmins("Hard shutdown", "The bot is being killed by " + mauthor)
						quit()
			except AttributeError:
				pass
		elif isinstance(message, praw.objects.Comment):
			commentsub = message.subreddit.display_name
			if commentsub.lower() == SUBREDDIT.lower():
				updatepost(message)

		message.mark_as_read()

def manage_schedule():
	print('Managing schedules')
	cur.execute('SELECT * FROM schedules WHERE POST =?', ['None'])
	fetch = cur.fetchall()
	fetch = list(fetch)
	fetch.sort(key=lambda x: x[1])

	reread = False
	idlist = ['t3_'+i[0] for i in fetch]
	submissionlist = []
	print('Checking for deletions')
	while len(idlist) > 0:
		submissionlist += r.get_info(thing_id=idlist[:100])
		idlist = idlist[100:]
	for item in submissionlist:
		if (not item.author) or (item.banned_by):
			print('\t' + item.id + ' has been deleted')
			cur.execute('DELETE FROM schedules WHERE ID=?', [item.id])
			sql.commit()
			reread = True

	if reread:
		cur.execute('SELECT * FROM schedules WHERE POST =?', ['None'])
		fetch = cur.fetchall()
		fetch = list(fetch)
		fetch.sort(key=lambda x: x[1])


	nowstamp = getTime(True)
	for schedule in fetch:
		postid = schedule[0]
		print('Checking schedule ' + postid, end="")
		posttime = int(schedule[1])
		if posttime < nowstamp:
			print()
			print('\tPreparing to post')
			post = r.get_info(thing_id="t3_" + postid)
			ptitle = schedule[3]
			psub = schedule[2]
			print('\tSubmitting post')
			try:
				if post.is_self:
					pbody = post.selftext
					newpost = r.submit(psub, ptitle, text=pbody)
				else:
					purl = post.url
					newpost = r.submit(psub, ptitle, url=purl, resubmit=True)
				errors = []
				if schedule[4] == 1:
					try:
						print('\tDistinguishing')
						newpost.distinguish()
					except:
						print('\tDistinguish failed')
						errors.append(ERRORDISTINGUISHFAIL)
				if schedule[5] == 1:
					try:
						print('\tStickying')
						newpost.sticky()
					except:
						print('\tSticky failed')
						errors.append(ERRORSTICKYFAIL)
				if schedule[6] != "" or schedule[7] != "":
					try:
						print('\tFlairing')
						newpost.set_flair(flair_text=schedule[6], flair_css_class=schedule[7])
					except:
						print('\tFlair failed')
				newsub = newpost.subreddit.display_name
				newlink = newpost.short_link
				newid = newpost.id
				newcomment = POSTEDCOMMENT % (newsub, newlink)
				newcomment += '\n\n'.join(errors)
				cur.execute('UPDATE schedules SET POST=? WHERE ID=?', [newid, postid])
				sql.commit()
				print('Flairing source.')
				post.add_comment(newcomment)
				post.set_flair(flair_text=POSTEDFLAIR_TEXT, flair_css_class=POSTEDFLAIR_CSS)

			except praw.errors.APIException as error:
				if error.error_type == "SUBREDDIT_NOTALLOWED":
					print("\tNOT ALLOWED IN SUBREDDIT!")
					cur.execute('UPDATE schedules SET TIME=? WHERE ID=?', [IMPOSSIBLETIME, postid])
					sql.commit()
					scheduledata = list(schedule)
					scheduledata[1] = IMPOSSIBLETIME
					comment=buildcomment(scheduledata, [ERRORNOTALLOWED%psub], critical=True)
					post.add_comment(comment)
						
		else:
			print(" : T-" + str(round(posttime - nowstamp)))

def alertadmins(messagesubject, messagetext):
	for admin in ADMINS:
		print('Messaging ' + admin)
		try:
			r.send_message(admin, messagesubject, messagetext)
		except:
			print('COULD NOT MESSAGE ADMIN')


while True:
	try:
		manage_new()
		manage_unread()
		manage_schedule()
	except Exception as e:
		error_message = traceback.format_exc()
		print(error_message)
		now = getTime(False)
		now = datetime.datetime.strftime(now, "%B %d %H:%M:%S UTC")
		error_message = '    ' + error_message
		error_message = error_message.replace('\n', '\n    ')
		error_message += '\n' + str(now)
		alertadmins(TRACEBACK_SUBJECT, error_message)
	print("Sleeping\n")
	time.sleep(WAIT)
