import praw
import re
import pickle

reddit = praw.Reddit(client_id='YCdMuTVwqiyixQ',
                     client_secret='jsViPYjEIITKpHZB0KrUu31zi2g',
                     password='danileti',
                     user_agent='testscript by /u/daniele_moro',
                     username='daniele_moro')

print(reddit.user.me())
subreddit = reddit.subreddit("AskReddit")
questions = []
for submission in subreddit.search('ai OR machine learning OR research'):
    print(submission.title)

