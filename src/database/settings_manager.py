"""Settings management operations for BertiBox database."""

from .models import Setting


class SettingsManager:
    def __init__(self, get_session):
        self.get_session = get_session
    
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
                    setting.value = str(value)
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