import slack
import os
from pathlib import Path
from dotenv import load_dotenv
import re,time,feedparser
import datetime
import pytz


class HakkiBey():

    def __init__(self, cleaner=False):

        env_path = Path('.') / '.editorconfig'
        load_dotenv(dotenv_path=env_path)
        self.user_client = slack.WebClient(token=os.environ['USER_TOKEN'])
        self.bot_client  = slack.WebClient(token=os.environ['BOT_TOKEN'])
        self.expired_threshold = int(os.environ['EXPIRED_THRESHOLD']) #mins
        self.cycle_time = int(os.environ['CYCLE_TIME']) #mins
        self.feed_url = os.environ['FEED_URL']
        self.msg_to_track = {}
        self.cleaner_on = cleaner

    def message_parsing(self):

        user_client = self.user_client
        current_time = datetime.datetime.now(pytz.UTC)
        msg_to_track = {}

        if self.msg_to_track:
            for id,value in self.msg_to_track.items():
                b=current_time
                a=value.replace(tzinfo=pytz.UTC)
                time_passed = (current_time - a).total_seconds()
                time_passed_in_min = round(time_passed / 60)
                if time_passed_in_min >= self.expired_threshold:
                    user_client.chat_delete(channel='C01DA5NPHDH', ts=id)
                else:
                    msg_to_track.update({id:value})
        self.msg_to_track = msg_to_track

    def delete_messages(self):

        user_client = self.user_client
        message_data = user_client.conversations_history(channel='C01DA5NPHDH').data
        active_messages = message_data['messages']

        timestamp_list = [m['ts'] for m in active_messages]
        for d, i in enumerate(timestamp_list):
            try:
                user_client.chat_delete(channel='C01DA5NPHDH', ts=i)
            except:
                pass
            time.sleep(1.5)

    def main(self):

        if self.cleaner_on:
            self.delete_messages()
        client = self.bot_client
        list_of_words = ['data analysis', 'data extraction', 'automation', 'automated', 'bot', 'scraper', 'scraped',
                         'scraping', 'scrape', 'stock', 'email', 'Scripting &amp; Automation', 'Web Scraper']

        hr=r'Hourly Range</b>:.+\n\n<br'
        posted =r'Posted On</b>: .+UTC'
        cat=r'Category</b>:.+<br />'
        skills=r'Skills</b>:.+'
        budget=r'Budget</b>:.+'
        urls=[]
        d=0
        current_local_time = datetime.datetime.now(pytz.timezone('Turkey')).strftime('%H:%M')
        now = datetime.datetime.now()
        minutes = -self.cycle_time
        hours_added = datetime.timedelta(minutes=minutes)
        last_time = now + hours_added

        while True:

            self.message_parsing()
            start = datetime.datetime.now()
            last_time_check = (start - last_time).total_seconds()/60
            if last_time_check > self.cycle_time:
                entries=[]
                nfeed = feedparser.parse(self.feed_url)
                print(f"\rFeed status: {nfeed['status']} /// # of entries: {len(nfeed.entries)} /// Last time parsed: {current_local_time}",end='\n')
                current_local_time = datetime.datetime.now(pytz.timezone('Turkey')).strftime('%H:%M')

                for n in nfeed.entries:
                    try:
                        hr_val=re.compile(hr).findall(n['summary'])[0].replace('</b>','').replace('\n','').replace('<br','').replace('<br />','').split(': ')[1]
                    except:
                        try:
                            hr_val=re.compile(budget).findall(n['summary'])[0].replace('</b>','').replace('\n','').replace('<br','').replace('<br />','').split(': ')[1]
                        except:
                            hr_val=''


                    posted_val=re.compile(posted).findall(n['summary'])[0].replace('</b>','').replace('\n','').replace('<br','').replace('<br />','').split(': ')[1]
                    date_time_obj = datetime.datetime.strptime(posted_val, '%B %d, %Y %H:%M UTC')
                    utc_time = date_time_obj
                    hours = 3
                    hours_added = datetime.timedelta(hours=hours)
                    posted_val = date_time_obj + hours_added
                    posted_val = posted_val.strftime('%H:%M')
                    try:
                        cat_val=re.compile(cat).findall(n['summary'])[0].replace('</b>','').replace('\n','').replace('<br','').replace('<br />','').replace('/>','').split(': ')[1]
                    except:
                        cat_val=''

                    try:
                        skills_val=re.compile(skills).findall(n['summary'])[0].replace('</b>','').replace('\n','').replace('<br','').replace('<br />','').split(':')[1]
                    except:
                        skills_val=''
                    url=n['id']
                    txt=n['summary'].split('<br />')[0].replace('<br />','').replace('<b>','').replace('&#039;',"'").replace('&nbsp;','')
                    target_title = [True if k in n['title'].lower() else False for k in list_of_words]
                    target_cat = [True if k in cat_val.lower().split(',') else False for k in list_of_words]
                    target_skills = [True if k in skills_val.lower().split(',') else False for k in list_of_words]
                    if any(target_title) or any(target_cat) or any(target_skills):
                        if url not in urls:
                            pr = [utc_time,f":pushpin:\n\n*{n['title']}*\n>\n\n```{txt}```\n\nPosted On: {posted_val}\nBudget: `{hr_val}`\nURL: <{url}|Job *Link*:bomb:>\n\n--------------------------------------------------"]
                            urls.append(url)
                            entries.append(pr)

                if entries:
                    entries.reverse()
                    current_time = datetime.datetime.now(pytz.UTC)
                    for d,entry in enumerate(entries):
                        entry_timestamp, entry_text= entry[0], entry[1]
                        time_passed = (current_time - entry_timestamp.replace(tzinfo=pytz.UTC)).total_seconds()
                        time_passed_in_min = round(time_passed / 60)
                        tracker = f"{entry_timestamp} - {time_passed_in_min}"
                        if time_passed_in_min < self.expired_threshold:
                            if len(entries)<3:
                                entry_edit = entry_text + '@berkaygokova'
                                msg = client.chat_postMessage(channel='#upwork', text=entry_edit, link_names = 1)
                                self.msg_to_track.update({msg['ts']: entry_timestamp})
                                #time.sleep(0.1)
                            else:
                                msg = client.chat_postMessage(channel='#upwork', text=entry_text)
                                self.msg_to_track.update({msg['ts']:entry_timestamp})
                            time.sleep(0.1)
                    last_time = datetime.datetime.now()
                if len(urls) % 250 == 0:
                    urls=[]
                d+=1
            print(f"\rCurrent Date: {datetime.datetime.now()} / Last check: {last_time_check}", end='')
session = HakkiBey(cleaner=True)
session.main()