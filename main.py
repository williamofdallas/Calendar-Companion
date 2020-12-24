from datetime import date
from datetime import datetime
from datetime import timedelta
import pickle
import os.path
from google.auth.transport.requests import Request
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivymd.uix.list import OneLineIconListItem, MDList
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.list import MDList
from kivy.uix.screenmanager import ScreenManager, Screen


# this is copied and pasted from the google.py source code because I couldn't figure out how to import the module

def Create_Service(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print(e)
        return None


client_secret_file = 'client_secret.json'
api_name = 'calendar'
api_version = 'v3'
scopes = ['https://www.googleapis.com/auth/calendar']

service = Create_Service(client_secret_file, api_name, api_version, scopes)


class ContentNavigationDrawer(BoxLayout):
    pass


class ItemDrawer(OneLineIconListItem):
    icon = StringProperty()
    target = StringProperty()


class DrawerList(ThemableBehavior, MDList):
    def set_color_item(self, instance_item):
        """Called when tap on a menu item."""

        # Set the color of the icon and text for the menu item.
        for item in self.children:
            if item.text_color == self.theme_cls.primary_color:
                item.text_color = self.theme_cls.text_color
                break
        instance_item.text_color = self.theme_cls.primary_color


class TransitionScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


class CalendarCompanionApp(MDApp):
    # this function defines the variables that will be passed between other functions
    # (most of these will be passed between the "refreshed",  "transition", and "squish" functions)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_0_id = None
        self.event_0_end_time = None
        self.event_1_id = None
        self.agenda = None
        self.transition_time = None

    def build(self):
        return Builder.load_file("main.kv")

    def openScreen(self, itemdrawer):
        self.openScreenName(itemdrawer.target)
        self.root.ids.nav_drawer.set_state("close")

    def openScreenName(self, screenName):
        self.root.ids.screen_manager.current = screenName

    def on_start(self):
        self.root.ids.content_drawer.ids.md_list.add_widget(
            ItemDrawer(target="transition", text="Transition Screen",
                       icon="play-outline",
                       on_release=self.openScreen)
        )
        self.root.ids.content_drawer.ids.md_list.add_widget(
            ItemDrawer(target="agenda", text="Agenda",
                       icon="view-agenda-outline",
                       on_release=self.openScreen)
        )
        self.root.ids.content_drawer.ids.md_list.add_widget(
            ItemDrawer(target="report", text="Report",
                       icon="newspaper-variant-outline",
                       on_release=self.openScreen)
        )
        self.root.ids.content_drawer.ids.md_list.add_widget(
            ItemDrawer(target="settings", text="Settings",
                       icon="settings-outline",
                       on_release=self.openScreen)
        )

        self.theme_cls.primary_palette = 'Gray'
        self.theme_cls.primary_hue = '300'
        self.refresh()

    def interrupt(self):
        print('new event!')

    def skip(self):
        print('skip event!')

    def refresh(self):

        # there needs to be a datetime now and a string utcnow, both with the same timestamp
        # datetime is used for displays and other calculations, utcnow is used for interacting with the calendar API

        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

        print(now)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        midnighttonight = datetime.combine(tomorrow, datetime.min.time()) + timedelta(hours=6)
        midnighttonight = midnighttonight.isoformat() + 'Z'

        print(now)
        print(midnighttonight)

        # grabs next agenda, until midnight
        agenda_result = service.events().list(calendarId='primary',
                                              timeMin=now,
                                              timeMax=midnighttonight,
                                              singleEvents=True,
                                              orderBy='startTime').execute()
        self.agenda = agenda_result.get('items', [])

        eventnumber = len(self.agenda)

        print(eventnumber)

        # creates/refreshes lists
        event_display_list = []
        event_id_list = []
        event_end_time_list = []
        event_description_list = []
        priority_value_list = []
        minimum_value_list = []

        eventnumber = 0

        # this part grabs the variables I want (ID's, titles, and start times), formats them, and indexes them as lists
        for event in self.agenda:

            event_end_time = event['end'].get('dateTime')
            event_end_time_list.append(event_end_time)

            event_id = event['id']
            event_id_list.append(event_id)

            # gets title of event
            event_title = event['summary']

            # gets description of event, and assigns it as blank if there is no description
            if 'description' in event:
                event_description = event['description']
            else:
                event_description = ''

            print(event_description)

            priority_value_indicator = "#priority:(\w+)"

            # gets first priority value, and assigns 0 if not specified
            priority_values_mentioned = re.findall(priority_value_indicator, event_description)

            if '#priority:' in event_description:
                priority_value = priority_values_mentioned[0]
            else:
                priority_value = 0
            priority_value_list.append(priority_value)

            # printing the hashtag_list
            print("priority value is:")
            print(priority_value)

            # finds minimum duration threshold value by searching for "#minimum:"
            minimum_value_indicator = "#minimum_duration:(\w+)"

            # gets priority value, and assigns 0 if not specified
            minimum_values_mentioned = re.findall(minimum_value_indicator, event_description)

            if '#minimum_duration:' in event_description:
                minimum_value = minimum_values_mentioned[0]
            else:
                minimum_value = 0

            # printing the hashtag_list
            print("minimum duration is:")
            print(minimum_value)

            # updates these to dictionary
            event['priority'] = priority_value
            event['minimum_threshold'] = minimum_value

            # remove these from the code's account of the event description (without modifying the event on the calendar)
            # so that categories can just be signified with a hashtag

            # get event category

            # this whole next part just cleans up the raw output I get when I get the start time of each event
            # this section just needs to use a datetime version of the now variable. would be much more elegant

            event_starttime_raw = event['start'].get('dateTime')
            event_starttime_t_split = event_starttime_raw.split('T')[-1]  # defines date part of this string as 'stuff before the T'
            event_starttime_remove_date = event_starttime_t_split.replace(event_starttime_raw, '')
            event_starttime_remove_t = event_starttime_remove_date.replace('T', '')
            event_starttime_col_split1 = event_starttime_remove_t.split(':')[0]
            event_starttime_hour = int(event_starttime_col_split1.replace(event_starttime_remove_t, ''))

            # converts from military time
            event_starttime_hour_pm = event_starttime_hour - 12

            # defines last part of the string as 'stuff after the second colon'
            event_starttime_col_split2 = event_starttime_remove_t.split(':')[1]
            event_starttime_minute = event_starttime_col_split2.replace(event_starttime_remove_t, '')
            if event_starttime_hour < 13:
                if event_starttime_hour == 12:
                    event_starttime = '(%s:%s pm)' % (event_starttime_hour, event_starttime_minute)
                else:
                    event_starttime = '(%s:%s am)' % (event_starttime_hour, event_starttime_minute)
            else:
                event_starttime = '(%s:%s pm)' % (event_starttime_hour_pm, event_starttime_minute)

            event_display = '%s %s' % (event_starttime, event_title)
            event_display_list.append(event_display)

            event_description_list.append(event_description)

            # print(eventnumber)
            eventnumber += 1

        print(self.agenda)

        # identifies variables by their corresponding place on the list
        event_0_display = event_display_list[0]
        event_1_display = event_display_list[1]
        event_2_display = event_display_list[2]
        event_3_display = event_display_list[3]

        self.event_0_id = event_id_list[0]
        self.event_1_id = event_id_list[1]

        self.event_0_end_time = event_end_time_list[0]

        # pairs display variables with ID's of kivy objects
        event_0_label = self.root.ids.event_0_label
        event_0_label.text = event_0_display

        event_1_label = self.root.ids.event_1_label
        event_1_label.text = event_1_display

        event_2_label = self.root.ids.event_2_label
        event_2_label.text = event_2_display

        event_3_label = self.root.ids.event_3_label
        event_3_label.text = event_3_display

    def transition(self):
        print('transition button pressed')

        self.transition_time = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

        event_0 = {
            'end': {'dateTime': self.transition_time},
        }

        service.events().patch(calendarId='primary', eventId=self.event_0_id, sendNotifications=True,
                               body=event_0).execute()

        event_1 = {
            'start': {'dateTime': self.transition_time},
        }

        service.events().patch(calendarId='primary', eventId=self.event_1_id, sendNotifications=True,
                               body=event_1).execute()
        self.refresh()



if __name__ == "__main__":
    CalendarCompanionApp().run()
