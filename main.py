import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

try:
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False


class Ps2ToolMilosApp(App):
    def build(self):
        self.usb_root = None
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=8)
        self.status_label = Label(text="Ps2ToolMilos - Pret", font_size=16, size_hint=(1, 0.12))
        self.layout.add_widget(self.status_label)
        row1 = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=5)
        scan_btn = Button(text="Scanner USB")
        scan_btn.bind(on_press=self.scan_usb)
        row1.add_widget(scan_btn)
        list_btn = Button(text="Lister fichiers")
        list_btn.bind(on_press=self.list_files)
        row1.add_widget(list_btn)
        self.layout.add_widget(row1)
        row2 = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=5)
        self.game_id_input = TextInput(hint_text="ID jeu (ex: SLES-12345)", multiline=False)
        row2.add_widget(self.game_id_input)
        self.game_name_input = TextInput(hint_text="Nom du jeu", multiline=False)
        row2.add_widget(self.game_name_input)
        self.layout.add_widget(row2)
        row3 = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=5)
        storage_btn = Button(text="Verifier espace")
        storage_btn.bind(on_press=self.check_storage)
        row3.add_widget(storage_btn)
        cover_btn = Button(text="Telecharger jaquette")
        cover_btn.bind(on_press=self.on_download_cover)
        row3.add_widget(cover_btn)
        self.layout.add_widget(row3)
        self.scroll = ScrollView(size_hint=(1, 0.58))
        self.file_grid = GridLayout(cols=1, size_hint_y=None, spacing=5)
        self.file_grid.bind(minimum_height=self.file_grid.setter('height'))
        self.scroll.add_widget(self.file_grid)
        self.layout.add_widget(self.scroll)
        return self.layout

    def on_download_cover(self, instance):
        game_id = self.game_id_input.text.strip()
        if not game_id:
            self.status_label.text = "Entre un ID de jeu d'abord"
            return
        paths = self.get_usb_paths()
        if not paths:
            self.status_label.text = "Aucune cle USB trouvee"
            return
        self.usb_root = paths[0]
        result = self.download_cover_art(game_id, self.usb_root)
        if result:
            self.status_label.text = f"Jaquette telechargee: {result}"

    def get_usb_paths(self):
        paths = []
        if not ANDROID:
            return paths
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            dirs = activity.getExternalFilesDirs(None)
            for i in range(len(dirs)):
                d = dirs[i]
                if d is not None:
                    full_path = d.getAbsolutePath()
                    if "/Android/data/" in full_path:
                        root = full_path.split("/Android/data/")[0]
                        paths.append(root)
        except Exception as e:
            self.status_label.text = f"Erreur chemins: {str(e)}"
        return paths

    def scan_usb(self, instance):
        if not ANDROID:
            self.status_label.text = "USB non disponible"
            return
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            usb_manager = activity.getSystemService(Context.USB_SERVICE)
            device_list = usb_manager.getDeviceList()
            devices = device_list.values().toArray()
            if len(devices) == 0:
                self.status_label.text = "Aucune cle USB detectee"
            else:
                names = []
                for i in range(len(devices)):
                    device = devices[i]
                    names.append(device.getDeviceName())
                self.status_label.text = "USB: " + ", ".join(names)
        except Exception as e:
            self.status_label.text = f"Erreur: {str(e)}"

    def list_files(self, instance):
        self.file_grid.clear_widgets()
        paths = self.get_usb_paths()
        if not paths:
            self.file_grid.add_widget(Label(text="Aucun volume trouve", size_hint_y=None, height=40))
            return
        for path in paths:
            try:
                entries = os.listdir(path)
                self.file_grid.add_widget(Label(text=f"[{path}]", size_hint_y=None, height=30, bold=True))
                if not entries:
                    self.file_grid.add_widget(Label(text="  (vide)", size_hint_y=None, height=30))
                for entry in entries:
                    full = os.path.join(path, entry)
                    tag = "[DIR]" if os.path.isdir(full) else "[FILE]"
                    self.file_grid.add_widget(Label(text=f"  {tag} {entry}", size_hint_y=None, height=30))
            except Exception as e:
                self.file_grid.add_widget(Label(text=f"Erreur: {str(e)}", size_hint_y=None, height=30))

    def check_storage(self, instance):
        paths = self.get_usb_paths()
        if not paths:
            self.status_label.text = "Aucun volume trouve"
            return
        info = []
        for path in paths:
            try:
                stat = os.statvfs(path)
                total = (stat.f_blocks * stat.f_frsize) // (1024*1024)
                free = (stat.f_bavail * stat.f_frsize) // (1024*1024)
                used = total - free
                info.append(f"{path}\nTotal: {total}Mo Libre: {free}Mo")
            except Exception as e:
                info.append(f"{path}: erreur {str(e)}")
        self.status_label.text = "\n".join(info)

    def download_cover_art(self, game_id, usb_root):
        try:
            import requests
        except ImportError:
            self.status_label.text = "Module requests non disponible"
            return None
        clean_id = game_id.replace("-", "_").replace(".", "_")
        url = f"https://art.gametdb.com/ps2/cover/EN/{clean_id}.jpg"
        art_dir = os.path.join(usb_root, "ART")
        if not os.path.exists(art_dir):
            os.makedirs(art_dir)
        dest_path = os.path.join(art_dir, f"{game_id}_COV.jpg")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(resp.content)
                return dest_path
            else:
                self.status_label.text = f"Jaquette non trouvee (code {resp.status_code})"
                return None
        except Exception as e:
            self.status_label.text = f"Erreur telechargement: {str(e)}"
            return None

    def detect_format(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        mapping = {".iso": "ISO", ".bin": "BIN", ".cue": "CUE", ".nrg": "NRG", ".ul": "UL"}
        return mapping.get(ext, "INCONNU")

    def convert_bin_cue_to_iso(self, cue_path, output_path):
        cue_dir = os.path.dirname(cue_path)
        bin_file = None
        with open(cue_path, 'r', errors='ignore') as f:
            for line in f:
                if line.strip().upper().startswith("FILE"):
                    parts = line.split('"')
                    if len(parts) >= 2:
                        bin_file = parts[1]
                        break
        if not bin_file:
            raise Exception("BIN introuvable dans le CUE")
        bin_path = os.path.join(cue_dir, bin_file)
        with open(bin_path, 'rb') as src, open(output_path, 'wb') as dst:
            while True:
                chunk = src.read(1024*1024)
                if not chunk:
                    break
                dst.write(chunk)
        return output_path

    def split_iso_to_ul(self, iso_path, game_id, game_name, output_dir):
        chunk_size = 1024 * 1024 * 1024 - 4096
        safe_name = "".join(c if c.isalnum() else "." for c in game_name)
        base_name = f"{game_id}.{safe_name}"
        total_size = os.path.getsize(iso_path)
        part_num = 0
        written = 0
        with open(iso_path, 'rb') as src:
            while written < total_size:
                part_name = f"{base_name}.{part_num:02d}"
                part_path = os.path.join(output_dir, part_name)
                remaining = min(chunk_size, total_size - written)
                with open(part_path, 'wb') as dst:
                    to_write = remaining
                    while to_write > 0:
                        buf = src.read(min(1024*1024, to_write))
                        if not buf:
                            break
                        dst.write(buf)
                        to_write -= len(buf)
                written += remaining
                part_num += 1
        return part_num


if __name__ == "__main__":
    Ps2ToolMilosApp().run()
