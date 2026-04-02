"""
SyncManager - Handles offline-first data synchronization with AWS backend
"""
import json
import os
import sqlite3
from datetime import datetime
from kivy.network.urlrequest import UrlRequest
from kivy.app import App
from kivy.clock import Clock

from utils.config import API_ENDPOINT
from utils.AuthManager import get_auth_manager


class SyncManager:
    """
    Manages synchronization between local SQLite database and AWS backend.

    Features:
    - Offline-first: All data saved locally first
    - Background sync when online
    - Conflict resolution (server wins)
    - Photo upload via pre-signed URLs
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.sync_in_progress = False
        self.last_sync = None
        self._load_sync_state()

    def _load_sync_state(self):
        """Load last sync timestamp from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create sync metadata table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Add sync columns to Grave_Locations if they don't exist
            cursor.execute("PRAGMA table_info(Grave_Locations)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'cloud_id' not in columns:
                cursor.execute("ALTER TABLE Grave_Locations ADD COLUMN cloud_id TEXT")
            if 'sync_status' not in columns:
                cursor.execute("ALTER TABLE Grave_Locations ADD COLUMN sync_status TEXT DEFAULT 'pending'")
            if 'last_synced' not in columns:
                cursor.execute("ALTER TABLE Grave_Locations ADD COLUMN last_synced TEXT")

            # Get last sync time
            cursor.execute("SELECT value FROM sync_metadata WHERE key = 'last_sync'")
            row = cursor.fetchone()
            if row:
                self.last_sync = row[0]

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error loading sync state: {e}")

    def _save_sync_state(self):
        """Save last sync timestamp to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sync_metadata (key, value)
                VALUES ('last_sync', ?)
            """, (self.last_sync,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving sync state: {e}")

    def get_pending_records(self):
        """Get all records that need to be synced"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM Grave_Locations
                WHERE sync_status = 'pending' OR sync_status IS NULL
            """)

            records = []
            for row in cursor.fetchall():
                record = dict(row)
                record['local_id'] = str(record['id'])
                records.append(record)

            conn.close()
            return records
        except Exception as e:
            print(f"Error getting pending records: {e}")
            return []

    def sync(self, on_complete=None, on_error=None):
        """
        Synchronize local database with AWS backend.

        Args:
            on_complete: Callback function called on success with sync results
            on_error: Callback function called on error with error message
        """
        if self.sync_in_progress:
            print("Sync already in progress")
            return

        # Check if user is authenticated
        auth_manager = get_auth_manager()
        if auth_manager.is_guest:
            if on_error:
                Clock.schedule_once(
                    lambda dt: on_error("Sign in to sync data.\nGuest data is stored locally only."), 0
                )
            return

        self.sync_in_progress = True
        pending_records = self.get_pending_records()

        # Prepare sync payload
        payload = {
            'last_sync': self.last_sync,
            'records': []
        }

        for record in pending_records:
            sync_record = {
                'local_id': record['local_id'],
                'latitude': record['latitude'],
                'longitude': record['longitude'],
                'veteran_name': record.get('veteran_name'),
                'branch_of_service': record.get('branch_of_service'),
                'birth_year': record.get('birth_year'),
                'death_year': record.get('death_year'),
                'cemetery_name': record.get('cemetary_name'),
                'notes': record.get('notes'),
                'accuracy': record.get('accuracy')
            }
            payload['records'].append(sync_record)

        def handle_success(req, result):
            self.sync_in_progress = False
            try:
                # Update local records with cloud IDs
                if 'id_mapping' in result:
                    self._update_cloud_ids(result['id_mapping'])

                # Update sync timestamp
                if 'sync_timestamp' in result:
                    self.last_sync = result['sync_timestamp']
                    self._save_sync_state()

                # Process downloaded records
                if 'downloaded' in result:
                    self._process_downloaded(result['downloaded'])

                print(f"Sync complete: {result.get('uploaded', 0)} uploaded, {len(result.get('downloaded', []))} downloaded")

                if on_complete:
                    Clock.schedule_once(lambda dt: on_complete(result), 0)

            except Exception as e:
                print(f"Error processing sync response: {e}")
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(str(e)), 0)

        def handle_error(req, error):
            self.sync_in_progress = False
            print(f"Sync error: {error}")
            if on_error:
                Clock.schedule_once(lambda dt: on_error(str(error)), 0)

        def handle_failure(req, result):
            self.sync_in_progress = False
            print(f"Sync failed: {result}")
            if on_error:
                Clock.schedule_once(lambda dt: on_error(str(result)), 0)

        # Build headers with auth token
        headers = {'Content-Type': 'application/json'}
        auth_manager = get_auth_manager()
        if auth_manager.is_authenticated() and auth_manager.access_token:
            headers['Authorization'] = f'Bearer {auth_manager.access_token}'
        elif auth_manager.id_token:
            headers['Authorization'] = f'Bearer {auth_manager.id_token}'

        # Make sync request
        UrlRequest(
            f"{API_ENDPOINT}/sync",
            req_body=json.dumps(payload),
            req_headers=headers,
            on_success=handle_success,
            on_error=handle_error,
            on_failure=handle_failure,
            method='POST'
        )

    def _update_cloud_ids(self, id_mapping):
        """Update local records with their cloud IDs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for local_id, cloud_id in id_mapping.items():
                cursor.execute("""
                    UPDATE Grave_Locations
                    SET cloud_id = ?, sync_status = 'synced', last_synced = ?
                    WHERE id = ?
                """, (cloud_id, datetime.utcnow().isoformat(), int(local_id)))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating cloud IDs: {e}")

    def _process_downloaded(self, records):
        """Process records downloaded from the server"""
        # For now, we don't merge server records back to local
        # This would be needed for multi-device sync
        pass

    def upload_photo(self, grave_id, photo_path, on_complete=None, on_error=None):
        """
        Upload a photo for a grave record using pre-signed URL.

        Args:
            grave_id: The cloud ID of the grave record
            photo_path: Local path to the photo file
            on_complete: Callback on success
            on_error: Callback on error
        """
        if not os.path.exists(photo_path):
            if on_error:
                on_error("Photo file not found")
            return

        def handle_url_success(req, result):
            upload_url = result.get('upload_url')
            if not upload_url:
                if on_error:
                    on_error("No upload URL received")
                return

            # Read photo file
            with open(photo_path, 'rb') as f:
                photo_data = f.read()

            def handle_upload_success(req, result):
                print(f"Photo uploaded successfully for grave {grave_id}")
                if on_complete:
                    Clock.schedule_once(lambda dt: on_complete(result), 0)

            def handle_upload_error(req, error):
                print(f"Photo upload error: {error}")
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(str(error)), 0)

            # Upload to S3
            UrlRequest(
                upload_url,
                req_body=photo_data,
                req_headers={'Content-Type': 'image/jpeg'},
                on_success=handle_upload_success,
                on_error=handle_upload_error,
                on_failure=handle_upload_error,
                method='PUT'
            )

        def handle_url_error(req, error):
            print(f"Error getting upload URL: {error}")
            if on_error:
                Clock.schedule_once(lambda dt: on_error(str(error)), 0)

        # Get pre-signed upload URL (with auth)
        photo_headers = {'Content-Type': 'application/json'}
        auth_manager = get_auth_manager()
        if auth_manager.is_authenticated() and auth_manager.access_token:
            photo_headers['Authorization'] = f'Bearer {auth_manager.access_token}'
        elif auth_manager.id_token:
            photo_headers['Authorization'] = f'Bearer {auth_manager.id_token}'

        UrlRequest(
            f"{API_ENDPOINT}/graves/{grave_id}/photo",
            req_headers=photo_headers,
            on_success=handle_url_success,
            on_error=handle_url_error,
            on_failure=handle_url_error,
            method='POST'
        )


# Convenience function to get sync manager instance
_sync_manager = None

def get_sync_manager():
    """Get or create the global SyncManager instance"""
    global _sync_manager
    if _sync_manager is None:
        app = App.get_running_app()
        if app:
            db_path = app.get_db_path()
            _sync_manager = SyncManager(db_path)
    return _sync_manager
