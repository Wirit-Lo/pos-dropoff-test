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

# --- วางต่อท้ายไฟล์ helpers.py ---

def click_scroll_arrow_smart(window, direction='right', repeat=5):
    """ใช้ช่วยเลื่อนหน้าจอในฟังก์ชัน Rotate Logic"""
    try:
        target_group = [c for c in window.descendants() if c.element_info.automation_id == "ShippingServiceList"]
        if target_group: target_group[0].set_focus()
        else: window.set_focus()
        
        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        window.type_keys(key_code * repeat, pause=0.2, set_foreground=False)
        return True
    except: return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    """(สำคัญ) ใช้หาปุ่มบริการ 'ธนาณัติธรรมดา' ที่อาจหลบอยู่"""
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False
        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            if rect.right < safe_limit:
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else: should_scroll = True
        else: should_scroll = True
        
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5): window.type_keys("{RIGHT}")
            time.sleep(1.0)
    log(f"[X] หาปุ่มไม่เจอ: {target_id}")
    return False

# --- วางต่อท้ายใน helpers.py ---

def select_item_from_dropdown_list(window, list_id, target_text):
    """
    ฟังก์ชันสำหรับเลือกรายการใน Dropdown ที่ต้องเลื่อนหา
    - list_id: ID ของตัวกล่องรายการ (เช่น 'SelectedSubList')
    - target_text: ข้อความที่ต้องการเลือก
    """
    log(f"...กำลังค้นหา '{target_text}' ในลิสต์ '{list_id}'...")
    
    # 1. รอให้กล่องรายการเด้งขึ้นมา
    if not wait_until_id_appears(window, list_id, timeout=5):
        log(f"[WARN] ไม่พบกล่องรายการ ID: {list_id}")
        return False

    # 2. จับตัวกล่องรายการเพื่อส่งคำสั่ง Scroll
    list_container = None
    # หาตัวที่มี ID ตรงและมองเห็น
    candidates = [c for c in window.descendants() if c.element_info.automation_id == list_id and c.is_visible()]
    if candidates:
        list_container = candidates[0]
    else:
        return False

    # 3. วนลูปหาข้อความ (เลื่อนลงไปเรื่อยๆ)
    for i in range(15): # ลองเลื่อนหา 15 รอบ
        try:
            # หา ListItem หรือ Text ที่มีคำที่ต้องการ
            for item in list_container.descendants():
                if target_text in item.window_text():
                    log(f"   [/] เจอรายการ '{item.window_text()}' -> คลิก")
                    item.click_input()
                    return True
            
            # ถ้ายังไม่เจอ ให้ส่งปุ่ม PageDown เพื่อเลื่อนลง
            list_container.type_keys("{PGDN}") 
            time.sleep(0.5)
        except: 
            break
            
    log(f"[X] หารายการ '{target_text}' ไม่เจอ")
    return False