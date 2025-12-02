import os
import sys
import warnings
import threading
import time
import json
import hashlib
import uuid
import datetime
import numpy as np  # <--- FIXED: Added missing import
from PIL import Image, ImageTk

# --- 1. SYSTEM CONFIGURATION ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Global placeholders for lazy loading
tf = None
hub = None
image_utils = None

# --- CONSTANTS ---
APP_NAME = "Crop Manager Pro"
VERSION = "v3.1 Stable"
DATA_FILE = "user_data.json"
MODEL_PATH = "my_model"
CLASSES_FILE = "classes.txt"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")
COLOR_ACCENT = "#2cc985"
COLOR_DANGER = "#e74c3c"
COLOR_BG_CARD = "#2b2b2b"

# --- 2. KNOWLEDGE BASE ---
class KnowledgeBase:
    """Generates detailed insights based on disease labels."""
    ADVICE = {
        "bacterial_spot": {
            "cause": "Bacterial infection (Xanthomonas)",
            "symptoms": "Small, water-soaked spots on leaves turning brown/black.",
            "treatment": "Apply copper-based fungicides. Remove infected leaves.",
            "prevention": "Avoid overhead watering. Rotate crops yearly."
        },
        "early_blight": {
            "cause": "Fungal infection (Alternaria solani)",
            "symptoms": "Concentric rings (bullseye pattern) on lower leaves.",
            "treatment": "Use bio-fungicides or copper sprays.",
            "prevention": "Mulch soil to prevent spore splash. Stake plants."
        },
        "late_blight": {
            "cause": "Water mold (Phytophthora infestans)",
            "symptoms": "Large, dark, greasy blotches. White fuzzy growth.",
            "treatment": "Use fungicides with chlorothalonil/copper immediately.",
            "prevention": "Destroy infected debris. Do not compost."
        },
        "powdery_mildew": {
            "cause": "Fungal spores",
            "symptoms": "White, flour-like powder on leaf surfaces.",
            "treatment": "Neem oil, sulfur sprays, or baking soda mixture.",
            "prevention": "Ensure good air circulation."
        },
        "healthy": {
            "cause": "N/A",
            "symptoms": "Leaves are vibrant green and structurally sound.",
            "treatment": "Continue current care routine.",
            "prevention": "Monitor regularly."
        }
    }

    @staticmethod
    def generate_report(raw_label, confidence):
        clean_label = raw_label.replace("_", " ").strip()
        is_healthy = "healthy" in clean_label.lower()
        
        # Find advice key
        key_match = "generic"
        for key in KnowledgeBase.ADVICE:
            if key in clean_label.lower():
                key_match = key
                break
        
        info = KnowledgeBase.ADVICE.get(key_match, {
            "cause": "Unknown pathogen or environmental stress.",
            "symptoms": "Visible discoloration or lesions.",
            "treatment": "Isolate plant. Consult local agricultural extension.",
            "prevention": "Maintain general hygiene."
        })

        return {
            "title": f"{'✅' if is_healthy else '⚠️'} {clean_label}",
            "status": "Healthy" if is_healthy else "Infected",
            "details": (
                f"🔬 **DIAGNOSIS:** {clean_label}\n"
                f"Confidence: {confidence * 100:.2f}%\n\n"
                f"📋 **SYMPTOMS:**\n{info['symptoms']}\n\n"
                f"💊 **TREATMENT:**\n{info['treatment']}\n\n"
                f"🛡️ **PREVENTION:**\n{info['prevention']}"
            )
        }

# --- 3. ROBUST DATABASE MANAGER (FIXED) ---
class DataManager:
    def __init__(self):
        self.filepath = DATA_FILE
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.filepath):
            self._save({"users": {}})
            self.register_user("admin", "admin")
        else:
            # Self-Repair: Check if file structure is valid
            try:
                data = self._load()
                if "users" not in data:
                    print("⚠️ Repairing database structure...")
                    # Migration: Wrap old data in 'users' key or reset
                    if "admin" in data: # It's the old format
                        new_data = {"users": data}
                        self._save(new_data)
                    else:
                        self._save({"users": {}})
            except:
                print("⚠️ Database corrupt. Resetting...")
                self._save({"users": {}})
                self.register_user("admin", "admin")

    def _load(self):
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except: return {"users": {}}

    def _save(self, data):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"DB Save Error: {e}")

    def _hash(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    # Auth
    def register_user(self, u, p):
        db = self._load()
        if u in db["users"]: return False, "Username taken"
        
        db["users"][u] = {
            "password": self._hash(p),
            "history": [],
            "inventory": []
        }
        self._save(db)
        return True, "Success"

    def verify_user(self, u, p):
        db = self._load()
        users = db.get("users", {})
        return u in users and users[u]["password"] == self._hash(p)

    # Inventory
    def add_item(self, user, name, category, qty, notes):
        db = self._load()
        if user in db["users"]:
            item = {
                "id": str(uuid.uuid4())[:8],
                "name": name,
                "category": category,
                "qty": qty,
                "notes": notes,
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            db["users"][user]["inventory"].insert(0, item)
            self._save(db)

    def get_inventory(self, user):
        return self._load().get("users", {}).get(user, {}).get("inventory", [])

    def delete_item(self, user, item_id):
        db = self._load()
        if user in db["users"]:
            inv = db["users"][user]["inventory"]
            db["users"][user]["inventory"] = [i for i in inv if i["id"] != item_id]
            self._save(db)

    def get_stats(self, user):
        inv = self.get_inventory(user)
        stats = {"Plant": 0, "Seed": 0, "Tool": 0, "Other": 0}
        for i in inv:
            cat = i.get("category", "Other")
            if cat in stats: stats[cat] += 1
            else: stats["Other"] += 1
        return stats

    # History
    def log_scan(self, user, img_path, report):
        db = self._load()
        if user in db["users"]:
            entry = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "file": os.path.basename(img_path),
                "result": report["title"],
                "status": report["status"]
            }
            db["users"][user]["history"].insert(0, entry)
            self._save(db)
    
    def get_history(self, user):
        return self._load().get("users", {}).get(user, {}).get("history", [])

# --- 4. AI ENGINE ---
class AI_Engine:
    def __init__(self):
        self.model = None
        self.classes = []
        self.is_ready = False
        self.mode = "standard"

    def load_resources(self, callback):
        global tf, hub, image_utils
        try:
            callback(0.1, "Initializing Core...")
            import tensorflow as tf_lib
            import tensorflow_hub as hub_lib
            from tensorflow.keras.preprocessing import image as img_utils
            tf, hub, image_utils = tf_lib, hub_lib, img_utils

            callback(0.3, "Loading Knowledge Base...")
            if os.path.exists(CLASSES_FILE):
                with open(CLASSES_FILE, "r") as f:
                    self.classes = [line.strip() for line in f.readlines()]
            else: self.classes = ["Unknown"]

            callback(0.5, "Loading Neural Network...")
            if not os.path.exists(MODEL_PATH): raise FileNotFoundError("Model missing")

            try:
                self.model = tf.keras.models.load_model(MODEL_PATH, custom_objects={'KerasLayer': hub.KerasLayer})
            except:
                self.model = tf.keras.layers.TFSMLayer(MODEL_PATH, call_endpoint='serving_default')
                self.mode = "layer"

            # WARM UP (Requires numpy)
            callback(0.8, "Warming up...")
            dummy = np.zeros((1, 224, 224, 3)) # <--- FIXED: np is now imported
            if self.mode == "layer": self.model(dummy)
            else: self.model.predict(dummy, verbose=0)

            callback(1.0, "Ready")
            self.is_ready = True
        except Exception as e:
            print(f"AI Fail: {e}")
            callback(1.0, "AI Failed")

    def predict(self, filepath):
        if not self.is_ready: return None
        try:
            img = image_utils.load_img(filepath, target_size=(224, 224))
            x = image_utils.img_to_array(img) / 255.0
            x = np.expand_dims(x, axis=0)

            if self.mode == "layer":
                res = self.model(x)
                probs = list(res.values())[0].numpy()[0]
            else:
                probs = self.model.predict(x, verbose=0)[0]

            idx = np.argmax(probs)
            label = self.classes[idx] if idx < len(self.classes) else f"Class {idx}"
            
            return KnowledgeBase.generate_report(label, np.max(probs))
        except Exception as e:
            print(e)
            return None

# --- 5. GUI ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self.db = DataManager()
        self.ai = AI_Engine()
        self.user = None

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.show_loading()

    def clear(self):
        for w in self.container.winfo_children(): w.destroy()

    # LOADING
    def show_loading(self):
        self.clear()
        f = ctk.CTkFrame(self.container, width=400, height=300, corner_radius=20)
        f.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(f, text="🌱", font=("Arial", 60)).pack(pady=(40,10))
        ctk.CTkLabel(f, text=APP_NAME, font=("Segoe UI", 28, "bold")).pack()
        self.status = ctk.CTkLabel(f, text="Initializing...", text_color="gray")
        self.status.pack(pady=5)
        self.pb = ctk.CTkProgressBar(f, width=300, progress_color=COLOR_ACCENT)
        self.pb.set(0)
        self.pb.pack(pady=30)
        threading.Thread(target=self._boot, daemon=True).start()

    def _boot(self):
        self.ai.load_resources(lambda v, m: (self.status.configure(text=m), self.pb.set(v)))
        time.sleep(0.5)
        self.after(0, self.show_login)

    # AUTH
    def show_login(self):
        self.clear()
        left = ctk.CTkFrame(self.container, width=500, corner_radius=0, fg_color="#151515")
        left.pack(side="left", fill="y")
        ctk.CTkLabel(left, text="🌾", font=("Arial", 120)).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(left, text="Smart Agriculture\nManager", font=("Segoe UI", 30, "bold")).place(relx=0.5, rely=0.6, anchor="center")

        right = ctk.CTkFrame(self.container, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)
        
        box = ctk.CTkFrame(right, width=400, height=500, corner_radius=20)
        box.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(box, text="Sign In", font=("Segoe UI", 30, "bold")).pack(pady=40)
        
        self.u_ent = ctk.CTkEntry(box, placeholder_text="Username", width=280, height=50)
        self.u_ent.pack(pady=10)
        self.p_ent = ctk.CTkEntry(box, placeholder_text="Password", show="•", width=280, height=50)
        self.p_ent.pack(pady=10)
        
        ctk.CTkButton(box, text="Login", width=280, height=50, fg_color=COLOR_ACCENT, font=("Segoe UI", 16, "bold"), command=self.login).pack(pady=20)
        ctk.CTkButton(box, text="Create Account", fg_color="transparent", command=self.reg_view).pack()

    def reg_view(self):
        self.clear()
        box = ctk.CTkFrame(self.container, width=400, height=500, corner_radius=20)
        box.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(box, text="New Account", font=("Segoe UI", 30, "bold")).pack(pady=40)
        self.ru = ctk.CTkEntry(box, placeholder_text="Username", width=280, height=50)
        self.ru.pack(pady=10)
        self.rp = ctk.CTkEntry(box, placeholder_text="Password", show="•", width=280, height=50)
        self.rp.pack(pady=10)
        ctk.CTkButton(box, text="Register", width=280, height=50, fg_color=COLOR_ACCENT, command=self.register).pack(pady=20)
        ctk.CTkButton(box, text="Back", fg_color="transparent", command=self.show_login).pack()

    def login(self):
        if self.db.verify_user(self.u_ent.get(), self.p_ent.get()):
            self.user = self.u_ent.get()
            self.dashboard()
        else: messagebox.showerror("Error", "Invalid Login")

    def register(self):
        if self.db.register_user(self.ru.get(), self.rp.get()):
            messagebox.showinfo("Success", "Registered!")
            self.show_login()
        else: messagebox.showerror("Error", "Username taken")

    # DASHBOARD
    def dashboard(self):
        self.clear()
        nav = ctk.CTkFrame(self.container, width=260, corner_radius=0)
        nav.pack(side="left", fill="y")
        ctk.CTkLabel(nav, text="Crop Manager", font=("Segoe UI", 24, "bold")).pack(pady=(40, 50))
        
        self.btns = {}
        for n, f in [("Disease Scan", self.view_scan), ("Inventory", self.view_inv), ("History", self.view_hist)]:
            b = ctk.CTkButton(nav, text=f"  {n}", height=55, fg_color="transparent", anchor="w", font=("Segoe UI", 16), command=f)
            b.pack(fill="x", padx=15, pady=5)
            self.btns[n] = b
            
        ctk.CTkLabel(nav, text=f"User: {self.user}", text_color="gray").pack(side="bottom", pady=10)
        ctk.CTkButton(nav, text="Sign Out", fg_color=COLOR_DANGER, command=self.show_login).pack(side="bottom", pady=30, padx=20, fill="x")
        
        self.main = ctk.CTkFrame(self.container, corner_radius=0, fg_color="transparent")
        self.main.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        self.view_scan()

    def set_nav(self, name):
        for k, v in self.btns.items(): v.configure(fg_color=COLOR_BG_CARD if k == name else "transparent")

    # TAB 1: SCANNER
    def view_scan(self):
        self.set_nav("Disease Scan")
        for w in self.main.winfo_children(): w.destroy()

        content = ctk.CTkFrame(self.main, fg_color="transparent")
        content.pack(fill="both", expand=True)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))

        ctk.CTkLabel(left, text="Image Analysis", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 20))
        self.img_lbl = ctk.CTkLabel(left, text="Upload Image", width=500, height=350, fg_color=COLOR_BG_CARD, corner_radius=15)
        self.img_lbl.pack(fill="x", pady=(0, 20))
        
        ctrls = ctk.CTkFrame(left, fg_color="transparent")
        ctrls.pack(fill="x")
        ctk.CTkButton(ctrls, text="Upload", width=150, height=45, command=self.upload).pack(side="left")
        self.btn_run = ctk.CTkButton(ctrls, text="Generate Report", width=150, height=45, state="disabled", fg_color=COLOR_ACCENT, command=self.run_ai)
        self.btn_run.pack(side="right")

        right = ctk.CTkFrame(content, width=400, fg_color=COLOR_BG_CARD, corner_radius=15)
        right.pack(side="right", fill="y", padx=(20, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="AI Insight Report", font=("Segoe UI", 20, "bold")).pack(pady=20)
        self.report_area = ctk.CTkTextbox(right, font=("Segoe UI", 14), wrap="word", fg_color="transparent")
        self.report_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.report_area.insert("0.0", "Waiting for analysis...\n\nUpload an image and click 'Generate Report' for details.")
        self.report_area.configure(state="disabled")

    def upload(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.jpg;*.png;*.jpeg")])
        if f:
            self.curr = f
            img = Image.open(f)
            img.thumbnail((500, 350))
            ci = ctk.CTkImage(img, size=img.size)
            self.img_lbl.configure(image=ci, text="")
            self.btn_run.configure(state="normal")

    def run_ai(self):
        self.report_area.configure(state="normal")
        self.report_area.delete("0.0", "end")
        self.report_area.insert("0.0", "🔄 Analyzing biological patterns...\nThis may take a moment.")
        self.update()
        
        report = self.ai.predict(self.curr)
        
        self.report_area.delete("0.0", "end")
        if report:
            self.report_area.insert("0.0", report["details"])
            self.db.log_scan(self.user, self.curr, report)
        else:
            self.report_area.insert("0.0", "❌ Analysis Failed.")
        
        self.report_area.configure(state="disabled")

    # TAB 2: INVENTORY
    def view_inv(self):
        self.set_nav("Inventory")
        for w in self.main.winfo_children(): w.destroy()
        
        head = ctk.CTkFrame(self.main, fg_color="transparent")
        head.pack(fill="x", pady=10)
        ctk.CTkLabel(head, text="Farm Inventory", font=("Segoe UI", 28, "bold")).pack(side="left")
        ctk.CTkButton(head, text="+ Add Item", fg_color=COLOR_ACCENT, command=self.add_pop).pack(side="right")

        stats = self.db.get_stats(self.user)
        sf = ctk.CTkFrame(self.main, height=80, fg_color=COLOR_BG_CARD)
        sf.pack(fill="x", pady=20)
        for cat, val in stats.items():
            f = ctk.CTkFrame(sf, fg_color="transparent")
            f.pack(side="left", fill="y", expand=True)
            ctk.CTkLabel(f, text=str(val), font=("Segoe UI", 24, "bold"), text_color=COLOR_ACCENT).pack()
            ctk.CTkLabel(f, text=cat, text_color="gray").pack()

        self.ilist = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        self.ilist.pack(fill="both", expand=True)
        self.load_inv()

    def load_inv(self):
        for w in self.ilist.winfo_children(): w.destroy()
        for i in self.db.get_inventory(self.user):
            r = ctk.CTkFrame(self.ilist, height=50, fg_color=COLOR_BG_CARD)
            r.pack(fill="x", pady=4)
            c_col = "#3498db" if i['category'] == "Seed" else COLOR_ACCENT if i['category'] == "Plant" else "gray"
            ctk.CTkLabel(r, text=i['category'], width=100, text_color=c_col).pack(side="left", padx=10)
            ctk.CTkLabel(r, text=i['name'], width=200, font=("Segoe UI", 14, "bold")).pack(side="left")
            ctk.CTkLabel(r, text=i['qty'], width=80).pack(side="left")
            ctk.CTkButton(r, text="×", width=30, fg_color=COLOR_DANGER, command=lambda x=i['id']: (self.db.delete_item(self.user, x), self.view_inv())).pack(side="right", padx=10)

    def add_pop(self):
        t = ctk.CTkToplevel(self)
        t.geometry("400x500")
        t.title("Add Item")
        t.transient(self)
        t.grab_set()
        ctk.CTkLabel(t, text="New Item", font=("Segoe UI", 20, "bold")).pack(pady=20)
        
        c = ctk.StringVar(value="Plant")
        ctk.CTkSegmentedButton(t, values=["Plant", "Seed", "Tool", "Fertilizer"], variable=c).pack(pady=10)
        
        n = ctk.CTkEntry(t, placeholder_text="Name")
        n.pack(pady=10, padx=40, fill="x")
        q = ctk.CTkEntry(t, placeholder_text="Quantity")
        q.pack(pady=10, padx=40, fill="x")
        nt = ctk.CTkEntry(t, placeholder_text="Notes")
        nt.pack(pady=10, padx=40, fill="x")
        
        def save():
            if n.get(): 
                self.db.add_item(self.user, n.get(), c.get(), q.get(), nt.get())
                self.view_inv()
                t.destroy()
        
        ctk.CTkButton(t, text="Save", fg_color=COLOR_ACCENT, command=save).pack(pady=30)

    # TAB 3: HISTORY
    def view_hist(self):
        self.set_nav("History")
        for w in self.main.winfo_children(): w.destroy()
        ctk.CTkLabel(self.main, text="Scan Logs", font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=20)
        sf = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        sf.pack(fill="both", expand=True)
        
        for l in self.db.get_history(self.user):
            r = ctk.CTkFrame(sf, height=60, fg_color=COLOR_BG_CARD)
            r.pack(fill="x", pady=5)
            ctk.CTkLabel(r, text=l['date'], width=120, text_color="gray").pack(side="left", padx=10)
            col = COLOR_ACCENT if "Healthy" in l['status'] else COLOR_DANGER
            ctk.CTkLabel(r, text=l['status'], width=100, text_color=col, font=("Segoe UI", 12, "bold")).pack(side="left")
            ctk.CTkLabel(r, text=l['result'].replace("✅ ", "").replace("⚠️ ", ""), font=("Segoe UI", 14)).pack(side="left", padx=10)

if __name__ == "__main__":
    app = App()
    app.mainloop()
