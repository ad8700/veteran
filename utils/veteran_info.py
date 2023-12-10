from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button

class VeteranInfoPopup(Popup):
    def __init__(self, grave_id, **kwargs):
        super(VeteranInfoPopup, self).__init__(**kwargs)
        self.grave_id = grave_id

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
        # Validate user input
        veteran_name = self.veteran_name_input.text
        branch_of_service = self.branch_input.text
        birth_year = self.birth_year_input.text or None
        death_year = self.death_year_input.text

    # Update the database
    def submit_info(self, instance):
    # ... Validate user input ...

    # Update the database
    conn.execute("""
        UPDATE Grave_Locations
        SET veteran_name=?, branch_of_service=?, birth_year=?, death_year=?
        WHERE id=?
    """, (veteran_name, branch_of_service, birth_year, death_year, self.grave_id))
    conn.commit()

    # Close the popup
    self.dismiss()
        
# When a new point is added, display the popup
def add_point(latitude, longitude, shapefile_id, accuracy=None):
    # ... Add logic to insert new point into Grave_Locations table
    # ...

    # Get the ID of the newly created record
    grave_id = conn.lastrowid

    # Show the popup for adding veteran information
    popup = VeteranInfoPopup(grave_id)
    popup.open()