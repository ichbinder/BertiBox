import pygame
import threading
from rfid_reader import RFIDReader
from database import Database, Base, Tag, Playlist, PlaylistItem
import time
import os
import atexit
import subprocess
import traceback
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Configure secret key for security, can be any random string
app.config['SECRET_KEY'] = 'your_secret_key_here!' # TODO: Replace with a secure key
socketio = SocketIO(app)
db = Database()
berti_box = None # Initialize later

# MP3-Verzeichnis
MP3_DIR = 'mp3'

# Create MP3 directory if it doesn't exist
os.makedirs(MP3_DIR, exist_ok=True)

# ---------------- BertiBox Class (integrated from main.py) ----------------

class BertiBox:
    def __init__(self, socketio_instance, db_instance):
        self.socketio = socketio_instance
        self.db = db_instance
        self.pygame_initialized = False # Initialize flag
        self.mixer_initialized = False  # Initialize flag

        # Load initial volume from DB FIRST
        try:
            initial_volume_str = self.db.get_setting('global_volume', '0.8') # Default 0.8
            self.current_volume = float(initial_volume_str)
            if not (0.0 <= self.current_volume <= 1.0):
                 print(f"Warning: Invalid volume '{self.current_volume}' loaded from DB, resetting to 0.8")
                 self.current_volume = 0.8
                 self.db.set_setting('global_volume', str(self.current_volume)) # Save corrected value
            print(f"Initial volume loaded from DB: {self.current_volume}")
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse volume from DB ('{initial_volume_str}'). Using default 0.8. Error: {e}")
            self.current_volume = 0.8
            self.db.set_setting('global_volume', str(self.current_volume)) # Save default value

        # Setze die Audio-Ausgabe auf den Kopfhörer-Ausgang
        try:
            subprocess.run(['amixer', 'set', 'PCM', '100%'], check=True)
            subprocess.run(['amixer', 'set', 'PCM', 'unmute'], check=True)
            print("Audio output configured.")
        except Exception as e:
            print(f"Warning: Could not configure audio output via amixer: {e}")
            print("Playback might use default output or fail.")

        # Initialisiere Pygame und Audio
        try:
            pygame.init()
            # Ensure ALSA is used if available, might need adjustment based on system
            # os.environ['SDL_AUDIODRIVER'] = 'alsa'
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=8192) # Increased buffer size
            pygame.mixer.set_num_channels(1) # Use only one channel for music
            pygame.mixer.music.set_volume(self.current_volume)  # Set initial volume
            print("Pygame Mixer initialized.")
            self.pygame_initialized = True
            self.mixer_initialized = True
        except pygame.error as e:
            print(f"Error initializing Pygame Mixer: {e}")
            print("Audio playback will not be available.")
            # Optionally, disable playback functionality if init fails
            self.running = False # Prevent start loop if pygame fails
            return

        self.rfid_reader = RFIDReader()
        self.running = False
        self.is_playing = False # True if music is actively playing or paused
        self.is_paused = False # True only if playback is paused
        self.last_tag_time = 0
        self.tag_timeout = 2.0  # Sekunden, die ein Tag als "noch da" gilt
        self.current_playlist = None # Holds {'id': playlist_id, 'name': name, 'items': []}
        self.current_playlist_items = [] # Holds the actual item dicts
        self.current_playlist_index = 0
        self.current_tag_id = None
        self.current_track_filename = None
        self.current_tag_name = None # Store the name of the current tag
        self.playback_check_timer = None
        self.sleep_timer = None # threading.Timer object for sleep
        self.sleep_timer_end_time = None # timestamp when timer expires
        print("BertiBox initialisiert")

    def start(self):
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init():
             print("Cannot start BertiBox: Pygame Mixer not initialized.")
             self.running = False
             return

        self.running = True
        self.rfid_reader.start_reading()
        print("RFID Reader gestartet")

        print("BertiBox main loop starting...")
        while self.running:
            try:
                tag_id = self.rfid_reader.get_tag()
                current_time = time.time()

                # --- Tag detection logic ---
                if tag_id and tag_id != self.current_tag_id:
                    print(f"New Tag detected: {tag_id} (Previous: {self.current_tag_id})")
                    # Emit specific event for management UI
                    self.socketio.emit('tag_detected', {'tag_id': tag_id})
                    print(f"Emitted 'tag_detected' for {tag_id} to management UI")
                    
                    # Update internal state and handle playback
                    self.current_tag_id = tag_id
                    self.last_tag_time = current_time
                    # Run handle_tag in background 
                    print(f"Scheduling handle_tag for {tag_id}")
                    self.socketio.start_background_task(self.handle_tag, tag_id)
                
                elif tag_id and tag_id == self.current_tag_id:
                    # Same tag detected, update last seen time
                    self.last_tag_time = current_time
                    # print(f"Tag {tag_id} still present.") 

                elif not tag_id and self.current_tag_id and (current_time - self.last_tag_time) > self.tag_timeout:
                    # --- Tag removal logic --- 
                    print(f"Tag '{self.current_tag_id}' timed out. Scheduling state clear.")
                    # Emit specific event for management UI about tag removal
                    self.socketio.emit('tag_detected', {'tag_id': None})
                    print(f"Emitted 'tag_detected' for None to management UI")
                    
                    # Clear internal state and stop playback (in background)
                    self.socketio.start_background_task(self.clear_current_tag_state)
                    # Prevent re-triggering immediately by clearing the ID now
                    self.current_tag_id = None 

                # --- Playback finish check --- 
                if self.is_playing and not self.is_paused:
                     if not pygame.mixer.music.get_busy():
                         print("Track finished naturally in main loop check. Scheduling next track.")
                         self.socketio.start_background_task(self.play_next, track_finished_naturally=True)

            except Exception as e:
                 # This block MUST be indented
                 print(f"ERROR in BertiBox main loop: {e}")
                 traceback.print_exc()
                 # Decide if error is fatal or recoverable
                 # For now, just log and continue
                 pass
            
            # This time.sleep MUST be at the same indentation level as the 'try' above
            # Prevent busy-waiting
            time.sleep(0.1) 
        
        # This print is correctly outside the while loop
        print("BertiBox main loop finished.")

    def handle_tag(self, tag_id):
        if not tag_id:
             # Should be handled by the timeout logic in start()
            return

        # Tag wurde erkannt
        print(f"Handling Tag: {tag_id}") # DEBUG
        try:
            # Hole den Tag mit seinen Playlists
            print(f"DB: Getting tag data for {tag_id}") # DEBUG
            tag_data = self.db.get_tag(tag_id)
            
            if not tag_data:
                # --- Tag NOT found - Add it now --- 
                print(f"Tag {tag_id} not found. Adding it to the database and creating default playlist...")
                session = self.db.get_session()
                try:
                    # Step 1: Add the tag
                    new_tag = Tag(tag_id=tag_id, name=f"Neuer Tag {tag_id}")
                    session.add(new_tag)
                    session.flush() # Get the ID

                    # Step 2: Create and associate default playlist
                    # Use the tag's default name as the playlist name initially
                    playlist = Playlist(name=new_tag.name)
                    new_tag.playlists.append(playlist)
                    session.add(playlist)
                    session.commit()
                    new_playlist_id = playlist.id
                    new_playlist_name = playlist.name
                    print(f"Successfully added new tag {tag_id} and default playlist (ID: {new_playlist_id}) to DB.")

                    # Update player status to show new tag (with empty playlist)
                    self.current_playlist = {'id': new_playlist_id, 'name': new_playlist_name, 'items': []}
                    self.current_playlist_items = []
                    self.current_tag_name = new_tag.name # Store the name of the newly added tag
                    self.current_playlist_index = 0
                    self.is_playing = False
                    self.is_paused = False
                    self.current_track_filename = None
                    self.emit_player_status()

                    # Frontend's loadTags() was already triggered by tag_detected, should show it now.
                    session.close()
                    return # Stop further processing in handle_tag for new tags
                
                except Exception as add_e:
                    print(f"EXCEPTION occurred while trying to add new tag {tag_id} and playlist: {add_e}")
                    traceback.print_exc()
                    session.rollback()
                    # Emit status reflecting tag detected but error occurred
                    self.current_playlist = None # Clear potentially inconsistent state
                    self.emit_player_status()
                    session.close()
                    return
                finally:
                    # Ensure session is closed if still active
                    if session.is_active:
                        session.close()
                # --- End Add new tag --- 
            
            # --- Tag WAS found - Store name and continue --- 
            self.current_tag_name = tag_data.get('name') # Store the name here

            if not tag_data.get('playlists'):
                # ... (handle existing tag with no playlist - should ideally not happen) ...
                print(f"DB Result: No playlist found for existing Tag {tag_id}.") # DEBUG
                self.stop_mp3()
                self.current_playlist = None
                self.current_playlist_items = []
                self.current_playlist_index = 0
                self.current_track_filename = None
                self.emit_player_status()
                return
            
            playlist_info = tag_data['playlists'][0]
            playlist_id = playlist_info.get('id')
            print(f"Playlist found: ID={playlist_id}, Name={playlist_info.get('name', 'N/A')}") # DEBUG

            # Load and play the playlist
            print(f"Calling load_and_play_playlist for ID: {playlist_id}") # DEBUG
            self.load_and_play_playlist(playlist_id)

        except Exception as e:
            print(f"ERROR in handle_tag for {tag_id}: {e}")
            traceback.print_exc()
            self.emit_player_status() # Emit current (likely error) state

    def load_and_play_playlist(self, playlist_id):
        try:
            # Check if it's the same playlist already loaded
            if self.current_playlist and self.current_playlist['id'] == playlist_id:
                 print(f"Playlist {playlist_id} ist bereits aktiv.")
                 # If not playing or paused, start from beginning
                 if not self.is_playing and not self.is_paused:
                     self.current_playlist_index = 0
                     self.play_current_track()
                 else:
                    # Already playing/paused this playlist, ensure status is emitted
                    self.emit_player_status()
                 return

            # Load playlist details and items
            print(f"Inside load_and_play_playlist for ID: {playlist_id}") # DEBUG
            print(f"DB: Getting playlist details for {playlist_id}") # DEBUG
            playlist_details = self.db.get_playlist(playlist_id)
            print(f"DB: Getting playlist items for {playlist_id}") # DEBUG
            items_data = self.db.get_playlist_items(playlist_id)

            # Check if playlist object was found
            if not playlist_details:
                 print(f"DB Result: Playlist details not found for ID {playlist_id}") # DEBUG
                 # Update status to reflect missing playlist details but potentially keep items if found?
                 # For now, treat as error
                 self.stop_mp3()
                 self.current_playlist = {'id': playlist_id, 'name': f"Playlist {playlist_id} (Not Found)", 'items': []}
                 self.current_playlist_items = []
                 self.current_playlist_index = 0
                 self.current_track_filename = None
                 self.emit_player_status()
                 return

            playlist_name = playlist_details.name if hasattr(playlist_details, 'name') else f"Playlist {playlist_id}"
            print(f"Playlist details loaded: Name='{playlist_name}'") # DEBUG

            if not items_data:
                print(f"DB Result: No items found in Playlist {playlist_id}") # DEBUG
                self.stop_mp3()
                self.current_playlist = {
                    'id': playlist_id,
                    'name': playlist_name,
                    'items': []
                }
                self.current_playlist_items = []
                self.current_playlist_index = 0
                self.current_track_filename = None
                self.emit_player_status()
                return

            print(f"Loaded Playlist {playlist_id} ('{playlist_name}') with {len(items_data)} items.") # DEBUG
            print("Stopping potentially previous playback...") # DEBUG
            self.stop_mp3() # Stop previous playback cleanly

            self.current_playlist = {
                'id': playlist_id,
                'name': playlist_name,
                # Store simplified items for status emission
                'items': [{'id': item['id'], 'mp3_file': item['mp3_file'], 'position': item['position']} for item in items_data]
            }
            self.current_playlist_items = items_data # Keep full data internally
            self.current_playlist_index = 0
            self.is_playing = False # Will be set by play_current_track
            self.is_paused = False
            print("Internal state updated with new playlist data.") # DEBUG

            # Play the first track
            print("Calling play_current_track...") # DEBUG
            self.play_current_track() # This will also emit the status

        except Exception as e:
            print(f"Fehler beim Laden/Abspielen der Playlist {playlist_id}: {e}")
            self.stop_mp3() # Ensure clean state on error
            self.current_playlist = None
            self.current_playlist_items = []
            self.current_playlist_index = 0
            self.current_track_filename = None
            self.is_playing = False
            self.is_paused = False
            self.emit_player_status()

    def play_current_track(self):
        """Plays the track at the current index."""
        if not self.current_playlist or not self.current_playlist_items:
            print("Play Current: No playlist or items.")
            self.stop_mp3() # Ensure clean state
            self.emit_player_status()
            return

        if self.current_playlist_index < 0 or self.current_playlist_index >= len(self.current_playlist_items):
             print(f"Play Current: Invalid index {self.current_playlist_index}, wrapping to 0.")
             self.current_playlist_index = 0 # Wrap around or handle end

        if not self.current_playlist_items: # Double check after potential wrap
             print("Play Current: Playlist empty after index adjustment.")
             self.stop_mp3()
             self.emit_player_status()
             return

        item = self.current_playlist_items[self.current_playlist_index]
        mp3_file = item['mp3_file']

        if self.play_mp3(mp3_file):
            self.current_track_filename = mp3_file
            self.is_playing = True
            self.is_paused = False
            self.emit_player_status()
            # Don't increment index here, play_mp3 starts the check_playback loop
        else:
            # Failed to play this track, try next one? Or stop?
            print(f"Failed to play {mp3_file}. Stopping.")
            self.stop_mp3() # Or potentially try next: self.play_next()
            self.emit_player_status()


    def play_mp3(self, mp3_file):
        """Loads and plays a single mp3 file."""
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init():
             print("Cannot play MP3: Pygame Mixer not initialized.")
             return False
        try:
            mp3_path = os.path.join(MP3_DIR, mp3_file)
            print(f"Versuche MP3 abzuspielen: {mp3_path}")

            if not os.path.exists(mp3_path):
                print(f"MP3-Datei nicht gefunden: {mp3_path}")
                self.current_track_filename = None # Clear filename if not found
                return False

            pygame.mixer.music.load(mp3_path)
            # Volume is already set globally, no need to set it per track
            pygame.mixer.music.play()

            # Cancel previous timer if exists
            if self.playback_check_timer:
                self.playback_check_timer.cancel()

            # Start polling to check when playback finishes
            self.check_playback()
            return True

        except Exception as e:
            print(f"Fehler beim Abspielen der MP3 '{mp3_file}': {e}")
            self.current_track_filename = None # Clear filename on error
            return False

    def check_playback(self):
        """Checks playback status and schedules next check or next song."""
        if not self.running: # Stop checking if BertiBox stopped
             return
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init():
             return # Stop if mixer stopped

        # Check only if we think we are playing and not paused
        if self.is_playing and not self.is_paused:
            if not pygame.mixer.music.get_busy():
                print("Track finished.")
                # Song finished naturally, play next
                self.play_next(track_finished_naturally=True)
            else:
                # Still playing, schedule next check
                self.playback_check_timer = threading.Timer(0.2, self.check_playback)
                self.playback_check_timer.start()
        # If paused or stopped, do nothing here

    def stop_mp3(self):
        """Stops MP3 playback completely."""
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init(): return
        if self.is_playing or self.is_paused or pygame.mixer.music.get_busy():
            print("Stoppe MP3 Wiedergabe")
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() # Unload the track
        # Cancel timer if running
        if self.playback_check_timer:
            self.playback_check_timer.cancel()
            self.playback_check_timer = None
        self.cancel_sleep_timer() # Cancel sleep timer when stopping playback
        self.is_playing = False
        self.is_paused = False
        self.current_track_filename = None # Clear filename when stopped
        # Don't clear playlist/tag here, that's handled by tag removal logic
        # Emit status handled by caller (e.g., handle_tag, start loop)


    def pause_playback(self):
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init(): return
        if self.is_playing and not self.is_paused:
            print("Pausiere Wiedergabe")
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = True # Keep is_playing true to indicate it *can* resume
             # Cancel the timer check while paused
            if self.playback_check_timer:
                self.playback_check_timer.cancel()
                self.playback_check_timer = None
            self.cancel_sleep_timer() # Cancel sleep timer when pausing
            self.emit_player_status()

    def resume_playback(self):
        if not hasattr(pygame, 'mixer') or not pygame.mixer.get_init(): return
        if self.is_playing and self.is_paused:
            print("Setze Wiedergabe fort")
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.check_playback() # Restart the finish check
            self.cancel_sleep_timer() # Cancel sleep timer if stopping completely
            self.emit_player_status()
        elif not self.is_playing and self.current_playlist:
            # If stopped but playlist loaded, treat as play from current index
            print("Wiedergabe nicht pausiert, starte vom aktuellen Index")
            self.play_current_track()


    def play_next(self, track_finished_naturally=False):
        """Plays the next track in the playlist."""
        if not self.current_playlist or not self.current_playlist_items:
            print("Play Next: No playlist loaded.")
            return

        self.current_playlist_index += 1
        if self.current_playlist_index >= len(self.current_playlist_items):
            print("Ende der Playlist erreicht, starte von vorne.")
            self.current_playlist_index = 0

        print(f"Spiele nächsten Titel (Index {self.current_playlist_index})")
        self.play_current_track() # This handles playing and status emit

    def play_previous(self):
        """Plays the previous track in the playlist."""
        if not self.current_playlist or not self.current_playlist_items:
            print("Play Previous: No playlist loaded.")
            return

        self.current_playlist_index -= 1
        if self.current_playlist_index < 0:
            print("Anfang der Playlist erreicht, springe zum Ende.")
            self.current_playlist_index = len(self.current_playlist_items) - 1
            if self.current_playlist_index < 0: # Handle empty list case
                self.current_playlist_index = 0

        print(f"Spiele vorherigen Titel (Index {self.current_playlist_index})")
        self.play_current_track() # This handles playing and status emit


    def stop(self):
        """Stops BertiBox, RFID reader, and Pygame."""
        print("Stoppe BertiBox")
        self.running = False
        if self.rfid_reader:
            self.rfid_reader.stop_reading()
            self.rfid_reader.cleanup()
        self.stop_mp3() # Ensure playback is stopped
         # Cancel timer if exists
        if self.playback_check_timer:
            self.playback_check_timer.cancel()
            self.playback_check_timer = None
        if hasattr(pygame, 'mixer') and pygame.mixer.get_init():
            pygame.mixer.quit()
        if pygame.get_init():
            pygame.quit()
        print("BertiBox gestoppt.")
        # self.db.cleanup() # Cleanup handled by Flask app context usually

    def get_player_status(self):
        """Returns the current player state."""
        status = {
            'tag_id': self.current_tag_id,
            'playlist': self.current_playlist, # Contains id, name, items list
            'current_track_index': self.current_playlist_index,
            'current_track_filename': self.current_track_filename,
            'is_playing': self.is_playing and not self.is_paused, # True only if actively playing
            'is_paused': self.is_paused, # True if paused,
            'tag_name': self.current_tag_name, # Add the current tag's name
            'volume': self.current_volume, # Return the stored volume
            'sleep_timer_remaining': self.get_sleep_timer_remaining() # Add remaining sleep time
        }
        # print(f"Get Status: {status}") # Debug log
        return status

    def emit_player_status(self):
        """Emits the current player status via SocketIO."""
        status = self.get_player_status()
        # print(f"Emitting Status: {status}") # Debug log
        self.socketio.emit('player_status_update', status)

    def clear_current_tag_state(self):
         """Clears the state associated with the current tag and stops playback."""
         # No need to clear self.current_tag_id here, it's cleared in start loop to prevent re-trigger
         print(f"Clearing player state due to tag timeout/removal.")
         self.stop_mp3() # Stops playback, clears playback state
         # Keep self.current_tag_id as None (already set in start loop)
         self.current_playlist = None
         self.current_playlist_items = []
         self.current_playlist_index = 0
         self.current_track_filename = None
         self.current_tag_name = None # Clear tag name as well
         self.cancel_sleep_timer() # Also cancel sleep timer
         print(f"State cleared. Emitting player status.") # DEBUG
         self.emit_player_status() # Send update to player UI

    def set_volume_internal(self, volume_float):
        """Internal method to set volume in pygame and save to DB."""
        try:
            if 0.0 <= volume_float <= 1.0:
                print(f"Setting internal volume to: {volume_float}")
                self.current_volume = volume_float
                if hasattr(pygame, 'mixer') and pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(self.current_volume)
                # Save to DB
                # Use socketio background task for DB operation to avoid blocking main thread/event handler?
                # For now, direct call, assuming set_setting is quick.
                self.db.set_setting('global_volume', str(self.current_volume))
            else:
                print(f"Internal volume set ignored, invalid value: {volume_float}")
        except Exception as e:
            print(f"Error in set_volume_internal: {e}")

    def get_sleep_timer_remaining(self):
        """Calculates remaining seconds for the sleep timer, or None."""
        if self.sleep_timer_end_time:
            remaining = self.sleep_timer_end_time - time.time()
            return max(0, remaining)
        return None

    def set_sleep_timer(self, duration_minutes):
        """Starts or restarts the sleep timer."""
        try:
            duration_seconds = int(duration_minutes) * 60
            if duration_seconds <= 0:
                print("Sleep timer duration must be positive.")
                self.cancel_sleep_timer() # Cancel if duration is invalid
                return

            self.cancel_sleep_timer() # Cancel any existing timer first

            self.sleep_timer_end_time = time.time() + duration_seconds
            self.sleep_timer = threading.Timer(duration_seconds, self._sleep_timer_expired)
            self.sleep_timer.daemon = True # Ensure thread doesn't block exit
            self.sleep_timer.start()
            print(f"Sleep timer set for {duration_minutes} minutes.")
            self.emit_player_status() # Notify clients
        except (ValueError, TypeError) as e:
            print(f"Invalid duration for sleep timer: {duration_minutes}. Error: {e}")
            self.cancel_sleep_timer() # Ensure no invalid timer is left

    def _sleep_timer_expired(self):
        """Called when the sleep timer finishes."""
        print("Sleep timer expired. Pausing playback.")
        self.sleep_timer = None # Clear timer object reference
        self.sleep_timer_end_time = None # Clear end time
        self.pause_playback() # Pause the music (which also emits status)
        # No need to emit status here, pause_playback does it.

    def cancel_sleep_timer(self):
        """Cancels the active sleep timer, if any."""
        if self.sleep_timer:
            print("Cancelling active sleep timer.")
            self.sleep_timer.cancel()
            self.sleep_timer = None
        was_active = self.sleep_timer_end_time is not None
        self.sleep_timer_end_time = None
        if was_active: # Only emit status if a timer was actually cancelled
            self.emit_player_status()

# --- Helper function to update BertiBox playlist state --- 
def update_berti_box_playlist(playlist_id):
     """Helper to reload playlist items in BertiBox and emit status."""
     if not berti_box:
          print("Update Helper: BertiBox not initialized.")
          return
     print(f"Helper: Updating BertiBox internal playlist for ID: {playlist_id}")
     try:
         # Use new session for safety in background task?
         # Let's try without first, assuming db methods handle sessions.
         updated_items_data = db.get_playlist_items(playlist_id)
         if berti_box.current_playlist and berti_box.current_playlist.get('id') == playlist_id:
              berti_box.current_playlist_items = updated_items_data
              # Also update the simplified list in the main playlist dict
              berti_box.current_playlist['items'] = [{'id': i['id'], 'mp3_file': i['mp3_file'], 'position': i['position']} for i in updated_items_data]
              # Adjust index if it's now out of bounds (e.g., after deletions)
              if berti_box.current_playlist_index >= len(updated_items_data):
                   berti_box.current_playlist_index = max(0, len(updated_items_data) - 1)
              print(f"Helper: BertiBox playlist {playlist_id} updated internally.")
              berti_box.emit_player_status() # Send update with new list/index
         else:
             # Playlist is not the currently active one in BertiBox, no internal update needed.
             print(f"Helper: Playlist {playlist_id} is not the active one in BertiBox.")
     except Exception as e:
          print(f"Helper: Error updating BertiBox playlist {playlist_id} in background: {e}")
          traceback.print_exc()

# ---------------- Flask Routes & SocketIO Handlers ----------------

@app.route('/')
def index():
    try:
        mp3_files = [f for f in os.listdir(MP3_DIR) if f.endswith('.mp3')]
    except FileNotFoundError:
        mp3_files = []
        print(f"Warning: MP3 directory '{MP3_DIR}' not found.")
    # Add a link to the player page
    return render_template('index.html', mp3_files=mp3_files, player_available=True)

@app.route('/player')
def player():
    # This route serves the HTML for the player interface
    return render_template('player.html')

# --- API Endpoints (Keep existing ones for now, but player control via SocketIO) ---

# Removed /api/current-tag POST endpoint, handled by BertiBox directly

@app.route('/api/tags', methods=['GET'])
def get_tags():
    try:
        tags = db.get_all_tags() # Expects list of dicts including playlist info
        # Process tags to ensure structure is consistent for JSON
        processed_tags = []
        for tag in tags:
            playlist_name = None
            playlist_id = None
            # Check if 'playlists' key exists and is a non-empty list
            if tag.get('playlists') and isinstance(tag['playlists'], list) and len(tag['playlists']) > 0:
                # Safely access the first playlist's details
                playlist_name = tag['playlists'][0].get('name')
                playlist_id = tag['playlists'][0].get('id')
            
            processed_tags.append({
                'id': tag.get('id'),
                'tag_id': tag.get('tag_id'),
                'name': tag.get('name'),
                'playlist_name': playlist_name,
                'playlist_id': playlist_id
            })

        return jsonify(processed_tags)
    except Exception as e:
        print(f"Error in get_tags: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ... (keep other existing API routes: POST /tags, DELETE /tags/<tag_id>, POST /playlists, etc.) ...
# ... Make sure they still function correctly with the shared db instance ...
@app.route('/api/tags', methods=['POST'])
def add_tag():
    data = request.get_json()
    tag_id = data.get('tag_id')
    name = data.get('name')

    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400

    session = db.get_session()
    try:
        # Prüfe, ob der Tag bereits existiert (using tag_id)
        existing_tag_orm = session.query(Tag).filter_by(tag_id=tag_id).first()

        if existing_tag_orm:
            # Tag aktualisieren
            existing_tag_orm.name = name
            session.commit()
            # Fetch updated data for response
            tag_data = db.get_tag(tag_id) # Use original method to get dict structure
            session.close()
            return jsonify({
                'id': tag_data.get('id'),
                'tag_id': tag_data.get('tag_id'),
                'name': tag_data.get('name'),
                'playlist_name': tag_data['playlists'][0]['name'] if tag_data.get('playlists') else None,
                'playlist_id': tag_data['playlists'][0]['id'] if tag_data.get('playlists') else None
            })

        # Neuen Tag erstellen
        new_tag = Tag(tag_id=tag_id, name=name)
        session.add(new_tag)
        session.flush() # Assign ID before creating playlist

        # Use the tag's name (or fallback) as the playlist name
        playlist_default_name = name or f"Tag {tag_id}" 
        playlist = Playlist(name=playlist_default_name)
        new_tag.playlists.append(playlist)
        session.add(playlist)
        session.commit()

        playlist_id = playlist.id
        playlist_name = playlist.name # Should now be the tag name or fallback
        tag_db_id = new_tag.id

        session.close() # Close session after commit

        return jsonify({
            'id': tag_db_id,
            'tag_id': tag_id,
            'name': name,
            'playlist_id': playlist_id,
            'playlist_name': playlist_name
        })
    except Exception as e:
        session.rollback()
        print(f"Error in add_tag: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/tags/<tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    if db.delete_tag(tag_id): # Assumes this handles related playlist deletions correctly
        # Optional: Update BertiBox if the deleted tag was the current one
        if berti_box and berti_box.current_tag_id == tag_id:
             berti_box.stop_mp3()
             berti_box.current_tag_id = None
             berti_box.current_playlist = None
             berti_box.current_playlist_items = []
             berti_box.current_playlist_index = 0
             berti_box.emit_player_status()
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Tag not found or could not be deleted'}), 404

@app.route('/api/playlists', methods=['POST'])
def add_playlist():
    # This route might need adjustment as the UI/BertiBox currently assumes
    # one playlist per tag, automatically created.
    # If explicitly creating playlists becomes a feature, this needs review.
    data = request.get_json()
    tag_id = data.get('tag_id')
    name = data.get('name')

    if not tag_id or not name:
        return jsonify({'error': 'Tag ID and name are required'}), 400

    session = db.get_session()
    try:
        tag = session.query(Tag).filter_by(tag_id=tag_id).first()
        if not tag:
             session.close()
             return jsonify({'error': f'Tag with ID {tag_id} not found'}), 404

        # Check if tag already has a playlist - enforce one-playlist rule
        if tag.playlists:
             session.close()
             return jsonify({'error': f'Tag {tag_id} already has a playlist. Only one playlist per tag is currently supported.'}), 400

        playlist = Playlist(name=name)
        tag.playlists.append(playlist)
        session.add(playlist)
        session.commit()

        playlist_id = playlist.id
        playlist_name = playlist.name

        session.close()
        return jsonify({
            'id': playlist_id,
            'name': playlist_name,
            'tag_id': tag_id
        })
    except Exception as e:
        session.rollback()
        print(f"Error in add_playlist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/playlists/<int:playlist_id>/items', methods=['GET'])
def get_playlist_items(playlist_id):
    try:
        items = db.get_playlist_items(playlist_id) # Should return list of dicts sorted by position
        return jsonify(items)
    except Exception as e:
        print(f"Error getting playlist items {playlist_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlists/<int:playlist_id>/items', methods=['POST'])
def add_playlist_item(playlist_id):
    # This endpoint might be less used if using batch add primarily
    data = request.get_json()
    mp3_file = data.get('mp3_file')

    if not mp3_file:
        return jsonify({'error': 'MP3 file is required'}), 400

    try:
        # Let database handle position assignment
        item = db.add_playlist_item(playlist_id, mp3_file)
        if item:
            # If bertibox is currently playing this playlist, update its state
            if berti_box and berti_box.current_playlist and berti_box.current_playlist['id'] == playlist_id:
                 # Reload items and update BertiBox's internal state
                 updated_items_data = db.get_playlist_items(playlist_id)
                 berti_box.current_playlist_items = updated_items_data
                 berti_box.current_playlist['items'] = [{'id': i['id'], 'mp3_file': i['mp3_file'], 'position': i['position']} for i in updated_items_data]
                 berti_box.emit_player_status() # Send update

            return jsonify({
                'id': item.id,
                'playlist_id': item.playlist_id,
                'mp3_file': item.mp3_file,
                'position': item.position
            })
        return jsonify({'error': 'Playlist not found or item could not be added'}), 404
    except Exception as e:
        print(f"Error adding item to playlist {playlist_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist-items/<int:item_id>', methods=['PUT'])
def update_playlist_item_endpoint(item_id):
    data = request.get_json()
    new_position = data.get('position')

    if new_position is None: # Check for None, 0 is a valid position
        return jsonify({'error': 'New position is required'}), 400
    try:
         new_position = int(new_position) # Ensure integer
    except (ValueError, TypeError):
         return jsonify({'error': 'Position must be an integer'}), 400

    # 1. Get playlist_id *before* updating the position
    session = db.get_session()
    item_obj = session.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item_obj:
        session.close()
        print(f"Update Error: Item {item_id} not found in DB.")
        return jsonify({'error': 'Item not found'}), 404
    playlist_id = item_obj.playlist_id
    session.close() # Close session after getting the ID

    try:
        # 2. Call the update function (assume it returns True/False)
        update_successful = db.update_playlist_item_position(item_id, new_position)
        
        # 3. Check the boolean result
        if update_successful:
             print(f"Updated position for item {item_id} in playlist {playlist_id} to {new_position}")
             # 4. Update BertiBox if this playlist is active, using the fetched playlist_id
             if berti_box and berti_box.current_playlist and berti_box.current_playlist.get('id') == playlist_id:
                  print(f"Scheduling BertiBox update for playlist {playlist_id}")
                  socketio.start_background_task(update_berti_box_playlist, playlist_id)
             return jsonify({'status': 'success'})
        else:
            # DB function returned False
            print(f"DB Error: update_playlist_item_position returned False for item {item_id}")
            return jsonify({'error': 'Item position could not be updated (DB operation failed)'}), 500 # Use 500 for server-side DB failure?
            
    except ValueError as ve: # Catch specific errors from DB layer if applicable
         print(f"Value error updating playlist item {item_id}: {ve}")
         return jsonify({'error': str(ve)}), 400
    except Exception as e:
         print(f"Error updating playlist item {item_id}: {e}")
         traceback.print_exc()
         return jsonify({'error': str(e)}), 500


@app.route('/api/playlist-items/<int:item_id>', methods=['DELETE']) # Use item_id from path
def delete_playlist_item(item_id):
    # Need playlist_id to update BertiBox state if necessary
    session = db.get_session()
    item_orm = session.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item_orm:
        session.close()
        return jsonify({'error': 'Item not found'}), 404
    playlist_id = item_orm.playlist_id
    session.close() # Close session after getting id

    if db.delete_playlist_item(item_id): # This handles the actual deletion and reordering
        # If bertibox is currently playing the affected playlist, update its state
        if berti_box and berti_box.current_playlist and berti_box.current_playlist['id'] == playlist_id:
             # Reload items and update BertiBox's internal state
             updated_items_data = db.get_playlist_items(playlist_id)
             berti_box.current_playlist_items = updated_items_data
             berti_box.current_playlist['items'] = [{'id': i['id'], 'mp3_file': i['mp3_file'], 'position': i['position']} for i in updated_items_data]

             # Adjust current index if needed (e.g., if deleted item was current or before)
             if berti_box.current_playlist_index >= len(berti_box.current_playlist_items):
                  # If the last item was deleted, wrap to 0 or stop if empty?
                  # Let's wrap to 0 for now if list not empty, otherwise index becomes 0 anyway.
                  berti_box.current_playlist_index = 0
             # Note: We don't automatically stop/change track here, just update the list state.
             # The player UI will reflect the change, and user interaction or track finish handles playback flow.
             berti_box.emit_player_status() # Send update
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Item not found or could not be deleted'}), 404


@app.route('/api/mp3-files', methods=['GET'])
def get_mp3_files():
    try:
        mp3_files = [f for f in os.listdir(MP3_DIR) if f.endswith('.mp3')]
        return jsonify(mp3_files)
    except FileNotFoundError:
        print(f"MP3 directory not found at: {MP3_DIR}")
        return jsonify([]) # Return empty list if dir doesn't exist
    except Exception as e:
        print(f"Error listing MP3 files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags/<tag_id>/playlist', methods=['GET'])
def get_tag_playlist(tag_id):
    # This route is used by the management UI to load playlist on tag selection.
    try:
        tag_data = db.get_tag(tag_id) # Fetches tag and associated playlist info
        if not tag_data or not tag_data.get('playlists'):
            # If tag exists but has no playlist (shouldn't happen with auto-creation)
            # Return structure indicating no playlist associated
             return jsonify({'id': None, 'name': None, 'items': []})

        # Assuming the first playlist is the relevant one
        playlist_info = tag_data['playlists'][0]
        playlist_id = playlist_info['id']
        items_data = db.get_playlist_items(playlist_id) # Fetch items sorted by position

        return jsonify({
            'id': playlist_id,
            'name': playlist_info.get('name', f"Playlist {playlist_id}"),
            'items': items_data # Return the detailed items directly
        })
    except Exception as e:
        print(f"Error getting playlist for tag {tag_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Batch add needs to ensure positions are handled correctly by db.add_playlist_items
@app.route('/api/playlists/<int:playlist_id>/items/batch', methods=['POST'])
def add_playlist_items_batch(playlist_id):
    data = request.get_json()
    mp3_files = data.get('mp3_files', [])

    if not mp3_files:
        return jsonify({'error': 'MP3 files list is required'}), 400

    try:
        # Assume db.add_playlist_items adds them and handles positioning
        # And assume it returns a list of dicts representing the added items
        added_items_dicts = db.add_playlist_items(playlist_id, mp3_files)
        if added_items_dicts:
             print(f"Added batch of {len(mp3_files)} items to playlist {playlist_id}")
             # Update BertiBox if this playlist is active
             if berti_box and berti_box.current_playlist and berti_box.current_playlist.get('id') == playlist_id:
                  socketio.start_background_task(update_berti_box_playlist, playlist_id)

             # Return the list of added items (already dicts)
             # The original code expected ORM objects, hence the error.
             # Now we assume added_items_dicts is the list we want to return.
             response_items = added_items_dicts
            
             # Simplified return assuming db function returns list of dicts:
             # response_items = added_items_dicts
             # If it still returns ORM objects, this would need attribute access:
             # response_items = [{'id': item.id, 'playlist_id': item.playlist_id, 'mp3_file': item.mp3_file, 'position': item.position}
             #                  for item in added_items_orm] # Assuming added_items_orm is list of ORM objects

             return jsonify(response_items), 201 # Created
        else:
            # Playlist not found or DB error during add
            return jsonify({'error': 'Playlist not found or items could not be added'}), 404
    except Exception as e:
        print(f"Error adding batch items to playlist {playlist_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- MP3 Upload Endpoint ---
ALLOWED_EXTENSIONS = {'mp3'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload-mp3', methods=['POST'])
def upload_mp3():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename) and file.mimetype == 'audio/mpeg':
        filename = secure_filename(file.filename)
        filepath = os.path.join(MP3_DIR, filename)
        
        # Check if file already exists
        if os.path.exists(filepath):
             return jsonify({'error': f'File \'{filename}\' already exists.'}), 409 # 409 Conflict
        
        try:
            file.save(filepath)
            print(f"MP3 file saved: {filepath}")
            # Optionally, trigger a refresh of the MP3 list for the modal
            # This could be done via SocketIO event if needed immediately,
            # or the frontend can refresh next time it fetches the list.
            return jsonify({'status': 'success', 'filename': filename})
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            traceback.print_exc()
            return jsonify({'error': f'Could not save file: {str(e)}'}), 500
    elif not allowed_file(file.filename) or file.mimetype != 'audio/mpeg':
         return jsonify({'error': 'Invalid file type. Only MP3 files are allowed.'}), 400
    else:
        return jsonify({'error': 'Unknown error during file check'}), 500

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send current status immediately to the new client
    if berti_box:
        # Use socketio.start_background_task for safety if status involves DB access
        # Though get_player_status should ideally use cached data
        socketio.start_background_task(berti_box.emit_player_status)
        # berti_box.emit_player_status() # Direct call might be okay if no blocking ops

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_player_status')
def handle_request_player_status():
    print('Received request for player status')
    if berti_box:
        socketio.start_background_task(berti_box.emit_player_status)
        # berti_box.emit_player_status()

@socketio.on('play_pause')
def handle_play_pause():
    print('Received play/pause command')
    if berti_box:
        # Run in background task to avoid blocking websocket handler
        socketio.start_background_task(lambda: berti_box.pause_playback() if (berti_box.is_playing and not berti_box.is_paused) else berti_box.resume_playback())

@socketio.on('play_track') # Specific track play
def handle_play_track(data):
     index = data.get('index')
     print(f'Received play track command for index: {index}')
     if berti_box and index is not None:
         try:
             index_int = int(index)
             # Check validity within a background task potentially
             if berti_box.current_playlist and 0 <= index_int < len(berti_box.current_playlist_items):
                  # Schedule the actual playback in a background task
                  socketio.start_background_task(lambda idx=index_int: (setattr(berti_box, 'current_playlist_index', idx), berti_box.play_current_track()))
             else:
                  print(f"Invalid index {index_int} for current playlist")
         except ValueError:
             print(f"Invalid index format: {index}")


@socketio.on('pause') # Explicit pause
def handle_pause():
    print('Received pause command')
    if berti_box:
        socketio.start_background_task(berti_box.pause_playback)

@socketio.on('resume') # Explicit resume
def handle_resume():
    print('Received resume command')
    if berti_box:
        socketio.start_background_task(berti_box.resume_playback)


@socketio.on('next_track')
def handle_next_track():
    print('Received next track command')
    if berti_box:
        socketio.start_background_task(berti_box.play_next)

@socketio.on('previous_track')
def handle_previous_track():
    print('Received previous track command')
    if berti_box:
        socketio.start_background_task(berti_box.play_previous)

@socketio.on('set_volume')
def handle_set_volume(data):
    volume = data.get('volume')
    print(f'Received set volume command: {volume}')
    if berti_box and volume is not None:
        try:
            vol_float = float(volume)
            if 0.0 <= vol_float <= 1.0 and hasattr(pygame, 'mixer') and pygame.mixer.get_init():
                # Volume setting is usually quick, direct call might be fine
                # but background task is safer if unsure
                socketio.start_background_task(lambda v=vol_float: (
                    berti_box.set_volume_internal(v), # Use internal method via the global berti_box instance
                    berti_box.emit_player_status() # Emit status with new volume
                ))
            else:
                 print(f"Invalid volume value: {vol_float}")
        except ValueError:
            print(f"Invalid volume format: {volume}")

@socketio.on('set_sleep_timer')
def handle_set_sleep_timer(data):
    duration_minutes = data.get('duration')
    print(f'Received set sleep timer command: {duration_minutes} minutes')
    if berti_box and duration_minutes is not None:
        # Run in background task to avoid blocking handler
        socketio.start_background_task(berti_box.set_sleep_timer, duration_minutes)

@socketio.on('cancel_sleep_timer')
def handle_cancel_sleep_timer():
    print('Received cancel sleep timer command')
    if berti_box:
        # Run in background task
        socketio.start_background_task(berti_box.cancel_sleep_timer)

# --- Cleanup ---
def cleanup():
    print("Flask app shutting down...")
    if berti_box:
        berti_box.stop() # This should handle pygame quit etc.
    db.cleanup() # Ensure DB session/engine is cleaned up

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask app and BertiBox...")
    # Register cleanup function
    atexit.register(cleanup)

    # Initialize BertiBox first (needs db)
    db.init_db() # Create tables if they don't exist
    berti_box = BertiBox(socketio, db) # Pass socketio and db instances

    # Start BertiBox in a background thread only if initialized correctly
    bertibox_thread = None
    # if hasattr(berti_box, 'running') and berti_box.running is not False: # Check if init failed
    # Check if pygame/mixer actually initialized
    if berti_box.pygame_initialized and berti_box.mixer_initialized:
        print("BertiBox initialized successfully, starting background thread...")
        bertibox_thread = threading.Thread(target=berti_box.start, name="BertiBoxThread", daemon=True)
        bertibox_thread.start()
    else:
         print("BertiBox instance created, but Pygame/Mixer init failed. Playback disabled.")
         # Allow web interface to run without playback
    # else:
    #      # This case implies BertiBox __init__ returned early due to critical error
    #      print("BertiBox could not be initialized (critical error in __init__). Running web interface without playback functionality.")


    # Start Flask-SocketIO server
    # Allow connections from any IP on the network (0.0.0.0)
    # use_reloader=False is crucial when using background threads/hardware.
    # debug=False is recommended for production/stable use.
    try:
        socketio.run(app, host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    except Exception as e:
         print(f"CRITICAL: Failed to start Flask-SocketIO server: {e}")
         traceback.print_exc()

    # Optional: Join the thread if needed, though daemon=True should handle exit
    # if bertibox_thread:
    #     bertibox_thread.join() # This would block shutdown until thread finishes
