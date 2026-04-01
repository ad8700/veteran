"""
LoginScreen - Modern authentication UI for Veteran Grave Marker app
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle

from utils.AuthManager import get_auth_manager

# ── Color Palette ──
COLORS = {
    'bg':          (0.11, 0.11, 0.16, 1),
    'surface':     (0.16, 0.17, 0.23, 1),
    'card':        (0.20, 0.21, 0.28, 1),
    'primary':     (0.20, 0.50, 0.90, 1),
    'accent':      (0.00, 0.59, 0.53, 1),
    'google':      (0.85, 0.26, 0.22, 1),
    'text':        (0.93, 0.93, 0.96, 1),
    'text_dim':    (0.55, 0.57, 0.63, 1),
    'white':       (1, 1, 1, 1),
    'input_bg':    (0.14, 0.14, 0.20, 1),
    'danger':      (1, 0.35, 0.35, 1),
}


def _flat_btn(text, bg_key='primary', height=dp(48), font_size='16sp', **kw):
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


def _styled_input(hint, **kw):
    return TextInput(
        hint_text=hint,
        multiline=False,
        size_hint_y=None,
        height=dp(46),
        background_color=COLORS['input_bg'],
        foreground_color=COLORS['text'],
        hint_text_color=COLORS['text_dim'],
        cursor_color=COLORS['primary'],
        padding=[dp(12), dp(10)],
        font_size='15sp',
        **kw,
    )


class LoginScreen(Screen):
    """Login screen with multiple authentication options"""

    def __init__(self, on_login_complete=None, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.name = 'login'
        self.on_login_complete = on_login_complete
        self.auth_manager = get_auth_manager()

        if self.auth_manager.is_authenticated():
            Clock.schedule_once(lambda dt: self._complete_login(), 0.1)
            return

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=[dp(24), dp(32)], spacing=dp(14))
        with root.canvas.before:
            Color(*COLORS['bg'])
            self._bg = Rectangle(size=root.size, pos=root.pos)
        root.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

        # Title
        root.add_widget(Label(size_hint_y=0.08))  # top spacer

        title = Label(
            text='Veteran Grave Marker',
            font_size='26sp',
            size_hint_y=None,
            height=dp(40),
            bold=True,
            color=COLORS['text'],
        )
        root.add_widget(title)

        subtitle = Label(
            text='Sign in to sync your data across devices',
            font_size='14sp',
            size_hint_y=None,
            height=dp(24),
            color=COLORS['text_dim'],
        )
        root.add_widget(subtitle)

        root.add_widget(Label(size_hint_y=0.06))  # spacer

        # Google sign-in
        google_btn = _flat_btn('Sign in with Google', bg_key='google', height=dp(50), font_size='17sp')
        google_btn.bind(on_press=self._sign_in_with_google)
        root.add_widget(google_btn)

        # Divider
        divider = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        divider.add_widget(Label(text='', size_hint_x=0.4))
        divider.add_widget(Label(text='or', color=COLORS['text_dim'], font_size='13sp', size_hint_x=0.2))
        divider.add_widget(Label(text='', size_hint_x=0.4))
        root.add_widget(divider)

        # Email / password
        self.email_input = _styled_input('Email', input_type='mail')
        root.add_widget(self.email_input)

        self.password_input = _styled_input('Password', password=True)
        root.add_widget(self.password_input)

        # Error
        self.error_label = Label(
            text='',
            color=COLORS['danger'],
            size_hint_y=None,
            height=dp(24),
            font_size='13sp',
        )
        root.add_widget(self.error_label)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        sign_in_btn = _flat_btn('Sign In', bg_key='primary')
        sign_in_btn.bind(on_press=self._sign_in_email)
        btn_row.add_widget(sign_in_btn)

        create_btn = _flat_btn('Create Account', bg_key='surface')
        create_btn.bind(on_press=self._show_create_account)
        btn_row.add_widget(create_btn)
        root.add_widget(btn_row)

        root.add_widget(Label(size_hint_y=0.04))  # spacer

        # Guest
        guest_btn = _flat_btn('Continue as Guest', bg_key='card', height=dp(46), font_size='15sp')
        guest_btn.bind(on_press=self._continue_as_guest)
        root.add_widget(guest_btn)

        info = Label(
            text='Guest data is stored locally only.\nSign in to sync across devices.',
            font_size='12sp',
            size_hint_y=None,
            height=dp(36),
            color=COLORS['text_dim'],
        )
        root.add_widget(info)

        root.add_widget(Label(size_hint_y=0.1))  # bottom spacer

        self.add_widget(root)

    def _sign_in_with_google(self, instance):
        self.error_label.text = ''
        if platform == 'android':
            url = self.auth_manager.get_google_sign_in_url()
            self._open_browser(url)
        else:
            self.error_label.text = 'Google Sign-In requires Android device'

    def _open_browser(self, url):
        try:
            if platform == 'android':
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Intent.ACTION_VIEW)
                intent.setData(Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
            else:
                import webbrowser
                webbrowser.open(url)
        except Exception as e:
            self.error_label.text = f'Error opening browser: {str(e)}'

    def handle_oauth_callback(self, url):
        def on_success(user_info):
            self._complete_login()

        def on_error(error):
            self.error_label.text = str(error)

        self.auth_manager.handle_oauth_callback(url, on_success, on_error)

    def _sign_in_email(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text

        if not email or not password:
            self.error_label.text = 'Please enter email and password'
            return

        self.error_label.text = 'Signing in...'
        instance.disabled = True

        def on_success(user_info):
            instance.disabled = False
            self._complete_login()

        def on_error(error):
            instance.disabled = False
            self.error_label.text = str(error)

        self.auth_manager.sign_in(email, password, on_success, on_error)

    def _show_create_account(self, instance):
        popup_content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        name_input = _styled_input('Name')
        popup_content.add_widget(name_input)

        email_input = _styled_input('Email', input_type='mail')
        popup_content.add_widget(email_input)

        password_input = _styled_input('Password (8+ characters)', password=True)
        popup_content.add_widget(password_input)

        error_label = Label(text='', color=COLORS['danger'], size_hint_y=None, height=dp(24), font_size='13sp')
        popup_content.add_widget(error_label)

        popup = Popup(title='Create Account', content=popup_content, size_hint=(0.9, 0.6))

        def do_create(btn):
            name = name_input.text.strip()
            email = email_input.text.strip()
            password = password_input.text
            if not email or not password:
                error_label.text = 'Email and password required'
                return
            if len(password) < 8:
                error_label.text = 'Password must be 8+ characters'
                return
            error_label.text = 'Creating account...'
            btn.disabled = True

            def on_success(result):
                popup.dismiss()
                self._show_verification_popup(email)

            def on_error(error):
                btn.disabled = False
                error_label.text = str(error)

            self.auth_manager.sign_up(email, password, name, on_success, on_error)

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        create_btn = _flat_btn('Create', bg_key='primary')
        create_btn.bind(on_press=do_create)
        btn_row.add_widget(create_btn)

        cancel_btn = _flat_btn('Cancel', bg_key='surface')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_row.add_widget(cancel_btn)

        popup_content.add_widget(btn_row)
        popup.open()

    def _show_verification_popup(self, email):
        popup_content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        info = Label(
            text=f'A verification code was sent to:\n{email}\n\nEnter the code below:',
            size_hint_y=0.4,
            color=COLORS['text'],
        )
        popup_content.add_widget(info)

        code_input = _styled_input('Verification Code', input_filter='int')
        popup_content.add_widget(code_input)

        error_label = Label(text='', color=COLORS['danger'], size_hint_y=None, height=dp(24), font_size='13sp')
        popup_content.add_widget(error_label)

        popup = Popup(title='Verify Email', content=popup_content, size_hint=(0.9, 0.5))

        def do_verify(btn):
            code = code_input.text.strip()
            if not code:
                error_label.text = 'Enter verification code'
                return
            error_label.text = 'Verifying...'
            btn.disabled = True

            def on_success(result):
                popup.dismiss()
                success_popup = Popup(
                    title='Success',
                    content=Label(text='Account created!\nYou can now sign in.'),
                    size_hint=(0.8, 0.3),
                )
                success_popup.open()

            def on_error(error):
                btn.disabled = False
                error_label.text = str(error)

            self.auth_manager.confirm_sign_up(email, code, on_success, on_error)

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        verify_btn = _flat_btn('Verify', bg_key='primary')
        verify_btn.bind(on_press=do_verify)
        btn_row.add_widget(verify_btn)

        cancel_btn = _flat_btn('Cancel', bg_key='surface')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_row.add_widget(cancel_btn)

        popup_content.add_widget(btn_row)
        popup.open()

    def _continue_as_guest(self, instance):
        self.auth_manager.continue_as_guest(on_success=self._complete_login)

    def _complete_login(self):
        if self.on_login_complete:
            self.on_login_complete()


class UserStatusBar(BoxLayout):
    """Shows current user status and sign out button"""

    def __init__(self, on_sign_out=None, **kwargs):
        super(UserStatusBar, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(42)
        self.padding = [dp(12), dp(4)]
        self.spacing = dp(8)
        self.on_sign_out = on_sign_out
        self.auth_manager = get_auth_manager()

        with self.canvas.before:
            Color(0.14, 0.14, 0.20, 1)
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

        self._build_ui()

    def _build_ui(self):
        self.user_label = Label(
            text=self._get_user_text(),
            halign='left',
            size_hint_x=0.7,
            font_size='13sp',
            color=(0.75, 0.76, 0.80, 1),
        )
        self.user_label.bind(size=self.user_label.setter('text_size'))
        self.add_widget(self.user_label)

        self.auth_button = Button(
            text='Sign Out' if self.auth_manager.is_authenticated() else 'Sign In',
            size_hint_x=0.3,
            background_normal='',
            background_color=(0.20, 0.21, 0.28, 1),
            color=(0.75, 0.76, 0.80, 1),
            font_size='13sp',
        )
        self.auth_button.bind(on_press=self._on_auth_button)
        self.add_widget(self.auth_button)

    def _get_user_text(self):
        if self.auth_manager.is_guest:
            return "Guest (local only)"
        return f"Signed in: {self.auth_manager.get_user_display_name()}"

    def _on_auth_button(self, instance):
        if self.auth_manager.is_authenticated():
            self.auth_manager.sign_out(on_complete=self._on_signed_out)
        else:
            if self.on_sign_out:
                self.on_sign_out()

    def _on_signed_out(self):
        self.update()
        if self.on_sign_out:
            self.on_sign_out()

    def update(self):
        self.user_label.text = self._get_user_text()
        self.auth_button.text = 'Sign Out' if self.auth_manager.is_authenticated() else 'Sign In'
