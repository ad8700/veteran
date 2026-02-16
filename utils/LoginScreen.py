"""
LoginScreen - User authentication UI for Veteran Grave Marker app

Provides options for:
- Sign in with Google
- Sign in with email/password
- Create account
- Continue as guest
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

from utils.AuthManager import get_auth_manager


class LoginScreen(Screen):
    """Login screen with multiple authentication options"""

    def __init__(self, on_login_complete=None, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.name = 'login'
        self.on_login_complete = on_login_complete
        self.auth_manager = get_auth_manager()

        # Check if already authenticated
        if self.auth_manager.is_authenticated():
            # Skip login screen
            Clock.schedule_once(lambda dt: self._complete_login(), 0.1)
            return

        self._build_ui()

    def _build_ui(self):
        """Build the login screen UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # Title
        title = Label(
            text='Veteran Grave Marker',
            font_size='24sp',
            size_hint_y=0.15,
            bold=True
        )
        layout.add_widget(title)

        # Subtitle
        subtitle = Label(
            text='Sign in to sync your data across devices',
            font_size='14sp',
            size_hint_y=0.08,
            color=(0.7, 0.7, 0.7, 1)
        )
        layout.add_widget(subtitle)

        # Spacer
        layout.add_widget(Label(size_hint_y=0.1))

        # Google Sign-In Button
        google_btn = Button(
            text='Sign in with Google',
            size_hint_y=0.12,
            background_color=(0.9, 0.3, 0.2, 1)
        )
        google_btn.bind(on_press=self._sign_in_with_google)
        layout.add_widget(google_btn)

        # Divider
        divider_layout = BoxLayout(size_hint_y=0.08, spacing=10)
        divider_layout.add_widget(Label(text='───────', color=(0.5, 0.5, 0.5, 1)))
        divider_layout.add_widget(Label(text='or', color=(0.5, 0.5, 0.5, 1), size_hint_x=0.3))
        divider_layout.add_widget(Label(text='───────', color=(0.5, 0.5, 0.5, 1)))
        layout.add_widget(divider_layout)

        # Email input
        self.email_input = TextInput(
            hint_text='Email',
            multiline=False,
            size_hint_y=0.1,
            input_type='mail'
        )
        layout.add_widget(self.email_input)

        # Password input
        self.password_input = TextInput(
            hint_text='Password',
            multiline=False,
            password=True,
            size_hint_y=0.1
        )
        layout.add_widget(self.password_input)

        # Error label
        self.error_label = Label(
            text='',
            color=(1, 0.3, 0.3, 1),
            size_hint_y=0.08
        )
        layout.add_widget(self.error_label)

        # Sign In / Create Account buttons
        button_row = BoxLayout(size_hint_y=0.12, spacing=10)

        sign_in_btn = Button(text='Sign In')
        sign_in_btn.bind(on_press=self._sign_in_email)
        button_row.add_widget(sign_in_btn)

        create_btn = Button(text='Create Account')
        create_btn.bind(on_press=self._show_create_account)
        button_row.add_widget(create_btn)

        layout.add_widget(button_row)

        # Spacer
        layout.add_widget(Label(size_hint_y=0.05))

        # Guest button
        guest_btn = Button(
            text='Continue as Guest',
            size_hint_y=0.1,
            background_color=(0.3, 0.3, 0.3, 1)
        )
        guest_btn.bind(on_press=self._continue_as_guest)
        layout.add_widget(guest_btn)

        # Info text
        info = Label(
            text='Guest data is stored locally only.\nSign in to sync across devices.',
            font_size='12sp',
            size_hint_y=0.12,
            color=(0.6, 0.6, 0.6, 1)
        )
        layout.add_widget(info)

        self.add_widget(layout)

    def _sign_in_with_google(self, instance):
        """Initiate Google Sign-In"""
        self.error_label.text = ''

        if platform == 'android':
            # Open browser for Google OAuth
            url = self.auth_manager.get_google_sign_in_url()
            self._open_browser(url)
        else:
            self.error_label.text = 'Google Sign-In requires Android device'

    def _open_browser(self, url):
        """Open URL in browser for OAuth"""
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
        """Handle OAuth callback from browser redirect"""
        def on_success(user_info):
            self._complete_login()

        def on_error(error):
            self.error_label.text = str(error)

        self.auth_manager.handle_oauth_callback(url, on_success, on_error)

    def _sign_in_email(self, instance):
        """Sign in with email and password"""
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
        """Show create account popup"""
        popup_content = BoxLayout(orientation='vertical', padding=10, spacing=10)

        name_input = TextInput(
            hint_text='Name',
            multiline=False,
            size_hint_y=None,
            height=44
        )
        popup_content.add_widget(name_input)

        email_input = TextInput(
            hint_text='Email',
            multiline=False,
            size_hint_y=None,
            height=44,
            input_type='mail'
        )
        popup_content.add_widget(email_input)

        password_input = TextInput(
            hint_text='Password (8+ characters)',
            multiline=False,
            password=True,
            size_hint_y=None,
            height=44
        )
        popup_content.add_widget(password_input)

        error_label = Label(
            text='',
            color=(1, 0.3, 0.3, 1),
            size_hint_y=None,
            height=30
        )
        popup_content.add_widget(error_label)

        button_row = BoxLayout(size_hint_y=None, height=44, spacing=10)

        popup = Popup(
            title='Create Account',
            content=popup_content,
            size_hint=(0.9, 0.6)
        )

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

        create_btn = Button(text='Create')
        create_btn.bind(on_press=do_create)
        button_row.add_widget(create_btn)

        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        button_row.add_widget(cancel_btn)

        popup_content.add_widget(button_row)
        popup.open()

    def _show_verification_popup(self, email):
        """Show email verification popup"""
        popup_content = BoxLayout(orientation='vertical', padding=10, spacing=10)

        info = Label(
            text=f'A verification code was sent to:\n{email}\n\nEnter the code below:',
            size_hint_y=0.4
        )
        popup_content.add_widget(info)

        code_input = TextInput(
            hint_text='Verification Code',
            multiline=False,
            size_hint_y=None,
            height=44,
            input_filter='int'
        )
        popup_content.add_widget(code_input)

        error_label = Label(
            text='',
            color=(1, 0.3, 0.3, 1),
            size_hint_y=None,
            height=30
        )
        popup_content.add_widget(error_label)

        popup = Popup(
            title='Verify Email',
            content=popup_content,
            size_hint=(0.9, 0.5)
        )

        def do_verify(btn):
            code = code_input.text.strip()
            if not code:
                error_label.text = 'Enter verification code'
                return

            error_label.text = 'Verifying...'
            btn.disabled = True

            def on_success(result):
                popup.dismiss()
                # Show success message
                success_popup = Popup(
                    title='Success',
                    content=Label(text='Account created!\nYou can now sign in.'),
                    size_hint=(0.8, 0.3)
                )
                success_popup.open()

            def on_error(error):
                btn.disabled = False
                error_label.text = str(error)

            self.auth_manager.confirm_sign_up(email, code, on_success, on_error)

        button_row = BoxLayout(size_hint_y=None, height=44, spacing=10)

        verify_btn = Button(text='Verify')
        verify_btn.bind(on_press=do_verify)
        button_row.add_widget(verify_btn)

        cancel_btn = Button(text='Cancel')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        button_row.add_widget(cancel_btn)

        popup_content.add_widget(button_row)
        popup.open()

    def _continue_as_guest(self, instance):
        """Continue without signing in"""
        self.auth_manager.continue_as_guest(on_success=self._complete_login)

    def _complete_login(self):
        """Called when login is complete (or skipped)"""
        if self.on_login_complete:
            self.on_login_complete()


class UserStatusBar(BoxLayout):
    """Shows current user status and sign out button"""

    def __init__(self, on_sign_out=None, **kwargs):
        super(UserStatusBar, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.padding = [10, 5]
        self.spacing = 10

        self.on_sign_out = on_sign_out
        self.auth_manager = get_auth_manager()

        self._build_ui()

    def _build_ui(self):
        # User label
        self.user_label = Label(
            text=self._get_user_text(),
            halign='left',
            size_hint_x=0.7
        )
        self.user_label.bind(size=self.user_label.setter('text_size'))
        self.add_widget(self.user_label)

        # Sign out / Sign in button
        self.auth_button = Button(
            text='Sign Out' if self.auth_manager.is_authenticated() else 'Sign In',
            size_hint_x=0.3
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
        """Update the UI to reflect current auth state"""
        self.user_label.text = self._get_user_text()
        self.auth_button.text = 'Sign Out' if self.auth_manager.is_authenticated() else 'Sign In'
