"""Tag management operations for BertiBox database."""

from .models import Tag, Playlist


class TagManager:
    def __init__(self, get_session):
        self.get_session = get_session
    
    def add_tag(self, tag_id, name=None):
        session = self.get_session()
        try:
            tag = Tag(tag_id=tag_id, name=name)
            session.add(tag)
            session.commit()
            session.refresh(tag)
            session.expunge(tag)
            return tag
        finally:
            session.close()
    
    def get_tag(self, tag_id):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if tag:
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
    
    def update_tag(self, tag_id, name):
        session = self.get_session()
        try:
            tag = session.query(Tag).filter_by(tag_id=tag_id).first()
            if tag:
                tag.name = name
                session.commit()
                session.refresh(tag)
                session.expunge(tag)
                return tag
            return None
        finally:
            session.close()
    
    def get_all_tags(self):
        session = self.get_session()
        try:
            tags = session.query(Tag).all()
            tag_list = []
            for tag in tags:
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