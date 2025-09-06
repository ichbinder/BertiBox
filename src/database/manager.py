"""Database manager for BertiBox application."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from .tag_manager import TagManager
from .playlist_manager import PlaylistManager
from .file_manager import FileManager
from .settings_manager import SettingsManager
from .. import config


class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.engine = create_engine(f'sqlite:///{config.DATABASE_FILE}', 
                                      connect_args={'check_same_thread': False})
            self.Session = sessionmaker(bind=self.engine)
            
            # Initialize managers
            self.tags = TagManager(self.get_session)
            self.playlists = PlaylistManager(self.get_session)
            self.files = FileManager(self.get_session)
            self.settings = SettingsManager(self.get_session)
            
            self.initialized = True
    
    def get_session(self):
        return self.Session()
    
    def init_db(self):
        Base.metadata.create_all(self.engine)
        self.settings.set_setting('global_volume', 
                                 self.settings.get_setting('global_volume', 
                                                         default_value=str(config.DEFAULT_VOLUME)), 
                                 True)
    
    def cleanup(self):
        pass
    
    # Tag operations (delegated to TagManager)
    def add_tag(self, tag_id, name=None):
        return self.tags.add_tag(tag_id, name)
    
    def get_tag(self, tag_id):
        return self.tags.get_tag(tag_id)
    
    def delete_tag(self, tag_id):
        return self.tags.delete_tag(tag_id)
    
    def update_tag(self, tag_id, name):
        return self.tags.update_tag(tag_id, name)
    
    def get_all_tags(self):
        return self.tags.get_all_tags()
    
    # Playlist operations (delegated to PlaylistManager)
    def add_playlist(self, tag_id, name):
        return self.playlists.add_playlist(tag_id, name)
    
    def get_playlist(self, playlist_id):
        return self.playlists.get_playlist(playlist_id)
    
    def add_playlist_item(self, playlist_id, mp3_file):
        return self.playlists.add_playlist_item(playlist_id, mp3_file)
    
    def get_playlist_items(self, playlist_id):
        return self.playlists.get_playlist_items(playlist_id)
    
    def delete_playlist_item(self, item_id):
        return self.playlists.delete_playlist_item(item_id)
    
    def update_playlist_item_position(self, item_id, new_position):
        return self.playlists.update_playlist_item_position(item_id, new_position)
    
    def add_playlist_items(self, playlist_id, mp3_files):
        return self.playlists.add_playlist_items(playlist_id, mp3_files)
    
    def assign_tag_to_file(self, tag_id, file_path_relative):
        return self.playlists.assign_tag_to_file(tag_id, file_path_relative)
    
    # File operations (delegated to FileManager)
    def is_file_in_playlist(self, file_path):
        return self.files.is_file_in_playlist(file_path)
    
    def is_file_used(self, relative_path):
        return self.files.is_file_used(relative_path)
    
    def update_path_references(self, old_path_relative, new_path_relative):
        return self.files.update_path_references(old_path_relative, new_path_relative)
    
    def are_files_in_folder_used(self, relative_folder_path, base_dir):
        return self.files.are_files_in_folder_used(relative_folder_path, base_dir)
    
    def get_playlists_for_file(self, file_path):
        return self.files.get_playlists_for_file(file_path)
    
    # Settings operations (delegated to SettingsManager)
    def get_setting(self, key, default_value=None):
        return self.settings.get_setting(key, default_value)
    
    def set_setting(self, key, value, set_if_not_exists=False):
        return self.settings.set_setting(key, value, set_if_not_exists)