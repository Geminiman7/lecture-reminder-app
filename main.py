
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.properties import ListProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from plyer import notification
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import os
from platformdirs import user_data_dir

# Database setup
db_dir = user_data_dir("LectureReminder", "YourAppName")
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "lectures.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS lectures
                  (id INTEGER PRIMARY KEY, day TEXT, time TEXT, subject TEXT, venue TEXT, lecturer TEXT)''')
conn.commit()

# Global flag to stop thread
stop_thread = False

# Layout for selectable list items
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    pass

# Selectable label for RecycleView
class SelectableLabel(RecycleDataViewBehavior, Label):
    index = None
    selected = False
    selectable = True

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.parent.select_with_touch(self.index, touch)
            return True

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected
        self.color = (1, 0, 0, 1) if is_selected else (1, 1, 1, 1)

# Main layout
class LectureReminderLayout(BoxLayout):
    lecture_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        # Inputs
        self.day_input = TextInput(hint_text="Day (e.g., Monday)", multiline=False)
        self.time_input = TextInput(hint_text="Time (HH:MM, e.g., 14:30)", multiline=False)
        self.subject_input = TextInput(hint_text="Subject", multiline=False)
        self.venue_input = TextInput(hint_text="Venue (e.g., Room 101)", multiline=False)
        self.lecturer_input = TextInput(hint_text="Lecturer Name", multiline=False)

        self.add_button = Button(text="Add Lecture", size_hint=(1, 0.2))
        self.add_button.bind(on_press=self.add_lecture)

        self.lecture_list = RecycleView()
        self.lecture_list.viewclass = 'SelectableLabel'

        # Correctly set the layout manager
        layout_manager = SelectableRecycleBoxLayout(
            default_size=(None, 40),
            default_size_hint=(1, None),
            size_hint=(1, None),
            orientation='vertical'
        )
        self.lecture_list.layout_manager = layout_manager

        self.remove_button = Button(text="Remove Selected", size_hint=(1, 0.2))
        self.remove_button.bind(on_press=self.remove_lecture)

        self.add_widget(Label(text="Day:"))
        self.add_widget(self.day_input)
        self.add_widget(Label(text="Time (HH:MM):"))
        self.add_widget(self.time_input)
        self.add_widget(Label(text="Subject:"))
        self.add_widget(self.subject_input)
        self.add_widget(Label(text="Venue:"))
        self.add_widget(self.venue_input)
        self.add_widget(Label(text="Lecturer:"))
        self.add_widget(self.lecturer_input)
        self.add_widget(self.add_button)
        self.add_widget(Label(text="Your Lectures:"))
        self.add_widget(self.lecture_list)
        self.add_widget(self.remove_button)

        self.update_lecture_list()

    def add_lecture(self, instance):
        day = self.day_input.text.strip()
        lecture_time = self.time_input.text.strip()
        subject = self.subject_input.text.strip()
        venue = self.venue_input.text.strip()
        lecturer = self.lecturer_input.text.strip()

        if day and lecture_time and subject and venue and lecturer:
            try:
                dt_time = datetime.strptime(lecture_time, "%H:%M").time()
                current_time = datetime.now().time()
                if day == datetime.now().strftime("%A") and dt_time <= current_time:
                    self.show_popup("Warning", "Lecture time is in the past.")
                    return
                cursor.execute("INSERT INTO lectures (day, time, subject, venue, lecturer) VALUES (?, ?, ?, ?, ?)",
                               (day, lecture_time, subject, venue, lecturer))
                conn.commit()
                self.show_popup("Success", "Lecture added!")
                self.clear_entries()
                self.update_lecture_list()
            except ValueError:
                self.show_popup("Error", "Time must be in HH:MM format (e.g., 14:30)")
        else:
            self.show_popup("Error", "All fields are required!")

    def clear_entries(self):
        self.day_input.text = ""
        self.time_input.text = ""
        self.subject_input.text = ""
        self.venue_input.text = ""
        self.lecturer_input.text = ""

    def update_lecture_list(self, *args):
        cursor.execute("SELECT id, day, time, subject, venue, lecturer FROM lectures")
        lectures = cursor.fetchall()
        self.lecture_data = [
            {'text': f"ID: {lec[0]} | {lec[1]} {lec[2]} - {lec[3]} @ {lec[4]} by {lec[5]}"}
            for lec in lectures
        ]
        self.lecture_list.data = self.lecture_data

    def remove_lecture(self, instance):
        selected_nodes = self.lecture_list.layout_manager.selected_nodes
        if selected_nodes:
            selected_index = selected_nodes[0]
            selected_item = self.lecture_list.data[selected_index]
            lecture_id = int(selected_item['text'].split("ID: ")[1].split(" |")[0])
            cursor.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
            conn.commit()
            self.show_popup("Success", "Lecture removed!")
            self.update_lecture_list()
        else:
            self.show_popup("Error", "Please select a lecture to remove!")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

# Reminder thread
def check_reminders():
    thread_conn = sqlite3.connect(db_path, check_same_thread=False)
    thread_cursor = thread_conn.cursor()
    reminders_sent = {}

    while not stop_thread:
        now = datetime.now()
        today = now.strftime("%A")
        current_time_str = now.strftime("%H:%M")

        thread_cursor.execute("SELECT id, time, subject, venue, lecturer FROM lectures WHERE day = ?", (today,))
        lectures = thread_cursor.fetchall()

        for lec_id, time_str, subject, venue, lecturer in lectures:
            lec_time = datetime.strptime(time_str, "%H:%M").time()
            lecture_dt = datetime.combine(now.date(), lec_time)
            time_diff = (lecture_dt - now).total_seconds() / 60

            lec_key = (lec_id, today)
            if lec_key not in reminders_sent:
                reminders_sent[lec_key] = []

            for interval, label in [(60, "1 hour"), (45, "45 minutes"), (30, "30 minutes"), (15, "15 minutes")]:
                notify_time = lecture_dt - timedelta(minutes=interval)
                if 0 <= (notify_time - now).total_seconds() / 60 <= 1 and interval not in reminders_sent[lec_key]:
                    try:
                        notification.notify(
                            title="Lecture Reminder",
                            message=f"'{subject}' by {lecturer} at {venue} in {label} at {time_str}",
                            app_name="Lecture Reminder",
                            timeout=10
                        )
                        reminders_sent[lec_key].append(interval)
                    except Exception as e:
                        print(f"Notification failed: {str(e)}")

        for key in list(reminders_sent):
            if key[1] != today:
                del reminders_sent[key]

        time.sleep(60)

    thread_conn.close()

# App class
class LectureReminderApp(App):
    def build(self):
        return LectureReminderLayout()

    def on_start(self):
        global stop_thread
        stop_thread = False
        self.reminder_thread = threading.Thread(target=check_reminders, daemon=True)
        self.reminder_thread.start()

    def on_stop(self):
        global stop_thread
        stop_thread = True
        if self.reminder_thread.is_alive():
            self.reminder_thread.join()
        conn.close()

if __name__ == '__main__':
    LectureReminderApp()