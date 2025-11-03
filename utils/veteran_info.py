from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.label import Label

class VeteranInfoPopup(Popup):
    def __init__(self, grave_id, db_path, latitude, longitude, **kwargs):
        super(VeteranInfoPopup, self).__init__(**kwargs)
        self.grave_id = grave_id
        self.db_path = db_path
        self.latitude = latitude
        self.longitude = longitude

        # Set popup properties
        self.title = "Record Veteran Grave"
        self.size_hint = (0.9, 0.8)

        # Initialize layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Location info label
        location_label = Label(
            text=f"Location: {latitude:.6f}, {longitude:.6f}",
            size_hint_y=0.1,
            font_size='12sp'
        )
        layout.add_widget(location_label)

        # Veteran Name Input
        self.veteran_name_input = TextInput(
            hint_text="Veteran Name (Required)",
            multiline=False,
            size_hint_y=0.15
        )
        layout.add_widget(self.veteran_name_input)

        # Branch of Service Dropdown Button
        self.branch_button = Button(
            text="Select Branch of Service",
            size_hint_y=0.15
        )
        self.branch_button.bind(on_release=self.show_branch_dropdown)
        layout.add_widget(self.branch_button)

        # Create dropdown
        branch_options = ["Army", "Navy", "Air Force", "Marine Corps", "Coast Guard"]
        self.branch_dropdown = DropDown()
        for branch in branch_options:
            btn = Button(text=branch, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.select_branch(btn.text))
            self.branch_dropdown.add_widget(btn)

        self.selected_branch = None

        # Birth Year Input
        self.birth_year_input = TextInput(
            hint_text="Birth Year (Optional)",
            multiline=False,
            input_filter='int',
            size_hint_y=0.15
        )
        layout.add_widget(self.birth_year_input)

        # Death Year Input
        self.death_year_input = TextInput(
            hint_text="Death Year (Required)",
            multiline=False,
            input_filter='int',
            size_hint_y=0.15
        )
        layout.add_widget(self.death_year_input)

        # Error message label (hidden by default)
        self.error_label = Label(
            text="",
            color=(1, 0, 0, 1),
            size_hint_y=0.1
        )
        layout.add_widget(self.error_label)

        # Buttons layout
        button_layout = BoxLayout(size_hint_y=0.15, spacing=10)

        # Cancel Button
        cancel_button = Button(text="Cancel")
        cancel_button.bind(on_press=self.dismiss)
        button_layout.add_widget(cancel_button)

        # Submit Button
        submit_button = Button(text="Save")
        submit_button.bind(on_press=self.submit_info)
        button_layout.add_widget(submit_button)

        layout.add_widget(button_layout)

        # Add layout to the popup
        self.content = layout

    def show_branch_dropdown(self, instance):
        """Show the branch dropdown menu"""
        self.branch_dropdown.open(instance)

    def select_branch(self, branch_name):
        """Handle branch selection"""
        self.selected_branch = branch_name
        self.branch_button.text = branch_name
        self.branch_dropdown.dismiss()
        print(f"Selected branch: {branch_name}")

    def submit_info(self, instance):
        """Update the database with veteran information"""
        import sqlite3

        # Clear previous error
        self.error_label.text = ""

        # Validate user input
        veteran_name = self.veteran_name_input.text.strip()
        branch_of_service = self.selected_branch
        birth_year = self.birth_year_input.text.strip()
        death_year = self.death_year_input.text.strip()

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
                SET veteran_name=?, branch_of_service=?, birth_year=?, death_year=?
                WHERE id=?
            """, (veteran_name, branch_of_service, birth_year_int, death_year_int, self.grave_id))
            conn.commit()
            conn.close()

            print(f"Saved grave record: {veteran_name}, {branch_of_service}, {birth_year_int}-{death_year_int}")

            # Close the popup
            self.dismiss()

        except Exception as e:
            self.error_label.text = f"Database error: {str(e)}"
            print(f"Error saving to database: {e}")
            import traceback
            traceback.print_exc()