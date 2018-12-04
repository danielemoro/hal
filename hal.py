from slackclient import SlackClient
from pprint import pprint
import os, sys
import praw
import re
import pickle
from pprint import pprint
import commentjson
import time


class HAL():
    def __init__(self):
        self.reddit = None
        self.slack = None

        self.init_reddit()
        self.init_slack()

    def load_tokens(self):
        with open('tokens.json') as f:
            return commentjson.load(f)

    def init_reddit(self):
        tokens = self.load_tokens()
        self.reddit = praw.Reddit(client_id=tokens['client_id'],
                                  client_secret=tokens['client_secret'],
                                  password=tokens['password'],
                                  user_agent=tokens['user_agent'],
                                  username=tokens['username'])

        if self.reddit.user.me() != "daniele_moro":
            raise Exception("Could not connect to Reddit")

    def init_slack(self):
        tokens = self.load_tokens()
        slack_token = tokens['slack_token']
        self.slack = SlackClient(slack_token)

    def get_discussion_starters(self):
        def clean_text(text):
            text = text.replace("Reddit", "AI Club")
            text = text.replace("subreddit", "website")
            text = text.replace("reddit", "AI Club")
            text = text.replace("[Serious]", "")
            text = text.replace("[SERIOUS]", "")
            return text.strip()

        def has_generated(text):
            return text in pickle.load(open("sent_questions.pkl", "rb"))

        def mark_generated(text):
            qs = pickle.load(open("sent_questions.pkl", "rb"))
            qs.append(text)
            pickle.dump(qs, open("sent_questions.pkl", "wb"))

        subreddit = self.reddit.subreddit("AskReddit")
        for submission in subreddit.search('ai OR machine learning OR research'):
            question = clean_text(submission.title)
            try:
                if not has_generated(question):
                    mark_generated(question)
                    return question
            except Exception:
                pickle.dump([], open("sent_questions.pkl", "wb"))
                return question

    def clear_sent_discussion_starter(self):
        pickle.dump([], open("sent_questions.pkl", "wb"))

    def access_cache(self, name, func, update=False):
        try:
            if update:
                data = func()
                pickle.dump(data, open('cache/' + str(name) + ".pkl", 'wb'))
                return data

            return pickle.load(open('cache/' + str(name) + ".pkl", 'rb'))
        except FileNotFoundError:
            if not os.path.exists('cache/'):
                os.makedirs('cache/')

            # force update
            return self.access_cache(name, func, True)

    def find_user_name(self, user_id):
        def func():
            return self.slack.api_call("users.list", count=1000)
        user_list = self.access_cache("userlist", func)

        for mem in user_list['members']:
            if mem['id'] == user_id:
                return mem['real_name']
        return None

    def get_last_k_messages_in_channel(self, channel_id, k):
        raw_history = self.slack.api_call(
            "conversations.history",
            channel=channel_id,
            count=k
        )
        try:
            return raw_history['messages']
        except Exception:
            print(raw_history)

    def find_channel_id(self, channel_name):
        def func():
            return self.slack.api_call("conversations.list", types="public_channel, private_channel, mpim, im")["channels"]
        raw_channels = self.access_cache("raw_channels", func)

        channels = {}
        for c in raw_channels:
            if 'name' in c:
                channels[c['name']] = c['id']
            else:
                user_name = self.find_user_name(c['user'])
                if user_name is not None:
                    channels[user_name] = c['id']
                else:
                    channels[c['id']] = c['id']
        try:
            return channels[channel_name]
        except Exception:
            return None

    def send_message(self, channel, message):
        channel_id = self.find_channel_id(channel)
        result = self.slack.api_call("chat.postMessage", channel=channel_id, text=message)
        if not result['ok']:
            return result
        else:
            return True

    def next_question(self, destination_channel, admin):
        admin_channel_id = self.find_channel_id(admin)

        question = self.get_discussion_starters()
        print("Asking {} if I can sent {}".format(admin, question))
        self.send_message(admin, "Can I send this message to {}?".format(destination_channel))
        self.send_message(admin, question)

        def check_if_approved():
            last_messages = self.get_last_k_messages_in_channel(admin_channel_id, 1)
            for m in last_messages:
                if 'user' in m:
                    print("Found response from", admin, ": ", m['text'])
                    if m['text'].lower() in ['yes', 'good', 'ok', 'sure', 'yep']:
                        print("Sending", question, "to", destination_channel)
                        self.send_message(admin, "SENDING")
                        if not self.send_message(destination_channel, question):
                            print("FAILED")
                    elif m['text'].lower() in ['quit', 'stop']:
                        print("GOODBYE")
                        self.send_message(admin, "GOODBYE")
                        sys.exit()
                    else:
                        self.send_message(admin, "NOT SENDING")
                        self.next_question(destination_channel, admin)
                    return True
            print("No response...")
            return False

        waiting = True
        count = 2
        while waiting:
            count += 1
            time.sleep(count ** 2)
            if check_if_approved():
                return

    def start(self, destination_channel="Daniele Moro", admin="Daniele Moro", interval=10):
        waiting = True
        while waiting:
            self.next_question(destination_channel=destination_channel, admin=admin)
            time.sleep(interval)

hal = HAL()
dan = hal.start()
