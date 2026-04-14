import json
import os
import sys
import threading
from datetime import datetime
from threading import Timer
import customtkinter as ctk
from tkinter import ttk

import pygame
import pystray
from PIL import Image, ImageDraw
import winreg
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.mara.gov.om/calendar_page2.asp"

pygame.mixer.init()

# --- resource path ---
def resource_path(file):
    try:
        base = sys._MEIPASS
    except:
        base = os.path.abspath(".")
    return os.path.join(base, file)

DEFAULT_SOUND = resource_path("adhan.mp3")

# --- app data ---
def app_data_dir():
    path = os.path.join(os.getenv("APPDATA"), "AzanApp")
    os.makedirs(path, exist_ok=True)
    return path

# --- ALL cities ---
cities = {
"Muscat":"0","Ibra":"1","Adam":"2","Izki":"3","Al Ashkhara":"4","Buraimi":"5",
"Al-Jazir":"6","Al Jama'a":"7","AlHashman":"8","Halaaniyat":"9","Al-Hamra":"10",
"Al-Khabura":"11","AlKhadrafi":"12","Lekhwair":"13","Al Duqm":"14","Ristaq":"15",
"Al Awabi":"16","AlQabil(Sh)":"17","AlQabil(Dh)":"18","Kamil&Wafi":"19",
"Mudhaibi":"20","Maamura":"21","Al-Howaisa":"22","AlWasit":"23","Wasl":"24",
"Bukha":"25","Bidbid":"26","Bidiya":"27","Barka":"28","Bahla":"29","Thumrait":"30",
"J Harasis":"31","JB Hassan":"32","JB BuAli":"33","Habrut":"34","Hag":"35",
"Daba Bay'aa":"36","Ras AlHad":"37","RMadrakah":"38","Rakhyut":"39","Rwahiba":"40",
"Raysut":"41","Sad'h":"42","Samail":"43","Samad Shan":"44","Sinaw":"45",
"Suwaiq":"46","Seyh Rawl":"47","Saiq":"48","Salyim":"49","Shinas":"50",
"Sohar":"51","Saham":"52","Sarab":"53","Sarfayt":"54","Salalah":"55",
"Sur":"56","Dhank":"57","Taqah":"58","Dhalqut":"59","Ibri":"60","Fahud":"61",
"Qarn Alam":"62","Quriyat":"63","Kanhat":"64","Liwa":"65","Mahdha":"66",
"Mhut":"67","Mad'ha":"68","Mirbat":"69","Marmour":"70","Marmul":"71",
"Musandam":"72","Musana'a":"73","Masirah":"74","Muqshin":"75","Manah":"76",
"Nakhal":"77","Nizwa":"78","Nimr":"79","Harweel":"80","Haima":"81",
"Khazan":"82","WB Khalid":"83","Wadi Hibi":"84","Yanqul":"85"
}

# --- cache ---
def cache_file(city):
    return os.path.join(app_data_dir(), f"cache_{city}.json")

def save_cache(city, data):
    with open(cache_file(city), "w") as f:
        json.dump({
            "month": datetime.now().strftime("%Y-%m"),
            "data": data
        }, f)

def load_cache(city):
    f = cache_file(city)
    if os.path.exists(f):
        with open(f) as file:
            data = json.load(file)
            if data["month"] == datetime.now().strftime("%Y-%m"):
                return data["data"]
    return None

# --- fetch ---
def fetch_prayer_times(city):
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    r = session.get(URL, headers=headers, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")

    viewstate = soup.find("input", {"name": "__VIEWSTATE"})
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})

    payload = {
        "__VIEWSTATE": viewstate["value"] if viewstate else "",
        "__EVENTVALIDATION": eventvalidation["value"] if eventvalidation else "",
        "CityID": cities[city],
        "Submit": "Submit"
    }

    r = session.post(URL, data=payload, headers=headers, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = soup.select("table tr")[1:]
    data = []

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) >= 7:
            data.append({
                "date": cols[0],
                "fajr": cols[1],
                "sunrise": cols[2],
                "dhuhr": cols[3],
                "asr": cols[4],
                "maghrib": cols[5],
                "isha": cols[6],
            })
    return data

def get_data(city):
    c = load_cache(city)
    if c:
        return c
    d = fetch_prayer_times(city)
    save_cache(city, d)
    return d

# --- audio ---
def play_sound(prayer):
    try:
        pygame.mixer.music.load(DEFAULT_SOUND)
        pygame.mixer.music.play()
    except Exception as e:
        print(e)

def stop():
    pygame.mixer.music.stop()

# --- FIXED normalize ---
def normalize(p, t):
    if p in ["fajr", "sunrise"]:
        return t + " AM"
    return t + " PM"

# --- FIXED schedule ---
def schedule(entry):
    now = datetime.now()
    today = now.strftime("%#d/%#m/%Y")

    for p, t in entry.items():
        if p == "date":
            continue
        try:
            dt = datetime.strptime(
                today + " " + normalize(p, t),
                "%d/%m/%Y %I:%M %p"
            )
            delay = (dt - now).total_seconds()

            if delay > 0:
                Timer(delay, lambda p=p: root.after(0, play_sound, p)).start()

        except Exception as e:
            print("Schedule error:", p, t, e)

# --- main logic ---
def show_today():
    city = city_var.get()
    data = get_data(city)

    today = datetime.now().strftime("%#d/%#m/%Y")
    entry = next((x for x in data if x["date"] == today), None)

    if not entry:
        return

    for i in tree.get_children():
        tree.delete(i)

    for p,t in entry.items():
        if p != "date":
            tree.insert("", "end", values=(p.capitalize(), t))

    schedule(entry)

# --- tray ---
def create_icon():
    img = Image.new('RGB', (64,64), "green")
    d = ImageDraw.Draw(img)
    d.text((18,20), "A", fill="white")
    return img

def safe_exit():
    try:
        icon.stop()
    except:
        pass
    try:
        root.after(0, root.quit)
        root.after(50, root.destroy)
    except:
        pass

def tray():
    global icon
    icon = pystray.Icon("Azan", create_icon(),
        menu=pystray.Menu(
            pystray.MenuItem("Open", lambda: root.after(0, show_window)),
            pystray.MenuItem("Exit", lambda: safe_exit())
        ))
    icon.run()

def show_window():
    root.deiconify()
    root.after(0, root.lift)

def on_close():
    try:
        root.withdraw()
    except:
        pass

# --- startup ---
def add_to_startup():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",0,winreg.KEY_SET_VALUE)

    winreg.SetValueEx(
        key,
        "AzanApp",
        0,
        winreg.REG_SZ,
        f'"{sys.executable}"'
    )
    winreg.CloseKey(key)

def auto_daily_update():
    show_today()
    root.after(24*60*60*1000, auto_daily_update)

# --- UI ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Prayer Times")
root.geometry("420x560")

frame = ctk.CTkFrame(root)
frame.pack(fill="both", expand=True, padx=15, pady=15)

ctk.CTkLabel(frame, text="Prayer Times", font=("Segoe UI", 22, "bold")).pack(pady=20)

city_var = ctk.StringVar(value="Muscat")
city_box = ctk.CTkComboBox(frame, values=list(cities.keys()), variable=city_var)
city_box.pack(fill="x", pady=10)

ctk.CTkButton(frame, text="Show Today", command=show_today).pack(fill="x", pady=10)

tree = ttk.Treeview(frame, columns=("Prayer","Time"), show="headings")
tree.heading("Prayer", text="Prayer")
tree.heading("Time", text="Time")
tree.pack(fill="both", expand=True, pady=10)

ctk.CTkButton(frame, text="Stop Sound", command=stop).pack(fill="x")

add_to_startup()
auto_daily_update()

root.after(100, root.withdraw)

root.protocol("WM_DELETE_WINDOW", on_close)
root.after(500, lambda: threading.Thread(target=tray, daemon=True).start())

root.mainloop()