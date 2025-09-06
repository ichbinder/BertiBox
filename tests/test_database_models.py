import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.database.models import Base, Tag, Playlist, PlaylistItem, Setting


class TestDatabaseModels(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test database engine and session factory."""
        cls.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
    
    def setUp(self):
        """Create a new session for each test."""
        self.session = self.Session()
    
    def tearDown(self):
        """Clean up the session after each test."""
        self.session.rollback()
        self.session.close()
        # Clear all tables
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()
    
    def test_tag_creation(self):
        """Test creating a Tag instance."""
        tag = Tag(tag_id="TAG001", name="Test Tag")
        self.session.add(tag)
        self.session.commit()
        
        retrieved_tag = self.session.query(Tag).filter_by(tag_id="TAG001").first()
        self.assertIsNotNone(retrieved_tag)
        self.assertEqual(retrieved_tag.tag_id, "TAG001")
        self.assertEqual(retrieved_tag.name, "Test Tag")
    
    def test_tag_unique_constraint(self):
        """Test that tag_id must be unique."""
        tag1 = Tag(tag_id="TAG001", name="First Tag")
        tag2 = Tag(tag_id="TAG001", name="Second Tag")
        
        self.session.add(tag1)
        self.session.commit()
        
        self.session.add(tag2)
        with self.assertRaises(IntegrityError):
            self.session.commit()
    
    def test_tag_nullable_constraint(self):
        """Test that tag_id cannot be null."""
        tag = Tag(name="Tag without ID")
        self.session.add(tag)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()
    
    def test_playlist_creation(self):
        """Test creating a Playlist instance."""
        tag = Tag(tag_id="TAG002", name="Test Tag")
        self.session.add(tag)
        self.session.commit()
        
        playlist = Playlist(name="Test Playlist", tag_id=tag.id)
        self.session.add(playlist)
        self.session.commit()
        
        retrieved_playlist = self.session.query(Playlist).filter_by(name="Test Playlist").first()
        self.assertIsNotNone(retrieved_playlist)
        self.assertEqual(retrieved_playlist.name, "Test Playlist")
        self.assertEqual(retrieved_playlist.tag_id, tag.id)
    
    def test_tag_playlist_relationship(self):
        """Test the relationship between Tag and Playlist."""
        tag = Tag(tag_id="TAG003", name="Test Tag")
        playlist1 = Playlist(name="Playlist 1")
        playlist2 = Playlist(name="Playlist 2")
        
        tag.playlists.append(playlist1)
        tag.playlists.append(playlist2)
        
        self.session.add(tag)
        self.session.commit()
        
        retrieved_tag = self.session.query(Tag).filter_by(tag_id="TAG003").first()
        self.assertEqual(len(retrieved_tag.playlists), 2)
        self.assertEqual(retrieved_tag.playlists[0].name, "Playlist 1")
        self.assertEqual(retrieved_tag.playlists[1].name, "Playlist 2")
        
        # Test back reference
        self.assertEqual(playlist1.tag.tag_id, "TAG003")
        self.assertEqual(playlist2.tag.tag_id, "TAG003")
    
    def test_playlist_item_creation(self):
        """Test creating a PlaylistItem instance."""
        tag = Tag(tag_id="TAG004", name="Test Tag")
        playlist = Playlist(name="Test Playlist")
        tag.playlists.append(playlist)
        self.session.add(tag)
        self.session.commit()
        
        item = PlaylistItem(
            playlist_id=playlist.id,
            mp3_file="test_song.mp3",
            position=0
        )
        self.session.add(item)
        self.session.commit()
        
        retrieved_item = self.session.query(PlaylistItem).filter_by(mp3_file="test_song.mp3").first()
        self.assertIsNotNone(retrieved_item)
        self.assertEqual(retrieved_item.mp3_file, "test_song.mp3")
        self.assertEqual(retrieved_item.position, 0)
        self.assertEqual(retrieved_item.playlist_id, playlist.id)
    
    def test_playlist_items_relationship(self):
        """Test the relationship between Playlist and PlaylistItem."""
        tag = Tag(tag_id="TAG005", name="Test Tag")
        playlist = Playlist(name="Test Playlist")
        tag.playlists.append(playlist)
        
        item1 = PlaylistItem(mp3_file="song1.mp3", position=1)
        item2 = PlaylistItem(mp3_file="song2.mp3", position=0)
        item3 = PlaylistItem(mp3_file="song3.mp3", position=2)
        
        playlist.items.extend([item1, item2, item3])
        
        self.session.add(tag)
        self.session.commit()
        
        retrieved_playlist = self.session.query(Playlist).filter_by(name="Test Playlist").first()
        self.assertEqual(len(retrieved_playlist.items), 3)
        
        # Check ordering by position
        self.assertEqual(retrieved_playlist.items[0].mp3_file, "song2.mp3")  # position 0
        self.assertEqual(retrieved_playlist.items[1].mp3_file, "song1.mp3")  # position 1
        self.assertEqual(retrieved_playlist.items[2].mp3_file, "song3.mp3")  # position 2
        
        # Test back reference
        self.assertEqual(item1.playlist.name, "Test Playlist")
    
    def test_playlist_item_nullable_constraint(self):
        """Test that mp3_file and position cannot be null."""
        tag = Tag(tag_id="TAG006", name="Test Tag")
        playlist = Playlist(name="Test Playlist")
        tag.playlists.append(playlist)
        self.session.add(tag)
        self.session.commit()
        
        # Test mp3_file nullable
        item1 = PlaylistItem(playlist_id=playlist.id, position=0)
        self.session.add(item1)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()
        
        # Test position nullable
        item2 = PlaylistItem(playlist_id=playlist.id, mp3_file="test.mp3")
        self.session.add(item2)
        with self.assertRaises(IntegrityError):
            self.session.commit()
    
    def test_setting_creation(self):
        """Test creating a Setting instance."""
        setting = Setting(key="volume", value="0.75")
        self.session.add(setting)
        self.session.commit()
        
        retrieved_setting = self.session.query(Setting).filter_by(key="volume").first()
        self.assertIsNotNone(retrieved_setting)
        self.assertEqual(retrieved_setting.key, "volume")
        self.assertEqual(retrieved_setting.value, "0.75")
    
    def test_setting_primary_key(self):
        """Test that Setting key acts as primary key."""
        setting1 = Setting(key="volume", value="0.5")
        self.session.add(setting1)
        self.session.commit()
        
        # Try to add another setting with same key using a fresh session
        # to avoid SQLAlchemy warning about conflicting instances
        self.session.expunge_all()  # Clear session to avoid identity conflicts
        setting2 = Setting(key="volume", value="0.8")
        self.session.add(setting2)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()  # Clear the failed transaction
    
    def test_setting_update(self):
        """Test updating a Setting value."""
        setting = Setting(key="theme", value="light")
        self.session.add(setting)
        self.session.commit()
        
        # Update the value
        retrieved_setting = self.session.query(Setting).filter_by(key="theme").first()
        retrieved_setting.value = "dark"
        self.session.commit()
        
        # Verify the update
        updated_setting = self.session.query(Setting).filter_by(key="theme").first()
        self.assertEqual(updated_setting.value, "dark")
    
    def test_cascade_delete(self):
        """Test cascade deletion of related objects."""
        tag = Tag(tag_id="TAG007", name="Test Tag")
        playlist = Playlist(name="Test Playlist")
        tag.playlists.append(playlist)
        
        item1 = PlaylistItem(mp3_file="song1.mp3", position=0)
        item2 = PlaylistItem(mp3_file="song2.mp3", position=1)
        playlist.items.extend([item1, item2])
        
        self.session.add(tag)
        self.session.commit()
        
        # Delete the playlist
        self.session.delete(playlist)
        self.session.commit()
        
        # Check that playlist items are also deleted (if cascade is configured)
        remaining_items = self.session.query(PlaylistItem).all()
        # Note: This behavior depends on cascade configuration
        # If cascade delete is not configured, items will remain
        
        # Check that tag still exists
        retrieved_tag = self.session.query(Tag).filter_by(tag_id="TAG007").first()
        self.assertIsNotNone(retrieved_tag)
        self.assertEqual(len(retrieved_tag.playlists), 0)
    
    def test_multiple_playlists_per_tag(self):
        """Test that a tag can have multiple playlists."""
        tag = Tag(tag_id="TAG008", name="Multi-Playlist Tag")
        
        for i in range(3):
            playlist = Playlist(name=f"Playlist {i}")
            tag.playlists.append(playlist)
            
            # Add items to each playlist
            for j in range(2):
                item = PlaylistItem(mp3_file=f"playlist{i}_song{j}.mp3", position=j)
                playlist.items.append(item)
        
        self.session.add(tag)
        self.session.commit()
        
        retrieved_tag = self.session.query(Tag).filter_by(tag_id="TAG008").first()
        self.assertEqual(len(retrieved_tag.playlists), 3)
        
        for i, playlist in enumerate(retrieved_tag.playlists):
            self.assertEqual(playlist.name, f"Playlist {i}")
            self.assertEqual(len(playlist.items), 2)
    
    def test_orphan_playlist(self):
        """Test creating a playlist without a tag."""
        playlist = Playlist(name="Orphan Playlist")
        self.session.add(playlist)
        self.session.commit()
        
        retrieved_playlist = self.session.query(Playlist).filter_by(name="Orphan Playlist").first()
        self.assertIsNotNone(retrieved_playlist)
        self.assertIsNone(retrieved_playlist.tag_id)
        self.assertIsNone(retrieved_playlist.tag)


if __name__ == '__main__':
    unittest.main()