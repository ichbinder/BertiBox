import pygame
import threading
from rfid_reader import RFIDReader
from database import Database
import time
import os
import requests
import atexit
import subprocess

class BertiBox:
    def __init__(self):
        # Setze die Audio-Ausgabe auf den Kopfhörer-Ausgang
        subprocess.run(['amixer', 'set', 'PCM', '100%'])
        subprocess.run(['amixer', 'set', 'PCM', 'unmute'])
        
        # Initialisiere Pygame und Audio
        pygame.init()
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.set_num_channels(1)
        pygame.mixer.music.set_volume(1.0)  # Maximale Lautstärke
        
        self.rfid_reader = RFIDReader()
        self.db = Database()
        self.running = False
        self.web_interface_url = 'http://localhost:5000'
        self.is_playing = False
        self.last_tag_time = 0
        self.tag_timeout = 2.0  # Sekunden, die ein Tag als "noch da" gilt
        self.current_playlist = None
        self.current_playlist_index = 0
        self.current_tag_id = None
        print("BertiBox initialisiert")

    def start(self):
        self.running = True
        self.rfid_reader.start_reading()
        print("RFID Reader gestartet")
        
        while self.running:
            tag_id = self.rfid_reader.get_tag()
            current_time = time.time()
            
            # Wenn ein neuer Tag erkannt wurde
            if tag_id and tag_id != self.current_tag_id:
                print(f"Neuer Tag erkannt: {tag_id}")
                self.current_tag_id = tag_id
                self.last_tag_time = current_time
                try:
                    requests.post(f"{self.web_interface_url}/api/current-tag", json={'tag_id': tag_id})
                    print(f"Tag an Webinterface gesendet: {tag_id}")
                except Exception as e:
                    print(f"Error sending tag to web interface: {e}")
                self.handle_tag(tag_id)
            # Wenn der gleiche Tag erkannt wurde, aktualisiere nur die Zeit
            elif tag_id == self.current_tag_id:
                self.last_tag_time = current_time
                # Prüfe, ob die aktuelle Datei zu Ende ist
                if self.is_playing and not pygame.mixer.music.get_busy():
                    self.play_next_in_playlist()
            # Wenn kein Tag erkannt wurde und der letzte Tag zu lange weg ist
            elif self.current_tag_id and (current_time - self.last_tag_time) > self.tag_timeout:
                print("Tag wirklich entfernt, stoppe Wiedergabe")
                self.stop_mp3()
                self.current_tag_id = None
                self.current_playlist = None
                self.current_playlist_index = 0
                try:
                    requests.post(f"{self.web_interface_url}/api/current-tag", json={'tag_id': None})
                    print("Tag-Entfernung an Webinterface gesendet")
                except Exception as e:
                    print(f"Error sending tag removal to web interface: {e}")
            
            time.sleep(0.1)

    def handle_tag(self, tag_id):
        if not tag_id:
            # Tag wurde entfernt, stoppe die Wiedergabe
            if self.is_playing:
                self.stop_mp3()
                self.current_playlist = None
                self.current_playlist_index = 0
                self.current_tag_id = None
            return
            
        # Tag wurde erkannt
        if not self.is_playing or tag_id != self.current_tag_id:
            # Hole den Tag mit seinen Playlists
            tag = self.db.get_tag(tag_id)
            if not tag:
                print(f"Tag {tag_id} nicht gefunden")
                return
                
            if not tag['playlists']:
                print(f"Keine Playlist für Tag {tag_id} gefunden")
                return
                
            # Nimm die erste Playlist des Tags
            playlist = tag['playlists'][0]
            print(f"Playlist gefunden für Tag {tag_id}: {playlist['name']}")
            
            # Speichere die aktuelle Tag-ID
            self.current_tag_id = tag_id
            
            # Spiele die Playlist ab
            self.play_playlist(playlist['id'])

    def play_playlist(self, playlist_id):
        try:
            items = self.db.get_playlist_items(playlist_id)
            if not items:
                print(f"Keine MP3s in Playlist {playlist_id} gefunden")
                return
                
            print(f"Spiele Playlist {playlist_id} ab")
            self.current_playlist = {'id': playlist_id}
            self.current_playlist_index = 0
            self.is_playing = True
            
            # Spiele das erste Lied ab
            self.play_next_in_playlist()
        except Exception as e:
            print(f"Fehler beim Abspielen der Playlist: {e}")
            self.is_playing = False

    def play_next_in_playlist(self):
        if not self.current_playlist:
            return
            
        items = self.db.get_playlist_items(self.current_playlist['id'])
        if not items:
            return
            
        if self.current_playlist_index >= len(items):
            self.current_playlist_index = 0  # Zurück zum Anfang der Playlist
            
        item = items[self.current_playlist_index]
        if self.play_mp3(item['mp3_file']):
            self.current_playlist_index += 1

    def play_mp3(self, mp3_file):
        try:
            # Vollständiger Pfad zur MP3-Datei
            mp3_path = os.path.join('mp3', mp3_file)
            print(f"Versuche MP3 abzuspielen: {mp3_path}")
            
            if not os.path.exists(mp3_path):
                print(f"MP3-Datei nicht gefunden: {mp3_path}")
                return False
            
            # Audio-Einstellungen anpassen
            pygame.mixer.music.set_volume(1.0)  # Maximale Lautstärke
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play()
            
            # Starte einen Timer, der die Wiedergabe überwacht
            self.is_playing = True
            threading.Timer(0.1, self.check_playback).start()
            
        except Exception as e:
            print(f"Fehler beim Abspielen der MP3: {e}")
            return False
        return True

    def check_playback(self):
        if self.is_playing and not pygame.mixer.music.get_busy():
            self.is_playing = False
            self.play_next_in_playlist()
        elif self.is_playing:
            # Prüfe alle 100ms, ob die Wiedergabe noch läuft
            threading.Timer(0.1, self.check_playback).start()

    def stop_mp3(self):
        if self.is_playing:
            print("Stoppe MP3 Wiedergabe")
            pygame.mixer.music.stop()
            self.is_playing = False

    def stop(self):
        print("Stoppe BertiBox")
        self.running = False
        self.rfid_reader.stop_reading()
        self.stop_mp3()
        pygame.mixer.quit()
        pygame.quit()
        self.rfid_reader.cleanup()
        self.db.cleanup()

    def handle_command(self, command):
        if command.lower() == 'stoppe bertibox':
            self.stop()
            return True
        return False

def cleanup():
    berti_box.stop()

if __name__ == '__main__':
    berti_box = BertiBox()
    atexit.register(cleanup)
    try:
        berti_box.start()
    except KeyboardInterrupt:
        berti_box.stop() 