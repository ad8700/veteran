from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivy.metrics import dp
from kivy.clock import Clock
import os

class VeteranInfoPopup(Popup):
    def __init__(self, grave_id, db_path, latitude, longitude, **kwargs):
        super(VeteranInfoPopup, self).__init__(**kwargs)
        self.grave_id = grave_id
        self.db_path = db_path
        self.latitude = latitude
        self.longitude = longitude
        self.photo_path = None

        # Set popup properties
        self.title = "Record Veteran Grave"
        self.size_hint = (0.95, 0.95)

        # Create scrollable content for smaller screens
        scroll_view = ScrollView(do_scroll_x=False)

        # Initialize layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Location info label
        location_label = Label(
            text=f"Location: {latitude:.6f}, {longitude:.6f}",
            size_hint_y=None,
            height=30,
            font_size='12sp'
        )
        layout.add_widget(location_label)

        # Photo section
        photo_section = BoxLayout(orientation='vertical', size_hint_y=None, height=180, spacing=5)

        # Photo thumbnail (placeholder initially)
        self.photo_image = Image(
            source='',
            size_hint_y=None,
            height=120,
            allow_stretch=True,
            keep_ratio=True
        )
        self.photo_label = Label(
            text="No photo taken",
            size_hint_y=None,
            height=120,
            color=(0.5, 0.5, 0.5, 1)
        )
        photo_section.add_widget(self.photo_label)

        # Photo buttons
        photo_buttons = BoxLayout(size_hint_y=None, height=44, spacing=10)
        self.take_photo_button = Button(text="Take Photo")
        self.take_photo_button.bind(on_press=self.take_photo)
        photo_buttons.add_widget(self.take_photo_button)

        self.retake_photo_button = Button(text="Retake", disabled=True)
        self.retake_photo_button.bind(on_press=self.take_photo)
        photo_buttons.add_widget(self.retake_photo_button)
        photo_section.add_widget(photo_buttons)

        layout.add_widget(photo_section)

        # Veteran Name Input
        self.veteran_name_input = TextInput(
            hint_text="Veteran Name (Required)",
            multiline=False,
            size_hint_y=None,
            height=44
        )
        layout.add_widget(self.veteran_name_input)

        # Branch of Service Dropdown Button
        self.branch_button = Button(
            text="Select Branch of Service",
            size_hint_y=None,
            height=dp(56)
        )
        self.branch_button.bind(on_release=self.show_branch_dropdown)
        layout.add_widget(self.branch_button)

        # Create branch dropdown with larger touch targets
        branch_options = ["Army", "Navy", "Air Force", "Marine Corps", "Coast Guard", "Space Force"]
        self.branch_dropdown = DropDown()
        for branch in branch_options:
            btn = Button(text=branch, size_hint_y=None, height=dp(56))
            btn.bind(on_release=lambda btn: self.select_branch(btn.text))
            self.branch_dropdown.add_widget(btn)

        self.selected_branch = None

        # Cemetery Selection Dropdown Button
        self.cemetery_button = Button(
            text="Select Cemetery (Optional)",
            size_hint_y=None,
            height=dp(56)
        )
        self.cemetery_button.bind(on_release=self.show_cemetery_dropdown)
        layout.add_widget(self.cemetery_button)

        # Create cemetery dropdown with common options
        cemetery_options = [
            "Arlington National Cemetery",
            "Jefferson Barracks National Cemetery",
            "Calverton National Cemetery",
            "Houston National Cemetery",
            "Fort Snelling National Cemetery",
            "Other / Unknown"
        ]
        self.cemetery_dropdown = DropDown()
        for cemetery in cemetery_options:
            btn = Button(text=cemetery, size_hint_y=None, height=dp(56))
            btn.bind(on_release=lambda btn: self.select_cemetery(btn.text))
            self.cemetery_dropdown.add_widget(btn)

        self.selected_cemetery = None

        # Birth Year Input
        self.birth_year_input = TextInput(
            hint_text="Birth Year (Optional)",
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=44
        )
        layout.add_widget(self.birth_year_input)

        # Death Year Input
        self.death_year_input = TextInput(
            hint_text="Death Year (Required)",
            multiline=False,
            input_filter='int',
            size_hint_y=None,
            height=44
        )
        layout.add_widget(self.death_year_input)

        # Notes field (multi-line)
        notes_label = Label(
            text="Notes (Optional):",
            size_hint_y=None,
            height=25,
            halign='left',
            text_size=(None, None)
        )
        notes_label.bind(size=notes_label.setter('text_size'))
        layout.add_widget(notes_label)

        self.notes_input = TextInput(
            hint_text="Additional notes about the grave site...",
            multiline=True,
            size_hint_y=None,
            height=100
        )
        layout.add_widget(self.notes_input)

        # Error message label (hidden by default)
        self.error_label = Label(
            text="",
            color=(1, 0, 0, 1),
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.error_label)

        # Buttons layout
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)

        # Cancel Button
        cancel_button = Button(text="Cancel")
        cancel_button.bind(on_press=self.dismiss)
        button_layout.add_widget(cancel_button)

        # Submit Button
        submit_button = Button(text="Save")
        submit_button.bind(on_press=self.submit_info)
        button_layout.add_widget(submit_button)

        layout.add_widget(button_layout)

        # Add layout to scroll view
        scroll_view.add_widget(layout)

        # Add scroll view to the popup
        self.content = scroll_view

    def show_branch_dropdown(self, instance):
        """Show the branch dropdown menu"""
        self.branch_dropdown.open(instance)

    def select_branch(self, branch_name):
        """Handle branch selection"""
        self.selected_branch = branch_name
        self.branch_button.text = branch_name
        self.branch_dropdown.dismiss()
        print(f"Selected branch: {branch_name}")

    def show_cemetery_dropdown(self, instance):
        """Show the cemetery dropdown menu"""
        self.cemetery_dropdown.open(instance)

    def select_cemetery(self, cemetery_name):
        """Handle cemetery selection"""
        self.selected_cemetery = cemetery_name
        self.cemetery_button.text = cemetery_name
        self.cemetery_dropdown.dismiss()
        print(f"Selected cemetery: {cemetery_name}")

    def take_photo(self, instance):
        """Open camera to take a photo of the headstone"""
        if platform == 'android':
            from android.permissions import request_permissions, Permission, check_permission

            # Check/request camera permission
            if not check_permission(Permission.CAMERA):
                # Request permission and schedule retry
                def on_permission_result(permissions, grants):
                    if grants and grants[0]:
                        Clock.schedule_once(lambda dt: self._capture_photo(), 0.5)
                    else:
                        self.error_label.text = "Camera permission denied"

                request_permissions([Permission.CAMERA], on_permission_result)
                return

            self._capture_photo()
        else:
            # For testing on desktop, simulate photo capture
            print("Camera not available on this platform (desktop testing)")
            self.error_label.text = "Camera only available on Android"

    def _capture_photo(self):
        """Actually capture the photo using plyer"""
        try:
            from plyer import camera
            from kivy.app import App

            # Get app's data directory for storing photos
            app = App.get_running_app()
            photos_dir = os.path.join(app.user_data_dir, 'photos')

            # Create photos directory if it doesn't exist
            if not os.path.exists(photos_dir):
                os.makedirs(photos_dir)

            # Generate unique filename
            filename = f"grave_{self.grave_id}.jpg"
            self.photo_path = os.path.join(photos_dir, filename)

            # Take photo
            camera.take_picture(
                filename=self.photo_path,
                on_complete=self._on_photo_complete
            )

        except Exception as e:
            print(f"Error taking photo: {e}")
            self.error_label.text = f"Camera error: {str(e)}"

    def _on_photo_complete(self, filepath):
        """Called when photo capture completes"""
        from kivy.clock import Clock

        def update_ui(dt):
            if filepath and os.path.exists(filepath):
                self.photo_path = filepath
                # Remove the "No photo" label and show the image
                photo_section = self.photo_label.parent
                photo_section.remove_widget(self.photo_label)

                self.photo_image.source = filepath
                photo_section.add_widget(self.photo_image, index=1)

                # Enable retake button
                self.retake_photo_button.disabled = False
                self.take_photo_button.text = "Photo Captured"

                print(f"Photo saved to: {filepath}")
            else:
                self.error_label.text = "Photo capture failed"
                print("Photo capture failed or was cancelled")

        Clock.schedule_once(update_ui, 0)

    def submit_info(self, instance):
        """Update the database with veteran information"""
        import sqlite3

        # Clear previous error
        self.error_label.text = ""

        # Validate user input
        veteran_name = self.veteran_name_input.text.strip()
        branch_of_service = self.selected_branch
        cemetery_name = self.selected_cemetery
        birth_year = self.birth_year_input.text.strip()
        death_year = self.death_year_input.text.strip()
        notes = self.notes_input.text.strip()

        # Validation
        if not veteran_name:
            self.error_label.text = "Veteran name is required"
            return

        if not death_year:
            self.error_label.text = "Death year is required"
            return

        # Validate death year is a valid 4-digit year
        if len(death_year) != 4 or not death_year.isdigit():
            self.error_label.text = "Death year must be a 4-digit year"
            return

        # Validate birth year if provided
        if birth_year and (len(birth_year) != 4 or not birth_year.isdigit()):
            self.error_label.text = "Birth year must be a 4-digit year"
            return

        # Convert years to integers
        death_year_int = int(death_year)
        birth_year_int = int(birth_year) if birth_year else None

        # Check birth year < death year if both provided
        if birth_year_int and birth_year_int >= death_year_int:
            self.error_label.text = "Birth year must be before death year"
            return

        try:
            # Update the database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Grave_Locations
                SET veteran_name=?, branch_of_service=?, birth_year=?, death_year=?,
                    cemetary_name=?, notes=?, photo_path=?
                WHERE id=?
            """, (veteran_name, branch_of_service, birth_year_int, death_year_int,
                  cemetery_name, notes if notes else None, self.photo_path, self.grave_id))
            conn.commit()
            conn.close()

            print(f"Saved grave record: {veteran_name}, {branch_of_service}, {birth_year_int}-{death_year_int}")
            if cemetery_name:
                print(f"  Cemetery: {cemetery_name}")
            if notes:
                print(f"  Notes: {notes[:50]}...")
            if self.photo_path:
                print(f"  Photo: {self.photo_path}")

            # Close this popup
            self.dismiss()

            # Show confirmation popup
            confirm_popup = Popup(
                title='Record Saved',
                content=Label(
                    text=f'Saved: {veteran_name}\n\nRecord saved to local database.\nTap "Sync" to upload to cloud.',
                    halign='center'
                ),
                size_hint=(0.85, 0.35),
                auto_dismiss=True
            )
            confirm_popup.open()

        except Exception as e:
            self.error_label.text = f"Database error: {str(e)}"
            print(f"Error saving to database: {e}")
            import traceback
            traceback.print_exc()
