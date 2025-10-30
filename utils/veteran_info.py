from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button

class VeteranInfoPopup(Popup):
    def __init__(self, grave_id, db_path, **kwargs):
        super(VeteranInfoPopup, self).__init__(**kwargs)
        self.grave_id = grave_id
        self.db_path = db_path

        # Initialize layout
        layout = BoxLayout(orientation='vertical')

        # Veteran Name Input
        self.veteran_name_input = TextInput(hint_text="Veteran Name")
        layout.add_widget(self.veteran_name_input)

        # Branch of Service Dropdown
        branch_options = ["Army", "Navy", "Air Force", "Marine Corps", "Coast Guard"]
        self.branch_dropdown = DropDown()
        for branch in branch_options:
            btn = Button(text=branch, size_hint_y=None, height=30)
            btn.bind(on_release=lambda btn: self.branch_dropdown.select(btn.text))
            self.branch_dropdown.add_widget(btn)
        self.branch_input = TextInput(hint_text="Branch of Service", readonly=True)
        self.branch_input.bind(on_touch_down=self.branch_dropdown.open)
        layout.add_widget(self.branch_input)

        # Birth Year Input
        self.birth_year_input = TextInput(hint_text="Birth Year (Optional)")
        layout.add_widget(self.birth_year_input)

        # Death Year Input
        self.death_year_input = TextInput(hint_text="Death Year")
        layout.add_widget(self.death_year_input)

        # Submit Button
        submit_button = Button(text="Submit", on_press=self.submit_info)
        layout.add_widget(submit_button)

        # Add layout to the popup
        self.add_widget(layout)

    def submit_info(self, instance):
        """Update the database with veteran information"""
        import sqlite3

        # Validate user input
        veteran_name = self.veteran_name_input.text
        branch_of_service = self.branch_input.text
        birth_year = self.birth_year_input.text or None
        death_year = self.death_year_input.text

        # Basic validation
        if not veteran_name or not death_year:
            print("Error: Veteran name and death year are required")
            return

        # Update the database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Grave_Locations
            SET veteran_name=?, branch_of_service=?, birth_year=?, death_year=?
            WHERE id=?
        """, (veteran_name, branch_of_service, birth_year, death_year, self.grave_id))
        conn.commit()
        conn.close()

        # Close the popup
        self.dismiss()