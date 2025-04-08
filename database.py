from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Sequence, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import os
import threading
import traceback

Base = declarative_base()

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, Sequence('tag_id_seq'), primary_key=True)
    tag_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100))
    playlists = relationship("Playlist", back_populates="tag")

class Playlist(Base):
    __tablename__ = 'playlists'
    id = Column(Integer, Sequence('playlist_id_seq'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'))
    name = Column(String(100))
    tag = relationship("Tag", back_populates="playlists")
    items = relationship("PlaylistItem", back_populates="playlist", order_by="PlaylistItem.position")

class PlaylistItem(Base):
    __tablename__ = 'playlist_items'
    id = Column(Integer, Sequence('playlist_item_id_seq'), primary_key=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id'))
    mp3_file = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    playlist = relationship("Playlist", back_populates="items")

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(50), primary_key=True)
    value = Column(String(255))

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            db_path = 'bertibox.db'
            self.engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})
            self.Session = sessionmaker(bind=self.engine)
            self.initialized = True
    
    def get_session(self):
        return self.Session()
    
    def init_db(self):
        Base.metadata.create_all(self.engine)
        self.set_setting('global_volume', self.get_setting('global_volume', default_value='0.8'), True)
    
    def cleanup(self):
        pass
    
    def add_tag(self, tag_id, name=None):
        session = self.get_session()
        try:
            tag = Tag(tag_id=tag_id, name=name)
            session.add(tag)
            session.commit()
            return tag
        finally:
            session.close()
    
    def get_tag(self, tag_id):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if tag:
                # Lade die Playlists explizit
                tag.playlists
                # Erstelle eine Kopie der Daten
                tag_data = {
                    'id': tag.id,
                    'tag_id': tag.tag_id,
                    'name': tag.name,
                    'playlists': [{
                        'id': playlist.id,
                        'name': playlist.name
                    } for playlist in tag.playlists]
                }
                return tag_data
            return None
        finally:
            session.close()
    
    def delete_tag(self, tag_id):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if tag:
                session.delete(tag)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def add_playlist(self, tag_id, name):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if not tag:
                tag = self.add_tag(tag_id)
            
            playlist = Playlist(name=name)
            tag.playlists.append(playlist)
            session.add(playlist)
            session.commit()
            return playlist
        finally:
            session.close()
    
    def get_playlist(self, playlist_id):
        session = self.get_session()
        try:
            return session.query(Playlist).filter_by(id=playlist_id).first()
        finally:
            session.close()
    
    def add_playlist_item(self, playlist_id, mp3_file):
        """Adds a single item to the end of the playlist with the correct position."""
        session = self.get_session()
        try:
            playlist = session.query(Playlist).filter_by(id=playlist_id).first()
            if not playlist:
                print(f"Add Item Error: Playlist {playlist_id} not found.")
                return None

            # Determine the next position by counting existing items (0-based index)
            current_item_count = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).count()
            new_position = current_item_count
            print(f"Adding single item {mp3_file} to playlist {playlist_id} at position {new_position}")

            # Create item with calculated position
            item = PlaylistItem(
                playlist_id=playlist_id,
                mp3_file=mp3_file,
                position=new_position
            )
            session.add(item)
            session.commit()
            print(f"Single item added successfully with ID {item.id}.")
            # Return the ORM object, the API route will convert it
            return item # Return the ORM object
        except Exception as e:
            print(f"Error adding single item {mp3_file} to playlist {playlist_id}: {e}")
            traceback.print_exc()
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_playlist_items(self, playlist_id):
        session = self.get_session()
        try:
            print(f"DB: Querying items for playlist {playlist_id}, ordered by position...") # DEBUG
            items = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).order_by(PlaylistItem.position).all()
            item_list = []
            for item in items:
                # DEBUG: Print position of each item as retrieved
                print(f"  -> Item ID: {item.id}, MP3: {item.mp3_file}, DB Position: {item.position}")
                item_list.append({
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                })
            print(f"DB: Returning {len(item_list)} items for playlist {playlist_id}") # DEBUG
            return item_list
        finally:
            session.close()
    
    def delete_playlist_item(self, item_id):
        """Deletes an item and re-sequences the remaining items in the playlist."""
        session = self.get_session()
        try:
            item_to_delete = session.query(PlaylistItem).filter_by(id=item_id).first()
            if not item_to_delete:
                print(f"Delete Error: Item {item_id} not found.")
                return False

            playlist_id = item_to_delete.playlist_id
            deleted_position = item_to_delete.position # Store before deleting
            print(f"Deleting item {item_id} (MP3: {item_to_delete.mp3_file}) from playlist {playlist_id} at position {deleted_position}.")

            # Delete the item
            session.delete(item_to_delete)
            session.commit() # Commit the deletion first
            
            # --- Re-sequence using fetch and loop (safer) --- 
            print(f"Re-sequencing remaining items in playlist {playlist_id} after deletion.")
            # Fetch all remaining items, ordered by their current position
            remaining_items = session.query(PlaylistItem)\
                .filter_by(playlist_id=playlist_id)\
                .order_by(PlaylistItem.position.asc())\
                .all()
            
            # Re-assign sequential positions (0, 1, 2, ...)
            needs_commit = False
            for index, item in enumerate(remaining_items):
                if item.position != index:
                    print(f"  Correcting position for item {item.id} (MP3: {item.mp3_file}) from {item.position} to {index}")
                    item.position = index
                    needs_commit = True # Mark that changes were made

            # Commit again only if positions were actually changed
            if needs_commit:
                print(f"Committing re-sequenced positions for playlist {playlist_id}.")
                session.commit()
            else:
                print(f"No position changes needed after deletion for playlist {playlist_id}.")
            
            print(f"Successfully processed deletion for item {item_id}.")
            return True
        except Exception as e:
            print(f"Error deleting or re-sequencing item {item_id}: {e}")
            traceback.print_exc()
            session.rollback()
            return False
        finally:
            session.close()
    
    def update_playlist_item_position(self, item_id, new_position):
        """Updates the position of an item and shifts other items accordingly."""
        session = self.get_session()
        try:
            item_to_move = session.query(PlaylistItem).filter_by(id=item_id).first()
            if not item_to_move:
                print(f"Update Position Error: Item {item_id} not found.")
                return False # Item not found

            playlist_id = item_to_move.playlist_id
            old_position = item_to_move.position
            target_position = new_position # This is the 0-based index from frontend

            if old_position == target_position:
                print(f"Update Position: Item {item_id} already at position {target_position}.")
                return True # No change needed

            # Determine shift direction and affected range
            if target_position > old_position:
                # --- Moving Down --- 
                # Shift items between old+1 and target UP (decrement position by 1)
                print(f"Moving item {item_id} DOWN from {old_position} to {target_position}. Shifting items in between.")
                session.query(PlaylistItem).\
                    filter(\
                        PlaylistItem.playlist_id == playlist_id,\
                        PlaylistItem.position > old_position,\
                        PlaylistItem.position <= target_position\
                    ).\
                    update({PlaylistItem.position: PlaylistItem.position - 1}, synchronize_session='fetch')\

            else: # target_position < old_position
                # --- Moving Up --- 
                # Shift items between target and old-1 DOWN (increment position by 1)
                print(f"Moving item {item_id} UP from {old_position} to {target_position}. Shifting items in between.")
                session.query(PlaylistItem).\
                    filter(\
                        PlaylistItem.playlist_id == playlist_id,\
                        PlaylistItem.position >= target_position,\
                        PlaylistItem.position < old_position\
                    ).\
                    update({PlaylistItem.position: PlaylistItem.position + 1}, synchronize_session='fetch')\

            # Finally, set the position of the moved item
            print(f"Setting final position for item {item_id} to {target_position}")
            item_to_move.position = target_position

            session.commit()
            print(f"Successfully updated position for item {item_id}.")
            return True # Indicate success

        except Exception as e:
            print(f"Error updating position for item {item_id} to {new_position}: {e}")
            traceback.print_exc()
            session.rollback()
            return False # Indicate failure
        finally:
            session.close()
    
    def update_tag(self, tag_id, name):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if tag:
                tag.name = name
                session.commit()
                return tag
            return None
        finally:
            session.close()
    
    def get_all_tags(self):
        session = self.get_session()
        try:
            tags = session.query(Tag).all()
            # Erstelle eine Liste von Dictionarys mit den Tag-Daten
            tag_list = []
            for tag in tags:
                # Lade die Playlists explizit
                tag.playlists
                tag_data = {
                    'id': tag.id,
                    'tag_id': tag.tag_id,
                    'name': tag.name,
                    'playlists': [{
                        'id': playlist.id,
                        'name': playlist.name
                    } for playlist in tag.playlists]
                }
                tag_list.append(tag_data)
            return tag_list
        finally:
            session.close()
    
    def add_playlist_items(self, playlist_id, mp3_files):
        """Adds multiple items to the end of the playlist with correct sequential positions."""
        session = self.get_session()
        try:
            playlist = session.query(Playlist).filter_by(id=playlist_id).first()
            if not playlist:
                print(f"Batch Add Error: Playlist {playlist_id} not found.")
                return None
            
            # Determine starting position based on current item count
            start_position = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).count()
            print(f"Batch adding {len(mp3_files)} items to playlist {playlist_id}, starting at position {start_position}")
            
            added_items_for_response = [] # List to hold dicts for the API response
            added_orm_items = [] # List to potentially return ORM objects if needed elsewhere

            for index, mp3_file in enumerate(mp3_files):
                current_position = start_position + index # Calculate 0-based position
                print(f"  - Adding: {mp3_file} at position {current_position}")
                item = PlaylistItem(
                    playlist_id=playlist_id,
                    mp3_file=mp3_file,
                    position=current_position
                )
                session.add(item)
                added_orm_items.append(item) # Keep track of ORM items if needed
            
            session.flush() # Assign IDs to ORM items before creating response dicts

            # Create list of dictionaries for the JSON response *after* flush/commit assigns IDs
            for item in added_orm_items:
                added_items_for_response.append({
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                })

            print(f"Committing {len(mp3_files)} new items for playlist {playlist_id}")
            session.commit()
            # Return the list of dictionaries
            return added_items_for_response
        except Exception as e:
            print(f"Error batch adding items to playlist {playlist_id}: {e}")
            traceback.print_exc()
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_setting(self, key, default_value=None):
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                return setting.value
            return default_value
        finally:
            session.close()
    
    def set_setting(self, key, value, set_if_not_exists=False):
        """Sets a setting value. If set_if_not_exists is True, it only sets the value if the key doesn't exist."""
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                if not set_if_not_exists:
                    print(f"Updating setting '{key}' to '{value}'")
                    setting.value = str(value) # Ensure value is stored as string
                    session.commit()
                else:
                    print(f"Setting '{key}' already exists, not overwriting.")
            else:
                print(f"Creating new setting '{key}' with value '{value}'")
                new_setting = Setting(key=key, value=str(value))
                session.add(new_setting)
                session.commit()
            return True
        except Exception as e:
            print(f"Error setting '{key}': {e}")
            session.rollback()
            return False
        finally:
            session.close() 