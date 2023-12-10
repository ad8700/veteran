import sqlite3

conn = sqlite3.connect('VeteranGraveMarker.db')

CREATE TABLE shapes (
    id INTEGER PRIMARY KEY,
    name TEXT,
    shapefile_path TEXT
);