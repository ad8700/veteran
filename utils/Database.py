import sqlite3

conn = sqlite3.connect('VeteranGraveMarker.db')

#Create the Cemetaries table to hold shapefiles
conn.execute("""CREATE TABLE IF NOT EXISTS Cemetaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    metadata TEXT
    )""")

#Create the grave locations table to hold the information about specific graves
conn.execute("""CREATE TABLE IF NOT EXISTS Grave_Locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    shapefile_id INTEGER,
    accuracy REAL,
    veteran_name STRING,
    branch_of_service STRING,
    birth_year SMALLINT,
    death_year SMALLINT,
    cemetary_name STRING,
    FOREIGN KEY (shapefile_id) REFERENCES Cemetaries(id)
)""")

# Function to add a new shapefile
def add_shapefile(name, path, metadata=None):
    conn.execute("INSERT INTO Cemetaries (name, path, metadata) VALUES (?, ?, ?)",
                 (name, path, metadata))
    conn.commit()

# Function to add a new point
def add_point(latitude, longitude, shapefile_id, accuracy=None):
    conn.execute("INSERT INTO Grave_Locations (latitude, longitude, shapefile_id, accuracy) VALUES (?, ?, ?, ?)",
                 (latitude, longitude, shapefile_id, accuracy))
    conn.commit()

# Define the function to perform the lookup
def add_point_with_shape(latitude, longitude, shapefile_id, accuracy=None):
    # Connect to the database
    conn = sqlite3.connect("VeteranGraveMarker.db")

    # Prepare the SQL query
    sql = """
        INSERT INTO Grave_Locations (latitude, longitude, timestamp, shapefile_id, accuracy)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)

        RETURNING
            (
                SELECT
                    CASE WHEN ST_Contains(s.geom, POINT(?, ?)) THEN c.name
                         ELSE 'undefined'
                    END AS cemetary_name
                FROM Cemetaries c
                WHERE c.id = ?
            )
        """

    # Execute the query with latitude, longitude, shapefile_id, accuracy and return the shape_name
    shape_name, = conn.execute(sql, (latitude, longitude, shapefile_id, accuracy, latitude, longitude, shapefile_id)).fetchone()

    # Update the point with the shape_name
    conn.execute("UPDATE Grave_Locations SET cemetary_name = ? WHERE id = ?", (cemetary_name, conn.lastrowid))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Return the shape_name
    return shape_name