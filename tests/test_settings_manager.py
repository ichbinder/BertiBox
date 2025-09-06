"""Tests for SettingsManager class."""

import unittest
from unittest.mock import MagicMock, Mock, patch
from src.database.settings_manager import SettingsManager
from src.database.models import Setting


class TestSettingsManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.get_session = Mock(return_value=self.mock_session)
        self.settings_manager = SettingsManager(self.get_session)
    
    def test_get_setting_exists(self):
        """Test getting an existing setting."""
        mock_setting = MagicMock(spec=Setting)
        mock_setting.value = "test_value"
        
        self.mock_session.query().filter_by().first.return_value = mock_setting
        
        result = self.settings_manager.get_setting("test_key")
        
        self.assertEqual(result, "test_value")
        self.mock_session.close.assert_called_once()
    
    def test_get_setting_not_exists_default(self):
        """Test getting a non-existent setting returns default."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.settings_manager.get_setting("test_key", default_value="default")
        
        self.assertEqual(result, "default")
        self.mock_session.close.assert_called_once()
    
    def test_get_setting_not_exists_no_default(self):
        """Test getting a non-existent setting without default."""
        self.mock_session.query().filter_by().first.return_value = None
        
        result = self.settings_manager.get_setting("test_key")
        
        self.assertIsNone(result)
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_new(self):
        """Test setting a new setting value."""
        self.mock_session.query().filter_by().first.return_value = None
        
        with patch('src.database.settings_manager.Setting') as MockSetting:
            mock_new_setting = MagicMock()
            MockSetting.return_value = mock_new_setting
            
            result = self.settings_manager.set_setting("new_key", "new_value")
        
        self.assertTrue(result)
        MockSetting.assert_called_once_with(key="new_key", value="new_value")
        self.mock_session.add.assert_called_once_with(mock_new_setting)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_update_existing(self):
        """Test updating an existing setting."""
        mock_setting = MagicMock(spec=Setting)
        mock_setting.value = "old_value"
        
        self.mock_session.query().filter_by().first.return_value = mock_setting
        
        result = self.settings_manager.set_setting("test_key", "new_value")
        
        self.assertTrue(result)
        self.assertEqual(mock_setting.value, "new_value")
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_if_not_exists_existing(self):
        """Test set_if_not_exists doesn't overwrite existing setting."""
        mock_setting = MagicMock(spec=Setting)
        mock_setting.value = "existing_value"
        
        self.mock_session.query().filter_by().first.return_value = mock_setting
        
        result = self.settings_manager.set_setting("test_key", "new_value", set_if_not_exists=True)
        
        self.assertTrue(result)
        self.assertEqual(mock_setting.value, "existing_value")  # Should not change
        self.mock_session.commit.assert_not_called()
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_if_not_exists_new(self):
        """Test set_if_not_exists creates new setting if not exists."""
        self.mock_session.query().filter_by().first.return_value = None
        
        with patch('src.database.settings_manager.Setting') as MockSetting:
            mock_new_setting = MagicMock()
            MockSetting.return_value = mock_new_setting
            
            result = self.settings_manager.set_setting("new_key", "new_value", set_if_not_exists=True)
        
        self.assertTrue(result)
        MockSetting.assert_called_once_with(key="new_key", value="new_value")
        self.mock_session.add.assert_called_once_with(mock_new_setting)
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_converts_to_string(self):
        """Test that setting values are converted to strings."""
        self.mock_session.query().filter_by().first.return_value = None
        
        with patch('src.database.settings_manager.Setting') as MockSetting:
            mock_new_setting = MagicMock()
            MockSetting.return_value = mock_new_setting
            
            result = self.settings_manager.set_setting("number_key", 42)
        
        self.assertTrue(result)
        MockSetting.assert_called_once_with(key="number_key", value="42")
        self.mock_session.close.assert_called_once()
    
    def test_set_setting_exception(self):
        """Test set_setting handles exceptions."""
        self.mock_session.query().filter_by().first.side_effect = Exception("DB Error")
        
        result = self.settings_manager.set_setting("test_key", "test_value")
        
        self.assertFalse(result)
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()