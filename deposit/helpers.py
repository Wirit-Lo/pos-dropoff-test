# ไฟล์: helpers.py
import time
from pywinauto import mouse

# --- ส่วน Log ---
def log(message):
    import datetime
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# --- ส่วน Wait & Check ---
def wait_for_text(window, text_list, timeout=10):
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible(): return True
        except: pass
        time.sleep(0.5)
    return False

def wait_until_id_appears(window, exact_id, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(1)
    return False

# --- ส่วน Click & Fill ---
def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text().strip():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.3)
    return False

def click_element_by_id(window, exact_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if found:
                found[0].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except: pass
        time.sleep(0.5)
    return False

def find_and_fill_smart(window, target_name, target_id_keyword, value, timeout=15):
    if not value or str(value).strip() == "": return False
    log(f"...รอช่อง '{target_name}' (Max {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            target_elem = None
            for child in window.descendants():
                if not child.is_visible(): continue
                aid, name = child.element_info.automation_id, child.element_info.name
                if target_name and name and target_name in name: target_elem = child; break
                if target_id_keyword and aid and target_id_keyword in aid: target_elem = child; break
            
            if target_elem:
                try: 
                    edits = target_elem.descendants(control_type="Edit")
                    if edits: target_elem = edits[0]
                except: pass
                target_elem.set_focus(); target_elem.click_input(); time.sleep(0.5)
                target_elem.type_keys(str(value), with_spaces=True)
                log(f"   [/] กรอก '{target_name}' เรียบร้อย")
                return True
        except: pass
        time.sleep(0.5)
    log(f"[WARN] หาช่อง '{target_name}' ไม่เจอ")
    return False

def smart_next(window):
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป'")
    else:
        window.type_keys("{ENTER}")

# --- ฟังก์ชันเฉพาะทาง ---
def click_toggle_inside_parent(window, parent_id):
    parents = [c for c in window.descendants() if c.element_info.automation_id == parent_id]
    if parents:
        thumbs = [c for c in parents[0].descendants() if c.element_info.automation_id == "SwitchThumb"]
        if thumbs: thumbs[0].click_input(); return True
    return False