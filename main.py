import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout

class veteranGraveApp(App):
    def build(self):
        layout = GridLayout(cols=1)
        label = Label(text="Welcome")
        layout.add_widget(label)
        return layout
    