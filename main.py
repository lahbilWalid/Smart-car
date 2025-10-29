import json
import random
import tkinter as tk
from tkinter import ttk
import time
from pygame import mixer
from queue import PriorityQueue
import logging

# Load alert configuration
with open("Alerts_config.json", "r", encoding="utf-8") as Al:
    Alerts = json.load(Al)

Alert_priority = Alerts["ALERTS"]
Alert_icon = Alerts["ICONS"]
Alert_son = Alerts["SONS"]
Alert_sensor = Alerts["SENSORS"]

# Configure logging
logging.basicConfig(
    filename="alerts.log",
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

# Define alert class
class Alerte:
    def __init__(self, nom, priority, horodatage, icon, son):
        self.nom = nom
        self.priority = priority
        self.horodatage = horodatage
        self.son = son
        self.icon = icon

    def __lt__(self, other):
        return self.priority < other.priority

# Define main application class
class AlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("simulation des alerts du smart car")
        self.tree = ttk.Treeview(root, columns=("Horodatage","Alert", "Priorité",  "Icône", "Son"), show="headings")
        self.tree.heading("Priorité", text="Priorité")
        self.tree.heading("Horodatage", text="Horodatage")
        self.tree.heading("Alert", text="Alerte")
        self.tree.heading("Icône", text="Icône")
        self.tree.heading("Son", text="Son")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # list to add alerts in
        self.all_alerts = []

        # add a frame for combobox and label
        filter_frame = tk.Frame(root)
        filter_frame.pack(pady=5)

        # add label
        filter_label = tk.Label(filter_frame, text="Filtrer par alerte :")
        filter_label.pack(side=tk.LEFT)

        # add a combobox to filter alerts
        self.filter_var = tk.StringVar()
        self.filter_combo = ttk.Combobox(filter_frame, textvariable= self.filter_var)
        self.filter_combo['values'] = ['Tous'] + list(Alert_priority.keys())
        self.filter_combo.current(0)
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind('<<ComboboxSelected>>', self.filtrer_alertes)

        # add a tag for every alert priority with a specific color
        self.tree.tag_configure("priorite1", background="#ffcccc")  # Rouge
        self.tree.tag_configure("priorite2", background="#ffe5b4")  # Orange
        self.tree.tag_configure("priorite3", background="#ccffcc")  # Vert


        self.button = tk.Button(root, text="Générer une alerte aléatoire", command= self.genererAlert)
        self.button.pack(pady=10)

        # add a frame for sensors
        sensor_frame = tk.Frame(root)
        sensor_frame.pack(pady=10)

        for sensor, alert_name in Alert_sensor.items():
            btn = tk.Button(sensor_frame, text = sensor, command = lambda a=alert_name: self.genererAlert(a))
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        sensor_frame.pack(anchor="center")

        self.alertQueue = PriorityQueue()
        self.current_alert = None
        self.current_channel = None
        mixer.init()

    def genererAlert(self, alert=None):
        if alert is None:
            nom = random.choice(list(Alert_priority.keys()))
        else:
            nom = alert

        priority = Alert_priority[nom]
        horodatage = time.strftime("%Y-%m-%d %H:%M:%S")
        icon = Alert_icon[nom]
        son = Alert_son[nom]

        alerte = Alerte(nom, priority, horodatage, icon, son)
        self.all_alerts.append(alerte)
        self.alertQueue.put(alerte)
        self.traiterAlert()

    def traiterAlert(self):
        if not self.alertQueue.empty():
            new_alerte = self.alertQueue.get()
            print(f"{new_alerte.nom} détectée")
            chemin = f"C:\\Users\\wlahbil\\PycharmProjects\\Ecockpit\\waves\\{new_alerte.son}"
            notif_path = "C:\\Users\\wlahbil\\PycharmProjects\\Ecockpit\\waves\\notif.wav"
            sound = mixer.Sound(chemin)
            self.tree.insert("", "end", values=(new_alerte.horodatage, new_alerte.nom, new_alerte.priority,  new_alerte.icon, new_alerte.son), tags=(f"priorite{new_alerte.priority}",))
            self.journaliser(new_alerte)
            self.root.update_idletasks()

            if self.current_alert:
                if new_alerte.priority < self.current_alert.priority:
                    if self.current_channel and self.current_channel.get_busy():
                        self.current_channel.stop()
                        print(f"l'alert {self.current_alert.nom} est  interrompu")
                elif new_alerte.priority >= self.current_alert.priority:
                    if self.current_channel and self.current_channel.get_busy():
                        print(f"l'alert {new_alerte.nom} est moin prioritaire")
                        notif_sound = mixer.Sound(notif_path)
                        channel = mixer.find_channel()
                        if channel:
                            channel.play(notif_sound)
                        return

            self.current_alert = new_alerte
            self.current_channel = mixer.find_channel()

            if self.current_channel:
                self.current_channel.play(sound, loops=2)

    # MQTT Communication entre capteurs

    def filtrer_alertes(self, event=None):
        # recuperate the value of the filter
        filtre = self.filter_var.get()

        # delete curent list of alerts
        for item in self.tree.get_children():
            self.tree.delete(item)

        # add the filtred alerts
        for alerte in self.all_alerts:
            if filtre == 'Tous' or filtre == alerte.nom :
                self.tree.insert("", "end", values=(alerte.horodatage, alerte.nom, alerte.priority, alerte.icon, alerte.son), tags=(f"priorite{alerte.priority}",))


    def journaliser(self, alerte):
        # Logging with appropriate level based on priority
        if alerte.priority == 1:
            logging.critical(f"Alerte : {alerte.nom} | Priorité : {alerte.priority} | Icon : {alerte.icon} | Son : {alerte.son}")
        elif alerte.priority == 2:
            logging.warning(f"Alerte : {alerte.nom} | Priorité : {alerte.priority} | Icon : {alerte.icon} | Son : {alerte.son}")
        else:
            logging.info(f"Alerte : {alerte.nom} | Priorité : {alerte.priority} | Icon : {alerte.icon} | Son : {alerte.son}")

        # Old method for LOGGING
        with open("journal_alert.txt", "a", encoding="utf-8") as j:
            j.write(f"{alerte.horodatage} | Alerte : {alerte.nom} | Priorité : {alerte.priority} | Icon : {alerte.icon} | son : {alerte.son} \n")

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = AlertApp(root)
    root.mainloop()
