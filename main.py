
import os
import webbrowser
import datetime
import requests
import speech_recognition as sr
import pyttsx3
import time
import threading
from dotenv import load_dotenv
from queue import Queue

load_dotenv()

class JARVIS:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.engine = pyttsx3.init()
        self.is_active = False
        self.command_queue = Queue()
        self.reminders = []
        self.last_command_time = time.time()

        self.engine.setProperty('rate', 180)
        self.engine.setProperty('voice', self.engine.getProperty('voices')[1].id)


        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.news_api_key = os.getenv("NEWSAPI_API_KEY")

        self.background_thread = threading.Thread(target=self._background_tasks)
        self.background_thread.daemon = True
        self.background_thread.start()

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def _background_tasks(self):
        """Handle periodic checks in background"""
        while True:
            # Check reminders every 10 seconds
            now = datetime.datetime.now()
            for reminder in self.reminders:
                if reminder['time'] <= now and not reminder['triggered']:
                    self.speak(f"Reminder: {reminder['message']}")
                    reminder['triggered'] = True
            time.sleep(10)

    def continuous_listen(self):
        """Continuous listening with timeout"""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.is_active:
                try:
                    print("Listening for command...")
                    audio = self.recognizer.listen(source, timeout=5)
                    text = self.recognizer.recognize_google(audio).lower()
                    self.command_queue.put(text)
                except sr.WaitTimeoutError:
                    if time.time() - self.last_command_time > 30:
                        self.is_active = False
                        self.speak("Entering sleep mode due to inactivity")
                except:
                    pass

    def process_command(self, command):
        self.last_command_time = time.time()
        print(f"Processing command: {command}")

        if "open" in command:
            sites = {
                "google": "https://google.com",
                "youtube": "https://youtube.com",
                "spotify": "https://open.spotify.com",
                "facebook": "https://facebook.com",
                "instagram": "https://instagram.com"
            }
            for site, url in sites.items():
                if site in command:
                    webbrowser.open(url)
                    self.speak(f"Opening {site} sir")
                    return

        elif "time" in command:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"Current time is {current_time}")

        elif "date" in command:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            self.speak(f"Today's date is {current_date}")

        elif "weather" in command:
            self.handle_weather(command)

        elif "remind me" in command:
            self.handle_reminders(command)

        elif "news" in command:
            self.handle_news()

        elif "email" in command:
            self.handle_email(command)

        elif "system status" in command:
            self.handle_system_status()

        elif "sleep" in command or "exit" in command:
            self.is_active = False
            self.speak("Going to standby mode")
            return

        else:
            self.handle_ai_query(command)

    def handle_weather(self, command):
        try:
            city = "London"  # Default city
            if "in " in command:
                city = command.split("in ")[1]
            
            response = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.openweather_api_key}&units=metric"
            )
            data = response.json()
            temp = data['main']['temp']
            desc = data['weather'][0]['description']
            self.speak(f"Weather in {city}: {desc}, temperature {temp}°C")
        except Exception as e:
            self.speak("Unable to retrieve weather data")

    def handle_reminders(self, command):
        try:
            message = command.split("remind me to ")[1]
            trigger_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
            self.reminders.append({
                'message': message,
                'time': trigger_time,
                'triggered': False
            })
            self.speak(f"Reminder set for 1 minute from now: {message}")
        except:
            self.speak("Could not set reminder, please try again")

    def handle_news(self):
        try:
            response = requests.get(
                f"https://newsapi.org/v2/top-headlines?country=us&apiKey={self.news_api_key}"
            )
            articles = response.json()['articles'][:3]
            headlines = [article['title'] for article in articles]
            self.speak("Top headlines: " + ". ".join(headlines))
        except:
            self.speak("Unable to fetch news updates")

    def handle_ai_query(self, command):
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": command}],
            "max_tokens": 150
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            reply = response.json()['choices'][0]['message']['content']
            self.speak(reply)
        except:
            self.speak("I'm having connection error, sir.")

    def run(self):
        self.speak("JARVIS initialization complete. Systems online")
        while True:
            try:
                audio_input = self.listen_once()
                if "jarvis" in audio_input:
                    self.is_active = True
                    self.speak("Yes sir? How can I assist?")
                    listener_thread = threading.Thread(target=self.continuous_listen)
                    listener_thread.start()
                    
                    while self.is_active:
                        if not self.command_queue.empty():
                            command = self.command_queue.get()
                            self.process_command(command)
                        time.sleep(0.1)
                        
            except KeyboardInterrupt:
                self.speak("Shutting down systems")
                break

    def listen_once(self):
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=3)
                return self.recognizer.recognize_google(audio).lower()
            except:
                return ""

if __name__ == "__main__":
    assistant = JARVIS()
    assistant.run()
