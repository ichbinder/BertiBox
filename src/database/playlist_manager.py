"""Playlist management operations for BertiBox database."""

import traceback
from .models import Tag, Playlist, PlaylistItem


class PlaylistManager:
    def __init__(self, get_session):
        self.get_session = get_session
    
    def add_playlist(self, tag_id, name):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if not tag:
                tag = Tag(tag_id=tag_id, name=name)
                session.add(tag)
                session.flush()
            
            playlist = Playlist(name=name, tag_id=tag.id)
            session.add(playlist)
            session.commit()
            session.refresh(playlist)
            
            _ = playlist.tag
            session.expunge(playlist)
            return playlist
        finally:
            session.close()
    
    def get_playlist(self, playlist_id):
        session = self.get_session()
        try:
            playlist = session.query(Playlist).filter_by(id=playlist_id).first()
            if playlist:
                _ = playlist.tag
                _ = playlist.items
                session.expunge(playlist)
            return playlist
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

            current_item_count = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).count()
            new_position = current_item_count
            print(f"Adding single item {mp3_file} to playlist {playlist_id} at position {new_position}")

            item = PlaylistItem(
                playlist_id=playlist_id,
                mp3_file=mp3_file,
                position=new_position
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            print(f"Single item added successfully with ID {item.id}.")
            
            result = {
                'id': item.id,
                'playlist_id': item.playlist_id,
                'mp3_file': item.mp3_file,
                'position': item.position
            }
            return result
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
            print(f"DB: Querying items for playlist {playlist_id}, ordered by position...")
            items = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).order_by(PlaylistItem.position).all()
            item_list = []
            for item in items:
                print(f"  -> Item ID: {item.id}, MP3: {item.mp3_file}, DB Position: {item.position}")
                item_list.append({
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                })
            print(f"DB: Returning {len(item_list)} items for playlist {playlist_id}")
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
            deleted_position = item_to_delete.position
            print(f"Deleting item {item_id} (MP3: {item_to_delete.mp3_file}) from playlist {playlist_id} at position {deleted_position}.")

            session.delete(item_to_delete)
            session.commit()
            
            print(f"Re-sequencing remaining items in playlist {playlist_id} after deletion.")
            remaining_items = session.query(PlaylistItem)\
                .filter_by(playlist_id=playlist_id)\
                .order_by(PlaylistItem.position.asc())\
                .all()
            
            needs_commit = False
            for index, item in enumerate(remaining_items):
                if item.position != index:
                    print(f"  Correcting position for item {item.id} (MP3: {item.mp3_file}) from {item.position} to {index}")
                    item.position = index
                    needs_commit = True

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
                return False

            playlist_id = item_to_move.playlist_id
            old_position = item_to_move.position
            target_position = new_position

            if old_position == target_position:
                print(f"Update Position: Item {item_id} already at position {target_position}.")
                return True

            if target_position > old_position:
                print(f"Moving item {item_id} DOWN from {old_position} to {target_position}. Shifting items in between.")
                session.query(PlaylistItem).\
                    filter(
                        PlaylistItem.playlist_id == playlist_id,
                        PlaylistItem.position > old_position,
                        PlaylistItem.position <= target_position
                    ).\
                    update({PlaylistItem.position: PlaylistItem.position - 1}, synchronize_session='fetch')
            else:
                print(f"Moving item {item_id} UP from {old_position} to {target_position}. Shifting items in between.")
                session.query(PlaylistItem).\
                    filter(
                        PlaylistItem.playlist_id == playlist_id,
                        PlaylistItem.position >= target_position,
                        PlaylistItem.position < old_position
                    ).\
                    update({PlaylistItem.position: PlaylistItem.position + 1}, synchronize_session='fetch')

            print(f"Setting final position for item {item_id} to {target_position}")
            item_to_move.position = target_position

            session.commit()
            print(f"Successfully updated position for item {item_id}.")
            return True

        except Exception as e:
            print(f"Error updating position for item {item_id} to {new_position}: {e}")
            traceback.print_exc()
            session.rollback()
            return False
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
            
            start_position = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).count()
            print(f"Batch adding {len(mp3_files)} items to playlist {playlist_id}, starting at position {start_position}")
            
            added_items_for_response = []
            added_orm_items = []

            for index, mp3_file in enumerate(mp3_files):
                current_position = start_position + index
                print(f"  - Adding: {mp3_file} at position {current_position}")
                item = PlaylistItem(
                    playlist_id=playlist_id,
                    mp3_file=mp3_file,
                    position=current_position
                )
                session.add(item)
                added_orm_items.append(item)
            
            session.flush()

            for item in added_orm_items:
                added_items_for_response.append({
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                })

            print(f"Committing {len(mp3_files)} new items for playlist {playlist_id}")
            session.commit()
            return added_items_for_response
        except Exception as e:
            print(f"Error batch adding items to playlist {playlist_id}: {e}")
            traceback.print_exc()
            session.rollback()
            return None
        finally:
            session.close()
    
    def assign_tag_to_file(self, tag_id, file_path_relative):
        """Assigns a file to a tag by adding it to the tag's associated playlist."""
        session = self.get_session()
        try:
            tag = session.query(Tag).filter(Tag.id == tag_id).first()
            if not tag:
                print(f"Assign Tag Error: Tag with DB ID {tag_id} not found.")
                return False

            if not tag.playlists:
                print(f"Assign Tag Error: No playlist found for Tag {tag_id} ('{tag.name}').")
                return False 
            
            playlist_id = tag.playlists[0].id
            playlist_name = tag.playlists[0].name

            cleaned_file_path = file_path_relative.lstrip('/')

            print(f"Assign Tag DB: Adding '{cleaned_file_path}' to Playlist ID {playlist_id} ('{playlist_name}') for Tag ID {tag_id}")
            added_item = self.add_playlist_item(playlist_id, cleaned_file_path)
            
            if added_item:
                print(f"Assign Tag DB: Successfully added item {added_item['id']}.")
                return True
            else:
                print(f"Assign Tag DB: Failed to add '{cleaned_file_path}' to Playlist ID {playlist_id} (possibly duplicate or DB error).")
                existing = session.query(PlaylistItem).filter_by(playlist_id=playlist_id, mp3_file=cleaned_file_path).first()
                if existing:
                    print(f"Assign Tag Info: File '{cleaned_file_path}' already exists in Playlist {playlist_id}.")
                    return True
                else:
                    return False

        except Exception as e:
            print(f"Database Error assigning tag {tag_id} to file '{file_path_relative}': {e}")
            traceback.print_exc()
            return False
        finally:
            session.close()