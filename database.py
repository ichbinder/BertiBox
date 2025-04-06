from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Sequence, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import os
import threading

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
    
    def add_playlist_item(self, playlist_id, mp3_file, position):
        session = self.get_session()
        try:
            playlist = session.query(Playlist).filter_by(id=playlist_id).first()
            if not playlist:
                return None
            
            # Hole die höchste ID und erhöhe sie um 1
            max_id = session.query(func.max(PlaylistItem.id)).scalar() or 0
            new_id = max_id + 1
            
            item = PlaylistItem(id=new_id, playlist_id=playlist_id, mp3_file=mp3_file, position=position)
            session.add(item)
            session.commit()
            return item
        finally:
            session.close()
    
    def get_playlist_items(self, playlist_id):
        session = self.get_session()
        try:
            items = session.query(PlaylistItem).filter_by(playlist_id=playlist_id).order_by(PlaylistItem.position).all()
            return [{
                'id': item.id,
                'playlist_id': item.playlist_id,
                'mp3_file': item.mp3_file,
                'position': item.position
            } for item in items]
        finally:
            session.close()
    
    def delete_playlist_item(self, item_id):
        session = self.get_session()
        try:
            item = session.query(PlaylistItem).filter_by(id=item_id).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def update_playlist_item_position(self, item_id, new_position):
        session = self.get_session()
        try:
            item = session.query(PlaylistItem).filter_by(id=item_id).first()
            if item:
                item.position = new_position
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
        session = self.get_session()
        try:
            playlist = session.query(Playlist).filter_by(id=playlist_id).first()
            if not playlist:
                return None
            
            # Hole die höchste ID
            max_id = session.query(func.max(PlaylistItem.id)).scalar() or 0
            current_position = session.query(func.max(PlaylistItem.position)).filter_by(playlist_id=playlist_id).scalar() or 0
            
            items = []
            for mp3_file in mp3_files:
                max_id += 1
                current_position += 1
                item = PlaylistItem(
                    id=max_id,
                    playlist_id=playlist_id,
                    mp3_file=mp3_file,
                    position=current_position
                )
                session.add(item)
                items.append({
                    'id': item.id,
                    'playlist_id': item.playlist_id,
                    'mp3_file': item.mp3_file,
                    'position': item.position
                })
            
            session.commit()
            return items
        finally:
            session.close() 