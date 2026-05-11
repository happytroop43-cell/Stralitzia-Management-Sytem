import os
import json
import csv
import webbrowser
import tempfile
import subprocess
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout

# Dark Theme Window Setup
Window.clearcolor = (0.1, 0.1, 0.1, 1)

KV = """
ScreenManagement:
    MainScreen:
    AnalysisScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 15
        Label:
            text: "HR MANAGEMENT & STRENGTH SYSTEM"
            font_size: '26sp'
            size_hint_y: None
            height: 80
            bold: True
            color: (1, 0.5, 0, 1)
        
        TextInput:
            id: search_input
            hint_text: "Search by name..."
            multiline: False
            size_hint_y: None
            height: 55
            on_text: root.refresh()
        
        BoxLayout:
            size_hint_y: None
            height: 60
            spacing: 15
            Button:
                text: "Add Personnel"
                bold: True
                on_release: app.edit_person_popup(None)
            Button:
                text: "Strength Analysis"
                bold: True
                on_release: root.manager.current = 'analysis'
            Button:
                text: "Export CSV"
                bold: True
                background_color: (0.1, 0.6, 0.3, 1)
                on_release: app.export_to_excel()
        
        ScrollView:
            GridLayout:
                id: container
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                padding: 10

<AnalysisScreen>:
    name: 'analysis'
    BoxLayout:
        orientation: 'vertical'
        padding: 30
        spacing: 20
        Label:
            text: "UNIT STRENGTH ANALYSIS REPORT"
            font_size: '26sp'
            bold: True
            size_hint_y: None
            height: 60
        
        ScrollView:
            size_hint_y: 1
            GridLayout:
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                Label:
                    id: stats
                    text: "Calculating..."
                    font_size: '18sp'
                    halign: 'left'
                    valign: 'top'
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
            
        BoxLayout:
            size_hint_y: None
            height: 65
            spacing: 20
            Button:
                text: "Print Full Analysis"
                bold: True
                background_color: (0, 0.4, 0.8, 1)
                on_release: app.print_action(root.ids.stats.text)
            Button:
                text: "Back to Register"
                bold: True
                on_release: root.manager.current = 'main'
"""

class ScreenManagement(ScreenManager):
    pass

class MainScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.refresh)

    def refresh(self, dt=None):
        container = self.ids.container
        container.clear_widgets()
        app = App.get_running_app()
        query = self.ids.search_input.text.lower()
        
        for i, p in enumerate(app.people):
            if query in p['name'].lower():
                row = BoxLayout(size_hint_y=None, height=80, spacing=10)
                
                info = f"{p.get('prefix', 'Rfn')} {p.get('rnk', '')} {p['name']} ({p.get('suffix', 'PE')})"
                name_btn = Button(text=info, background_color=(0.2, 0.2, 0.2, 1), color=(1,1,1,1), font_size='16sp')
                name_btn.bind(on_release=lambda x, idx=i: app.edit_person_popup(idx))
                
                status_btn = Button(text=p['status'], size_hint_x=0.3, background_color=(1, 0.5, 0, 1), bold=True)
                status_btn.bind(on_release=lambda x, idx=i: app.cycle_status(idx))
                
                row.add_widget(name_btn)
                row.add_widget(status_btn)
                container.add_widget(row)

class AnalysisScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        total = len(app.people)
        pe = sum(1 for p in app.people if p.get('suffix') == "PE")
        mc = sum(1 for p in app.people if p.get('suffix') == "MC")
        
        # Military Rank Groupings
        off_ranks = ["Col", "Maj", "Capt", "Lt", "Cpln"]
        wo_ranks = ["WO1", "WO2"]
        
        officers = sum(1 for p in app.people if p.get('prefix') in off_ranks)
        warrant_off = sum(1 for p in app.people if p.get('prefix') in wo_ranks)
        other_ranks = total - officers - warrant_off

        # Status counts
        status_counts = {}
        for p in app.people:
            s = p.get('status', 'Unknown')
            status_counts[s] = status_counts.get(s, 0) + 1
        
        notes_list = "\n".join([f" • {p['name']} ({p.get('status', 'Unknown')}): {p.get('note', 'No notes')}" for p in app.people if p.get('note')])
        st_breakdown = "\n".join([f" • {s}: {c}" for s, c in status_counts.items()])

        self.ids.stats.text = (
            f"--- UNIT SUMMARY DATA ---\n"
            f"Total Personnel: {total}\n"
            f"PE (Permanent): {pe} | MC (Militia): {mc}\n"
            f"---------------------------\n"
            f"Officers: {officers}\n"
            f"Warrant Officers: {warrant_off}\n"
            f"Other Ranks: {other_ranks}\n"
            f"---------------------------\n"
            f"CURRENT STATUS BREAKDOWN:\n{st_breakdown}\n"
            f"---------------------------\n"
            f"SICK LEAVE / ADMIN REMARKS:\n{notes_list or 'No active notes.'}"
        )

class HRApp(App):
    people = ListProperty([])
    prefixes = ["Col", "Maj", "Cpln", "Capt", "Lt", "WO1", "WO2", "SSgt", "Cpl", "L/Cpl", "Rfn", "Psap"]

    def build(self):
        self.load_data()
        return Builder.load_string(KV)

    def load_data(self):
        self.data_file = os.path.join(self.user_data_dir, "hr_v7_db.json")
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self.people = json.load(f)
        else:
            self.people = [{"prefix": "Rfn", "fn": "000", "rnk": "Pte", "name": "Admin", "suffix": "PE", "status": "Present", "note": ""}]

    def save_data(self):
        with open(self.data_file, "w") as f: 
            json.dump(list(self.people), f, indent=4)

    def open_usb_chooser(self, target_input):
        content = BoxLayout(orientation='vertical')
        # Path='/' allows browsing to /media (Linux/USB) or Drive letters (Windows)
        chooser = FileChooserIconView(path='/', filters=['*'])
        content.add_widget(chooser)
        
        btn_row = BoxLayout(size_hint_y=None, height=50)
        sel_btn = Button(text="Select File")
        can_btn = Button(text="Cancel")
        btn_row.add_widget(sel_btn)
        btn_row.add_widget(can_btn)
        content.add_widget(btn_row)
        
        popup = Popup(title="Browse External USB/OTG Storage", content=content, size_hint=(0.95, 0.95))
        
        def on_select(instance):
            if chooser.selection:
                target_input.text = chooser.selection[0]
                popup.dismiss()
        
        sel_btn.bind(on_release=on_select)
        can_btn.bind(on_release=popup.dismiss)
        popup.open()

    def edit_person_popup(self, index=None):
        if index is not None:
            p = self.people[index]
        else:
            p = {"prefix": "Rfn", "fn": "", "rnk": "", "name": "", "suffix": "PE", "status": "Present", "note": ""}

        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        # Row 1: The requested structure
        row1 = BoxLayout(size_hint_y=None, height=55, spacing=8)
        
        prefix_btn = Button(text=p.get('prefix', 'Rfn'), size_hint_x=0.2, bold=True, background_color=(0.2, 0.4, 0.8, 1))
        def toggle_pref(inst):
            inst.text = self.prefixes[(self.prefixes.index(inst.text) + 1) % len(self.prefixes)]
        prefix_btn.bind(on_release=toggle_pref)

        fn_in = TextInput(text=p.get('fn', ''), hint_text="F/N", multiline=False, size_hint_x=0.15)
        rnk_in = TextInput(text=p.get('rnk', ''), hint_text="RNK", multiline=False, size_hint_x=0.15)
        name_in = TextInput(text=p.get('name', ''), hint_text="Name", multiline=False, size_hint_x=0.35)
        
        suffix_btn = Button(text=p.get('suffix', 'PE'), size_hint_x=0.15, bold=True, background_color=(0.2, 0.6, 0.4, 1))
        def toggle_suf(inst):
            inst.text = "MC" if inst.text == "PE" else "PE"
        suffix_btn.bind(on_release=toggle_suf)

        row1.add_widget(prefix_btn)
        row1.add_widget(fn_in)
        row1.add_widget(rnk_in)
        row1.add_widget(name_in)
        row1.add_widget(suffix_btn)

        # Row 2: Sick Leave / Notes / USB Attach
        row2 = BoxLayout(size_hint_y=None, height=55, spacing=8)
        note_in = TextInput(text=p.get('note', ''), hint_text="Sick Leave Note or USB File Path...", multiline=False)
        usb_btn = Button(text="Attach File", size_hint_x=0.25, background_color=(1, 0.8, 0, 1), color=(0,0,0,1), bold=True)
        usb_btn.bind(on_release=lambda x: self.open_usb_chooser(note_in))
        
        row2.add_widget(note_in)
        row2.add_widget(usb_btn)

        content.add_widget(row1)
        content.add_widget(row2)

        # Main Controls
        btn_layout = BoxLayout(size_hint_y=None, height=60, spacing=10)
        save_btn = Button(text="SAVE RECORD", background_color=(0, 0.7, 0, 1), bold=True)
        print_btn = Button(text="PRINT RECORD", background_color=(0, 0.4, 0.8, 1), bold=True)
        clear_btn = Button(text="CLEAR", background_color=(0.8, 0, 0, 1), bold=True)
        cancel_btn = Button(text="CANCEL")

        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(print_btn)
        btn_layout.add_widget(clear_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Personnel File Editor", content=content, size_hint=(0.95, 0.75))

        print_btn.bind(on_release=lambda x: self.print_action(f"SICK LEAVE / PERSONNEL RECORD\nName: {name_in.text}\nRank: {prefix_btn.text} {rnk_in.text}\nNote: {note_in.text}"))
        
        def save_person(instance):
            new_data = {
                "prefix": prefix_btn.text, "fn": fn_in.text, "rnk": rnk_in.text,
                "name": name_in.text, "suffix": suffix_btn.text, "status": p['status'], "note": note_in.text
            }
            if index is not None:
                self.people[index] = new_data
            else:
                self.people.append(new_data)
            self.save_data()
            self.root.get_screen('main').refresh()
            popup.dismiss()

        def clear_fields():
            fn_in.text = ''
            rnk_in.text = ''
            name_in.text = ''
            note_in.text = ''

        save_btn.bind(on_release=save_person)
        clear_btn.bind(on_release=lambda x: clear_fields())
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def print_action(self, text):
        """Generates a text report and triggers system print dialogue."""
        try:
            fd, path = tempfile.mkstemp(suffix=".txt")
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(text)
            
            if os.name == 'nt':
                os.startfile(path, "print")  # Windows Native
            elif os.name == 'posix':
                # Unix/Linux/Mac
                if os.uname().sysname == 'Darwin':
                    subprocess.run(['open', path])  # macOS
                else:
                    subprocess.run(['xdg-open', path])  # Linux
        except Exception as e:
            print(f"Printing error: {e}")

    def export_to_excel(self):
        path = os.path.join(os.path.expanduser("~"), "HR_Nominal_Roll.csv")
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Prefix", "F/N", "RNK", "Name", "Suffix", "Status", "Note"])
                for p in self.people:
                    writer.writerow([p.get('prefix'), p.get('fn'), p.get('rnk'), p.get('name'), p.get('suffix'), p.get('status'), p.get('note')])
            
            # Open the file with the default application
            if os.name == 'nt':
                os.startfile(path)  # Windows
            elif os.name == 'posix':
                if os.uname().sysname == 'Darwin':
                    subprocess.run(['open', path])  # macOS
                else:
                    subprocess.run(['xdg-open', path])  # Linux
            print(f"CSV exported successfully to {path}")
        except Exception as e:
            print(f"Export error: {e}")

    def cycle_status(self, index):
        states = ["Present", "Absent", "Leave", "Sick", "OI", "OE", "MA", "TIL", "STUDY LEAVE", "Course", "Detached Duty"]
        curr = self.people[index].get("status", "Present")
        next_idx = (states.index(curr) + 1) % len(states) if curr in states else 0
        self.people[index]["status"] = states[next_idx]
        self.save_data()
        self.root.get_screen('main').refresh()

if __name__ == "__main__":
    HRApp().run()
