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
from kivy.graphics import Color, RoundedRectangle, Rectangle
import os

# ── Color Palette (shared with main) ──
COLORS = {
    'bg':          (0.11, 0.11, 0.16, 1),
    'surface':     (0.16, 0.17, 0.23, 1),
    'card':        (0.20, 0.21, 0.28, 1),
    'primary':     (0.20, 0.50, 0.90, 1),
    'accent':      (0.00, 0.59, 0.53, 1),
    'danger':      (0.90, 0.30, 0.25, 1),
    'text':        (0.93, 0.93, 0.96, 1),
    'text_dim':    (0.55, 0.57, 0.63, 1),
    'white':       (1, 1, 1, 1),
    'success':     (0.18, 0.72, 0.40, 1),
    'camera':      (0.95, 0.55, 0.10, 1),
    'input_bg':    (0.14, 0.14, 0.20, 1),
}


def _flat_btn(text, bg_key='primary', height=dp(48), font_size='15sp', **kw):
    return Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size=font_size,
        background_normal='',
        background_color=COLORS.get(bg_key, COLORS['primary']),
        color=COLORS['white'],
        bold=True,
        **kw,
    )


def _styled_input(hint, multiline=False, height=dp(46), **kw):
    return TextInput(
        hint_text=hint,
        multiline=multiline,
        size_hint_y=None,
        height=height,
        background_color=COLORS['input_bg'],
        foreground_color=COLORS['text'],
        hint_text_color=COLORS['text_dim'],
        cursor_color=COLORS['primary'],
        padding=[dp(12), dp(10)],
        font_size='15sp',
        **kw,
    )


def _section_label(text):
    lbl = Label(
        text=text,
        size_hint_y=None,
        height=dp(22),
        font_size='12sp',
        color=COLORS['text_dim'],
        halign='left',
        bold=True,
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class VeteranInfoPopup(Popup):
    def __init__(self, grave_id, db_path, latitude, longitude, **kwargs):
        super(VeteranInfoPopup, self).__init__(**kwargs)
        self.grave_id = grave_id
        self.db_path = db_path
        self.latitude = latitude
        self.longitude = longitude
        self.photo_path = None

        # Popup styling
        self.title = "Record Veteran Grave"
        self.title_size = '18sp'
        self.title_color = COLORS['text']
        self.size_hint = (0.95, 0.95)
        self.separator_color = COLORS['accent']
        self.background_color = COLORS['bg']

        # Scrollable content
        scroll_view = ScrollView(do_scroll_x=False)

        layout = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(12)],
            spacing=dp(10),
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter('height'))

        # ── Location ──
        coord_label = Label(
            text=f"{latitude:.6f}, {longitude:.6f}",
            size_hint_y=None,
            height=dp(28),
            font_size='13sp',
            color=COLORS['text_dim'],
        )
        layout.add_widget(coord_label)

        # ── Camera / Photo Section ──
        layout.add_widget(_section_label("HEADSTONE PHOTO"))

        photo_card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(200),
            spacing=dp(8),
            padding=[dp(10), dp(8)],
        )
        with photo_card.canvas.before:
            Color(*COLORS['card'])
            self._photo_bg = RoundedRectangle(
                size=photo_card.size, pos=photo_card.pos, radius=[dp(10)]
            )
        photo_card.bind(
            size=lambda w, v: setattr(self._photo_bg, 'size', v),
            pos=lambda w, v: setattr(self._photo_bg, 'pos', v),
        )

        # Photo thumbnail area
        self.photo_image = Image(
            source='',
            size_hint_y=None,
            height=dp(120),
            allow_stretch=True,
            keep_ratio=True,
        )
        self.photo_label = Label(
            text="Tap the camera button to photograph the headstone",
            size_hint_y=None,
            height=dp(120),
            color=COLORS['text_dim'],
            font_size='13sp',
        )
        photo_card.add_widget(self.photo_label)

        # Camera button row
        cam_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))

        self.take_photo_button = _flat_btn(
            "[ Camera ]  Take Photo", bg_key='camera', height=dp(48), font_size='16sp'
        )
        self.take_photo_button.bind(on_press=self.take_photo)
        cam_row.add_widget(self.take_photo_button)

        self.retake_photo_button = _flat_btn(
            "Retake", bg_key='card', height=dp(48), font_size='14sp'
        )
        self.retake_photo_button.disabled = True
        self.retake_photo_button.bind(on_press=self.take_photo)
        cam_row.add_widget(self.retake_photo_button)

        photo_card.add_widget(cam_row)
        layout.add_widget(photo_card)

        # ── Veteran Details ──
        layout.add_widget(_section_label("VETERAN DETAILS"))

        self.veteran_name_input = _styled_input("Veteran Name (Required)")
        layout.add_widget(self.veteran_name_input)

        # Branch dropdown
        self.branch_button = _flat_btn(
            "Select Branch of Service", bg_key='surface', height=dp(48), font_size='15sp'
        )
        self.branch_button.bind(on_release=self.show_branch_dropdown)
        layout.add_widget(self.branch_button)

        branch_options = [
            "Army", "Navy", "Air Force", "Marine Corps", "Coast Guard", "Space Force"
        ]
        self.branch_dropdown = DropDown()
        for branch in branch_options:
            btn = Button(
                text=branch,
                size_hint_y=None,
                height=dp(50),
                background_normal='',
                background_color=COLORS['surface'],
                color=COLORS['text'],
                font_size='15sp',
            )
            btn.bind(on_release=lambda b: self.select_branch(b.text))
            self.branch_dropdown.add_widget(btn)
        self.selected_branch = None

        # Cemetery dropdown
        self.cemetery_button = _flat_btn(
            "Select Cemetery (Optional)", bg_key='surface', height=dp(48), font_size='15sp'
        )
        self.cemetery_button.bind(on_release=self.show_cemetery_dropdown)
        layout.add_widget(self.cemetery_button)

        cemetery_options = [
            "Arlington National Cemetery",
            "Jefferson Barracks National Cemetery",
            "Calverton National Cemetery",
            "Houston National Cemetery",
            "Fort Snelling National Cemetery",
            "Other / Unknown",
        ]
        self.cemetery_dropdown = DropDown()
        for cem in cemetery_options:
            btn = Button(
                text=cem,
                size_hint_y=None,
                height=dp(50),
                background_normal='',
                background_color=COLORS['surface'],
                color=COLORS['text'],
                font_size='15sp',
            )
            btn.bind(on_release=lambda b: self.select_cemetery(b.text))
            self.cemetery_dropdown.add_widget(btn)
        self.selected_cemetery = None

        # Year inputs side by side
        year_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        self.birth_year_input = _styled_input("Birth Year", input_filter='int')
        self.death_year_input = _styled_input("Death Year *", input_filter='int')
        year_row.add_widget(self.birth_year_input)
        year_row.add_widget(self.death_year_input)
        layout.add_widget(year_row)

        # Notes
        layout.add_widget(_section_label("NOTES"))
        self.notes_input = _styled_input(
            "Additional notes about the grave site...",
            multiline=True,
            height=dp(90),
        )
        layout.add_widget(self.notes_input)

        # Error label
        self.error_label = Label(
            text="",
            color=COLORS['danger'],
            size_hint_y=None,
            height=dp(28),
            font_size='13sp',
        )
        layout.add_widget(self.error_label)

        # Action buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))

        cancel_btn = _flat_btn("Cancel", bg_key='surface', height=dp(50))
        cancel_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(cancel_btn)

        save_btn = _flat_btn("Save Record", bg_key='success', height=dp(50), font_size='16sp')
        save_btn.bind(on_press=self.submit_info)
        btn_row.add_widget(save_btn)

        layout.add_widget(btn_row)

        scroll_view.add_widget(layout)
        self.content = scroll_view

    # ── Dropdown handlers ──

    def show_branch_dropdown(self, instance):
        self.branch_dropdown.open(instance)

    def select_branch(self, branch_name):
        self.selected_branch = branch_name
        self.branch_button.text = branch_name
        self.branch_dropdown.dismiss()

    def show_cemetery_dropdown(self, instance):
        self.cemetery_dropdown.open(instance)

    def select_cemetery(self, cemetery_name):
        self.selected_cemetery = cemetery_name
        self.cemetery_button.text = cemetery_name
        self.cemetery_dropdown.dismiss()

    # ── Camera ──

    def take_photo(self, instance):
        """Open camera to photograph the headstone"""
        if platform == 'android':
            from android.permissions import request_permissions, Permission, check_permission

            if not check_permission(Permission.CAMERA):
                def on_permission_result(permissions, grants):
                    if grants and grants[0]:
                        Clock.schedule_once(lambda dt: self._capture_photo(), 0.3)
                    else:
                        self.error_label.text = "Camera permission denied"

                request_permissions([Permission.CAMERA], on_permission_result)
                return

            self._capture_photo()
        else:
            self.error_label.text = "Camera only available on Android"

    def _capture_photo(self):
        """Capture photo using plyer camera"""
        try:
            from plyer import camera
            from kivy.app import App

            app = App.get_running_app()
            photos_dir = os.path.join(app.user_data_dir, 'photos')
            if not os.path.exists(photos_dir):
                os.makedirs(photos_dir)

            filename = f"grave_{self.grave_id}.jpg"
            self.photo_path = os.path.join(photos_dir, filename)

            camera.take_picture(
                filename=self.photo_path,
                on_complete=self._on_photo_complete,
            )
        except Exception as e:
            print(f"Error taking photo: {e}")
            self.error_label.text = f"Camera error: {str(e)}"

    def _on_photo_complete(self, filepath):
        """Called when photo capture completes"""
        def update_ui(dt):
            if filepath and os.path.exists(filepath):
                self.photo_path = filepath

                # Swap placeholder label for actual image
                photo_section = self.photo_label.parent
                if self.photo_label.parent:
                    photo_section.remove_widget(self.photo_label)
                    self.photo_image.source = filepath
                    photo_section.add_widget(self.photo_image, index=1)

                self.retake_photo_button.disabled = False
                self.take_photo_button.text = "Photo Captured"
                self.take_photo_button.background_color = COLORS['success']
            else:
                self.error_label.text = "Photo capture cancelled"

        Clock.schedule_once(update_ui, 0)

    # ── Save ──

    def submit_info(self, instance):
        """Validate and save to database"""
        import sqlite3

        self.error_label.text = ""

        veteran_name = self.veteran_name_input.text.strip()
        branch_of_service = self.selected_branch
        cemetery_name = self.selected_cemetery
        birth_year = self.birth_year_input.text.strip()
        death_year = self.death_year_input.text.strip()
        notes = self.notes_input.text.strip()

        if not veteran_name:
            self.error_label.text = "Veteran name is required"
            return

        if not death_year:
            self.error_label.text = "Death year is required"
            return

        if len(death_year) != 4 or not death_year.isdigit():
            self.error_label.text = "Death year must be a 4-digit year"
            return

        if birth_year and (len(birth_year) != 4 or not birth_year.isdigit()):
            self.error_label.text = "Birth year must be a 4-digit year"
            return

        death_year_int = int(death_year)
        birth_year_int = int(birth_year) if birth_year else None

        if birth_year_int and birth_year_int >= death_year_int:
            self.error_label.text = "Birth year must be before death year"
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE Grave_Locations
                SET veteran_name=?, branch_of_service=?, birth_year=?, death_year=?,
                    cemetary_name=?, notes=?, photo_path=?
                WHERE id=?
            """, (
                veteran_name, branch_of_service, birth_year_int, death_year_int,
                cemetery_name, notes if notes else None, self.photo_path, self.grave_id,
            ))
            conn.commit()
            conn.close()

            print(f"Saved: {veteran_name}, {branch_of_service}, {death_year_int}")
            self.dismiss()

            confirm_popup = Popup(
                title='Record Saved',
                content=Label(
                    text=f'{veteran_name}\n\nSaved locally. Tap Sync to upload.',
                    halign='center',
                ),
                size_hint=(0.85, 0.30),
                auto_dismiss=True,
            )
            confirm_popup.open()

        except Exception as e:
            self.error_label.text = f"Database error: {str(e)}"
            print(f"Error saving: {e}")
            import traceback
            traceback.print_exc()
