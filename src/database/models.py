"""Database models for BertiBox application."""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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