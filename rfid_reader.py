import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import threading
from queue import Queue

class RFIDReader:
    def __init__(self):
        self.reader = SimpleMFRC522()
        self.tag_queue = Queue()
        self.running = False
        self.read_thread = None
        self.last_tag = None
        self.last_tag_time = 0
        self.tag_timeout = 1.0  # Sekunden, die ein Tag als "noch da" gilt
        self.debounce_time = 0.5  # Sekunden zwischen zwei Lesungen

    def start_reading(self):
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()

    def stop_reading(self):
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)  # Warte maximal 1 Sekunde auf das Ende des Threads
            if self.read_thread.is_alive():
                print("Warnung: RFID-Reader-Thread konnte nicht ordnungsgemäß beendet werden")

    def _read_loop(self):
        while self.running:
            try:
                # Versuche, den Tag zu lesen, aber blockiere nicht zu lange
                id, text = self.reader.read_no_block()
                current_time = time.time()
                
                if id:
                    tag_id = str(id)
                    # Wenn es ein neuer Tag ist oder der alte Tag zu lange weg war
                    if tag_id != self.last_tag or (current_time - self.last_tag_time) > self.tag_timeout:
                        self.tag_queue.put(tag_id)
                        self.last_tag = tag_id
                        self.last_tag_time = current_time
                else:
                    # Wenn kein Tag gelesen wurde und der letzte Tag zu lange weg ist
                    if self.last_tag and (current_time - self.last_tag_time) > self.tag_timeout:
                        self.tag_queue.put(None)
                        self.last_tag = None
                
                time.sleep(self.debounce_time)
            except Exception as e:
                print(f"Error reading RFID: {e}")
                time.sleep(1)

    def get_tag(self):
        try:
            return self.tag_queue.get_nowait()
        except:
            return None

    def cleanup(self):
        try:
            if hasattr(GPIO, 'getmode') and GPIO.getmode() is not None:
                GPIO.cleanup()
        except Exception as e:
            print(f"Warnung bei GPIO-Cleanup: {e}") 