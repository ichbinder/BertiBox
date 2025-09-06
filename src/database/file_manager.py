"""File management operations for BertiBox database."""

import os
import traceback
from .models import Tag, Playlist, PlaylistItem


class FileManager:
    def __init__(self, get_session):
        self.get_session = get_session
    
    def is_file_in_playlist(self, file_path: str) -> bool:
        """Checks if a given file path exists in any playlist THAT IS LINKED TO A TAG."""
        session = self.get_session()
        try:
            path_to_check = file_path.lstrip('/')
            print(f"[DB is_file_in_playlist] Checking DB for file '{path_to_check}' linked to a valid Tag")
            
            exists = (session.query(PlaylistItem.id)
                      .join(Playlist, PlaylistItem.playlist_id == Playlist.id)
                      .join(Tag, Playlist.tag_id == Tag.id)
                      .filter(PlaylistItem.mp3_file == path_to_check)
                      .first() is not None)

            print(f"[DB is_file_in_playlist] Result (linked to Tag?): {exists}")
            session.close()
            return exists
        except Exception as e:
            print(f"Error checking if file '{file_path}' is in a tagged playlist: {e}")
            session.rollback()
            session.close()
            return False

    def is_file_used(self, relative_path):  
        """Checks if a given relative file path is used in any playlist item."""
        session = self.get_session()
        try:
            count = session.query(PlaylistItem).filter(PlaylistItem.mp3_file == relative_path.lstrip('/')).count()
            return count > 0
        except Exception as e:
            print(f"Error checking if file '{relative_path}' is used: {e}")
            traceback.print_exc()
            return True 
        finally:
            session.close() 

    def update_path_references(self, old_path_relative, new_path_relative):
        """Updates file paths in PlaylistItem records when a file or folder is moved/renamed."""
        session = self.get_session()
        updated_count = 0
        try:
            old_path_db = old_path_relative.lstrip('/')
            new_path_db = new_path_relative.lstrip('/')
            
            items_to_update = session.query(PlaylistItem).filter(PlaylistItem.mp3_file == old_path_db).all()
            for item in items_to_update:
                print(f"DB Update: Changing PlaylistItem {item.id} path from '{item.mp3_file}' to '{new_path_db}'")
                item.mp3_file = new_path_db
                updated_count += 1

            old_dir_prefix = old_path_db + '/'
            new_dir_prefix = new_path_db + '/'
            items_in_dir = session.query(PlaylistItem).filter(PlaylistItem.mp3_file.startswith(old_dir_prefix)).all()
            for item in items_in_dir:
                original_path = item.mp3_file
                updated_path = original_path.replace(old_dir_prefix, new_dir_prefix, 1)
                print(f"DB Update: Changing PlaylistItem {item.id} path from '{original_path}' to '{updated_path}' (folder move)")
                item.mp3_file = updated_path
                updated_count += 1

            if updated_count > 0:
                session.commit()
                print(f"DB Update: Committed changes for {updated_count} playlist items.")
            return True
        
        except Exception as e:
            session.rollback()
            print(f"Database Error updating path references from '{old_path_db}' to '{new_path_db}': {e}")
            traceback.print_exc()
            return False
        finally:
            session.close()

    def are_files_in_folder_used(self, relative_folder_path, base_dir):
        """Recursively checks if any file within the given folder path is used in any playlist item."""
        try:
            base_dir_abs = os.path.abspath(base_dir)
            clean_relative_path = os.path.normpath(relative_folder_path.lstrip('/'))
            folder_full_path = os.path.join(base_dir_abs, clean_relative_path)
            folder_full_path = os.path.abspath(folder_full_path)

            if not os.path.isdir(folder_full_path):
                print(f"Warning: Folder '{folder_full_path}' not found during usage check.")
                return False

            print(f"Checking usage for files inside: {folder_full_path}")
            for root, dirs, files in os.walk(folder_full_path):
                for filename in files:
                    file_full_path = os.path.join(root, filename)
                    file_relative_path = os.path.relpath(file_full_path, base_dir_abs).replace(os.sep, '/')
                    print(f"  Checking file: {file_relative_path}")
                    if self.is_file_used(file_relative_path):
                        print(f"  --> Found used file: {file_relative_path}")
                        return True
            
            print(f"No used files found in folder: {relative_folder_path}")
            return False

        except Exception as e:
            print(f"Error checking folder usage for '{relative_folder_path}': {e}")
            traceback.print_exc()
            return True 

    def get_playlists_for_file(self, file_path: str) -> list[dict]:
        """Finds all Tags whose associated playlist contains the given file path."""
        session = self.get_session()
        tags_info = []
        try:
            path_to_check = file_path.lstrip('/')
            print(f"DB Query: Finding Tags for file_path = '{path_to_check}'")

            results = (session.query(Tag.tag_id, Tag.name)
                       .join(Playlist, Tag.id == Playlist.tag_id)
                       .join(PlaylistItem, Playlist.id == PlaylistItem.playlist_id)
                       .filter(PlaylistItem.mp3_file == path_to_check)
                       .distinct()
                       .all())

            for tag_rfid, tag_name in results:
                print(f"  -> Found Tag - RFID: {tag_rfid}, Name: {tag_name!r}") 
                tags_info.append({
                    'tag_id': tag_rfid,
                    'name': tag_name
                })
            print(f"DB Query: Found {len(tags_info)} Tags for file '{path_to_check}'")
            return tags_info

        except Exception as e:
            print(f"Database Error finding tags for file '{file_path}': {e}")
            traceback.print_exc()
            return [] 
        finally:
            session.close()