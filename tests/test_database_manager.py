import unittest
from unittest.mock import Mock, MagicMock, patch, call
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.manager import Database
from src.database.models import Base, Tag, Playlist, PlaylistItem, Setting


class TestDatabaseManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test database in memory."""
        # Create a temporary database file
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        
        # Patch config to use test database
        self.config_patcher = patch('src.database.manager.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.DATABASE_FILE = self.test_db_path
        self.mock_config.DEFAULT_VOLUME = 0.5
        self.mock_config.MP3_DIR = '/test/mp3'
        
        # Reset Database singleton
        Database._instance = None
        
        # Create database instance
        self.db = Database()
        self.db.init_db()
    
    def tearDown(self):
        """Clean up test database."""
        self.config_patcher.stop()
        
        # Close and remove test database
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
        # Reset singleton
        Database._instance = None
    
    def test_singleton_pattern(self):
        """Test that Database follows singleton pattern."""
        db1 = Database()
        db2 = Database()
        self.assertIs(db1, db2)
    
    def test_add_tag(self):
        """Test adding a tag."""
        tag = self.db.add_tag("TEST_TAG", "Test Tag Name")
        
        self.assertIsNotNone(tag)
        self.assertEqual(tag.tag_id, "TEST_TAG")
        self.assertEqual(tag.name, "Test Tag Name")
        
        # Verify in database
        retrieved = self.db.get_tag("TEST_TAG")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['tag_id'], "TEST_TAG")
        self.assertEqual(retrieved['name'], "Test Tag Name")
    
    def test_get_tag(self):
        """Test retrieving a tag."""
        self.db.add_tag("TEST_TAG", "Test Tag")
        
        tag_data = self.db.get_tag("TEST_TAG")
        
        self.assertIsNotNone(tag_data)
        self.assertEqual(tag_data['tag_id'], "TEST_TAG")
        self.assertEqual(tag_data['name'], "Test Tag")
        self.assertIsInstance(tag_data['playlists'], list)
    
    def test_get_tag_not_found(self):
        """Test retrieving non-existent tag."""
        tag_data = self.db.get_tag("NONEXISTENT")
        self.assertIsNone(tag_data)
    
    def test_delete_tag(self):
        """Test deleting a tag."""
        self.db.add_tag("DELETE_ME", "To be deleted")
        
        # Delete the tag
        result = self.db.delete_tag("DELETE_ME")
        self.assertTrue(result)
        
        # Verify deletion
        tag_data = self.db.get_tag("DELETE_ME")
        self.assertIsNone(tag_data)
    
    def test_delete_tag_not_found(self):
        """Test deleting non-existent tag."""
        result = self.db.delete_tag("NONEXISTENT")
        self.assertFalse(result)
    
    def test_update_tag(self):
        """Test updating a tag name."""
        self.db.add_tag("UPDATE_TAG", "Original Name")
        
        updated_tag = self.db.update_tag("UPDATE_TAG", "New Name")
        
        self.assertIsNotNone(updated_tag)
        self.assertEqual(updated_tag.name, "New Name")
        
        # Verify in database
        tag_data = self.db.get_tag("UPDATE_TAG")
        self.assertEqual(tag_data['name'], "New Name")
    
    def test_add_playlist(self):
        """Test adding a playlist to a tag."""
        tag = self.db.add_tag("TAG_WITH_PLAYLIST", "Tag")
        playlist = self.db.add_playlist("TAG_WITH_PLAYLIST", "Test Playlist")
        
        self.assertIsNotNone(playlist)
        self.assertEqual(playlist.name, "Test Playlist")
        
        # Verify tag has playlist
        tag_data = self.db.get_tag("TAG_WITH_PLAYLIST")
        self.assertEqual(len(tag_data['playlists']), 1)
        self.assertEqual(tag_data['playlists'][0]['name'], "Test Playlist")
    
    def test_add_playlist_creates_tag_if_missing(self):
        """Test that adding playlist creates tag if it doesn't exist."""
        playlist = self.db.add_playlist("NEW_TAG", "Auto-created Playlist")
        
        self.assertIsNotNone(playlist)
        
        # Verify tag was created
        tag_data = self.db.get_tag("NEW_TAG")
        self.assertIsNotNone(tag_data)
    
    def test_get_playlist(self):
        """Test retrieving a playlist."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Test Playlist")
        
        retrieved = self.db.get_playlist(playlist.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Playlist")
    
    def test_add_playlist_item(self):
        """Test adding an item to a playlist."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        item = self.db.add_playlist_item(playlist.id, "song.mp3")
        
        self.assertIsNotNone(item)
        self.assertEqual(item['mp3_file'], "song.mp3")
        self.assertEqual(item['position'], 0)
        
        # Add second item
        item2 = self.db.add_playlist_item(playlist.id, "song2.mp3")
        self.assertEqual(item2['position'], 1)
    
    def test_add_playlist_item_invalid_playlist(self):
        """Test adding item to non-existent playlist."""
        item = self.db.add_playlist_item(999, "song.mp3")
        self.assertIsNone(item)
    
    def test_get_playlist_items(self):
        """Test retrieving playlist items."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add items
        self.db.add_playlist_item(playlist.id, "song1.mp3")
        self.db.add_playlist_item(playlist.id, "song2.mp3")
        self.db.add_playlist_item(playlist.id, "song3.mp3")
        
        items = self.db.get_playlist_items(playlist.id)
        
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['mp3_file'], "song1.mp3")
        self.assertEqual(items[0]['position'], 0)
        self.assertEqual(items[1]['mp3_file'], "song2.mp3")
        self.assertEqual(items[1]['position'], 1)
        self.assertEqual(items[2]['mp3_file'], "song3.mp3")
        self.assertEqual(items[2]['position'], 2)
    
    def test_delete_playlist_item(self):
        """Test deleting a playlist item and re-sequencing."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add items
        item1 = self.db.add_playlist_item(playlist.id, "song1.mp3")
        item2 = self.db.add_playlist_item(playlist.id, "song2.mp3")
        item3 = self.db.add_playlist_item(playlist.id, "song3.mp3")
        
        # Delete middle item
        result = self.db.delete_playlist_item(item2['id'])
        self.assertTrue(result)
        
        # Check re-sequencing
        items = self.db.get_playlist_items(playlist.id)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['mp3_file'], "song1.mp3")
        self.assertEqual(items[0]['position'], 0)
        self.assertEqual(items[1]['mp3_file'], "song3.mp3")
        self.assertEqual(items[1]['position'], 1)
    
    def test_update_playlist_item_position_move_down(self):
        """Test moving an item down in the playlist."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add items
        item1 = self.db.add_playlist_item(playlist.id, "song1.mp3")
        item2 = self.db.add_playlist_item(playlist.id, "song2.mp3")
        item3 = self.db.add_playlist_item(playlist.id, "song3.mp3")
        
        # Move first item to position 2
        result = self.db.update_playlist_item_position(item1['id'], 2)
        self.assertTrue(result)
        
        items = self.db.get_playlist_items(playlist.id)
        self.assertEqual(items[0]['mp3_file'], "song2.mp3")
        self.assertEqual(items[1]['mp3_file'], "song3.mp3")
        self.assertEqual(items[2]['mp3_file'], "song1.mp3")
    
    def test_update_playlist_item_position_move_up(self):
        """Test moving an item up in the playlist."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add items
        item1 = self.db.add_playlist_item(playlist.id, "song1.mp3")
        item2 = self.db.add_playlist_item(playlist.id, "song2.mp3")
        item3 = self.db.add_playlist_item(playlist.id, "song3.mp3")
        
        # Move last item to position 0
        result = self.db.update_playlist_item_position(item3['id'], 0)
        self.assertTrue(result)
        
        items = self.db.get_playlist_items(playlist.id)
        self.assertEqual(items[0]['mp3_file'], "song3.mp3")
        self.assertEqual(items[1]['mp3_file'], "song1.mp3")
        self.assertEqual(items[2]['mp3_file'], "song2.mp3")
    
    def test_add_playlist_items_batch(self):
        """Test adding multiple items at once."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add existing item
        self.db.add_playlist_item(playlist.id, "existing.mp3")
        
        # Add batch
        mp3_files = ["batch1.mp3", "batch2.mp3", "batch3.mp3"]
        items = self.db.add_playlist_items(playlist.id, mp3_files)
        
        self.assertIsNotNone(items)
        self.assertEqual(len(items), 3)
        
        # Verify positions
        all_items = self.db.get_playlist_items(playlist.id)
        self.assertEqual(len(all_items), 4)
        self.assertEqual(all_items[0]['mp3_file'], "existing.mp3")
        self.assertEqual(all_items[1]['mp3_file'], "batch1.mp3")
        self.assertEqual(all_items[2]['mp3_file'], "batch2.mp3")
        self.assertEqual(all_items[3]['mp3_file'], "batch3.mp3")
    
    def test_get_all_tags(self):
        """Test retrieving all tags."""
        self.db.add_tag("TAG1", "Tag One")
        self.db.add_tag("TAG2", "Tag Two")
        self.db.add_tag("TAG3", "Tag Three")
        
        self.db.add_playlist("TAG1", "Playlist 1")
        self.db.add_playlist("TAG2", "Playlist 2")
        
        tags = self.db.get_all_tags()
        
        self.assertEqual(len(tags), 3)
        tag_ids = [tag['tag_id'] for tag in tags]
        self.assertIn("TAG1", tag_ids)
        self.assertIn("TAG2", tag_ids)
        self.assertIn("TAG3", tag_ids)
    
    def test_get_setting(self):
        """Test retrieving a setting."""
        # Test default value
        value = self.db.get_setting("nonexistent", "default")
        self.assertEqual(value, "default")
        
        # Set a value
        self.db.set_setting("test_key", "test_value")
        
        # Retrieve it
        value = self.db.get_setting("test_key")
        self.assertEqual(value, "test_value")
    
    def test_set_setting(self):
        """Test setting a value."""
        result = self.db.set_setting("new_setting", "new_value")
        self.assertTrue(result)
        
        # Verify
        value = self.db.get_setting("new_setting")
        self.assertEqual(value, "new_value")
        
        # Update existing
        result = self.db.set_setting("new_setting", "updated_value")
        self.assertTrue(result)
        
        value = self.db.get_setting("new_setting")
        self.assertEqual(value, "updated_value")
    
    def test_set_setting_if_not_exists(self):
        """Test set_if_not_exists parameter."""
        # Set initial value
        self.db.set_setting("existing", "original")
        
        # Try to set with set_if_not_exists=True
        self.db.set_setting("existing", "new", set_if_not_exists=True)
        
        # Should keep original value
        value = self.db.get_setting("existing")
        self.assertEqual(value, "original")
        
        # Set new key with set_if_not_exists=True
        self.db.set_setting("new_key", "new_value", set_if_not_exists=True)
        value = self.db.get_setting("new_key")
        self.assertEqual(value, "new_value")
    
    def test_is_file_in_playlist(self):
        """Test checking if file is in a playlist linked to a tag."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        self.db.add_playlist_item(playlist.id, "linked.mp3")
        
        # Create orphan playlist (no tag)
        session = self.db.get_session()
        orphan_playlist = Playlist(name="Orphan")
        session.add(orphan_playlist)
        session.commit()
        orphan_id = orphan_playlist.id
        session.close()
        
        self.db.add_playlist_item(orphan_id, "orphan.mp3")
        
        # Test linked file
        self.assertTrue(self.db.is_file_in_playlist("linked.mp3"))
        self.assertTrue(self.db.is_file_in_playlist("/linked.mp3"))  # With leading slash
        
        # Test orphan file (should return False as it's not linked to a tag)
        self.assertFalse(self.db.is_file_in_playlist("orphan.mp3"))
        
        # Test non-existent file
        self.assertFalse(self.db.is_file_in_playlist("nonexistent.mp3"))
    
    def test_is_file_used(self):
        """Test checking if file is used in any playlist."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        self.db.add_playlist_item(playlist.id, "used.mp3")
        
        self.assertTrue(self.db.is_file_used("used.mp3"))
        self.assertTrue(self.db.is_file_used("/used.mp3"))  # With leading slash
        self.assertFalse(self.db.is_file_used("unused.mp3"))
    
    def test_update_path_references(self):
        """Test updating file paths when files are moved/renamed."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Add items
        self.db.add_playlist_item(playlist.id, "folder/file1.mp3")
        self.db.add_playlist_item(playlist.id, "folder/file2.mp3")
        self.db.add_playlist_item(playlist.id, "other.mp3")
        
        # Rename folder
        result = self.db.update_path_references("folder", "new_folder")
        self.assertTrue(result)
        
        # Verify updates
        items = self.db.get_playlist_items(playlist.id)
        mp3_files = [item['mp3_file'] for item in items]
        self.assertIn("new_folder/file1.mp3", mp3_files)
        self.assertIn("new_folder/file2.mp3", mp3_files)
        self.assertIn("other.mp3", mp3_files)
    
    def test_assign_tag_to_file(self):
        """Test assigning a tag to a file."""
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        
        # Get tag's database ID
        tag_data = self.db.get_tag("TAG")
        tag_db_id = tag_data['id']
        
        result = self.db.assign_tag_to_file(tag_db_id, "new_file.mp3")
        self.assertTrue(result)
        
        # Verify file was added
        items = self.db.get_playlist_items(playlist.id)
        mp3_files = [item['mp3_file'] for item in items]
        self.assertIn("new_file.mp3", mp3_files)
        
        # Test duplicate assignment (should return True)
        result = self.db.assign_tag_to_file(tag_db_id, "new_file.mp3")
        self.assertTrue(result)
    
    @patch('src.database.file_manager.os.walk')
    @patch('src.database.file_manager.os.path.isdir')
    def test_are_files_in_folder_used(self, mock_isdir, mock_walk):
        """Test checking if files in folder are used."""
        # Setup mock filesystem
        mock_isdir.return_value = True
        mock_walk.return_value = [
            ('/base/folder', ['subfolder'], ['file1.mp3', 'file2.mp3']),
            ('/base/folder/subfolder', [], ['file3.mp3'])
        ]
        
        # Add used file to database
        tag = self.db.add_tag("TAG", "Tag")
        playlist = self.db.add_playlist("TAG", "Playlist")
        self.db.add_playlist_item(playlist.id, "folder/file1.mp3")
        
        # Test folder with used files
        result = self.db.are_files_in_folder_used("folder", "/base")
        self.assertTrue(result)
    
    def test_get_playlists_for_file(self):
        """Test getting all tags that contain a specific file."""
        # Create multiple tags with playlists
        tag1 = self.db.add_tag("TAG1", "Tag One")
        playlist1 = self.db.add_playlist("TAG1", "Playlist 1")
        self.db.add_playlist_item(playlist1.id, "shared.mp3")
        
        tag2 = self.db.add_tag("TAG2", "Tag Two")
        playlist2 = self.db.add_playlist("TAG2", "Playlist 2")
        self.db.add_playlist_item(playlist2.id, "shared.mp3")
        
        tag3 = self.db.add_tag("TAG3", "Tag Three")
        playlist3 = self.db.add_playlist("TAG3", "Playlist 3")
        self.db.add_playlist_item(playlist3.id, "other.mp3")
        
        # Get tags for shared file
        tags = self.db.get_playlists_for_file("shared.mp3")
        
        self.assertEqual(len(tags), 2)
        tag_ids = [tag['tag_id'] for tag in tags]
        self.assertIn("TAG1", tag_ids)
        self.assertIn("TAG2", tag_ids)
        self.assertNotIn("TAG3", tag_ids)
        
        # Test with leading slash
        tags = self.db.get_playlists_for_file("/shared.mp3")
        self.assertEqual(len(tags), 2)
        
        # Test non-existent file
        tags = self.db.get_playlists_for_file("nonexistent.mp3")
        self.assertEqual(len(tags), 0)


if __name__ == '__main__':
    unittest.main()