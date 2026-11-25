"""
Android APK & Portable UI entry point for Atulya All File Converter.
Launches the local conversion server in a background thread and opens the interactive UI.
"""
import sys
import threading
import time

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.core.window import Window
    import webbrowser

    class AtulyaConverterApp(App):
        def build(self):
            Window.clearcolor = (0.05, 0.07, 0.09, 1.0)
            layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
            
            title = Label(
                text="⚡ Atulya File Converter",
                font_size='24sp',
                bold=True,
                color=(0.35, 0.65, 1.0, 1.0),
                size_hint_y=0.3
            )
            subtitle = Label(
                text="100% Private Offline Conversion Engine\n40+ Formats (PDF, DOCX, CSV, Images)",
                font_size='14sp',
                color=(0.7, 0.75, 0.8, 1.0),
                halign='center',
                size_hint_y=0.3
            )
            btn_studio = Button(
                text="Open Converter Studio",
                size_hint=(0.85, 0.2),
                pos_hint={'center_x': 0.5},
                background_color=(0.14, 0.53, 0.21, 1.0)
            )
            btn_studio.bind(on_release=self.open_studio)

            btn_update = Button(
                text="🔄 Check for OTA Updates",
                size_hint=(0.85, 0.18),
                pos_hint={'center_x': 0.5},
                background_color=(0.23, 0.35, 0.6, 1.0)
            )
            btn_update.bind(on_release=self.trigger_ota_update)

            self.status_label = Label(
                text="Version: 0.1.0 (Offline Engine Ready)",
                font_size='12sp',
                color=(0.5, 0.55, 0.6, 1.0),
                size_hint_y=0.15
            )

            layout.add_widget(title)
            layout.add_widget(subtitle)
            layout.add_widget(btn_studio)
            layout.add_widget(btn_update)
            layout.add_widget(self.status_label)
            return layout

        def trigger_ota_update(self, *args):
            self.status_label.text = "Checking GitHub for OTA updates..."
            threading.Thread(target=self._check_ota_background, daemon=True).start()

        def _check_ota_background(self):
            try:
                from atulya_all_file_converter.updater import check_for_updates, download_and_apply_update
                from atulya_all_file_converter import __version__
                info = check_for_updates(__version__)
                if not info:
                    self.status_label.text = "You are on the latest version!"
                    return
                self.status_label.text = f"Found v{info['latest_version']}! Downloading APK..."
                success, msg = download_and_apply_update(info["download_url"], info["asset_name"])
                self.status_label.text = msg
            except Exception as ex:
                self.status_label.text = f"Update error: {ex}"

        def on_start(self):
            threading.Thread(target=self.start_server, daemon=True).start()

        def start_server(self):
            try:
                import uvicorn
                from atulya_all_file_converter.server import app
                uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
            except Exception as e:
                print(f"Server start error: {e}")

        def open_studio(self, *args):
            webbrowser.open("http://127.0.0.1:8765")

    if __name__ == '__main__':
        AtulyaConverterApp().run()

except ImportError:
    # Fallback to direct CLI or local server
    from atulya_all_file_converter.cli import main
    if __name__ == '__main__':
        main()
