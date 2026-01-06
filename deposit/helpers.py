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

def select_item_from_dropdown_list(window, combo_id, target_text):
    """
    ฟังก์ชันเลือก Dropdown: กดกล่องให้กาง -> เลื่อนหา -> กดเลือก
    - combo_id: ID ของกล่อง ComboBox (เช่น 'SelectedSubList')
    - target_text: ข้อความที่ต้องการเลือก
    """
    log(f"...กำลังจัดการ Dropdown ID: '{combo_id}' เลือก: '{target_text}'...")

    # 1. หาตัวกล่อง ComboBox และกดเพื่อให้รายการกางออก
    combo_box = None
    # หาจาก ID ที่ระบุ
    candidates = [c for c in window.descendants() if c.element_info.automation_id == combo_id and c.is_visible()]
    if candidates:
        combo_box = candidates[0]
        # กดที่ตัวกล่อง 1 ครั้งเพื่อกางรายการ
        log(f"   [/] เจอ ComboBox -> กดเพื่อกางรายการ")
        combo_box.click_input()
        time.sleep(1.5) # รอให้รายการเด้งออกมา (Animation)
    else:
        log(f"[WARN] หา ComboBox ID '{combo_id}' ไม่เจอ")
        return False

    # 2. วนลูปหา 'ListItem' ที่มีชื่อที่เราต้องการ
    # (เราหาจาก window.descendants() เลย เพราะรายการที่เด้งมามักจะเป็น Popup ลอยอยู่เหนือสุด)
    for i in range(15): # ลองเลื่อนหา 15 รอบ
        try:
            found_item = None
            # ค้นหาเฉพาะ Control Type ที่เป็น ListItem หรือ Text
            # เทคนิค: หาจากข้อความ target_text ตรงๆ เลยจะเร็วกว่า
            for child in window.descendants():
                # เช็คว่ามองเห็นและมีชื่อตรงกับเป้าหมาย
                if child.is_visible() and target_text in child.window_text():
                    found_item = child
                    break
            
            if found_item:
                log(f"   [/] เจอรายการ '{target_text}' -> คลิกเลือก")
                found_item.set_focus()
                found_item.click_input()
                return True
            else:
                # ถ้ายังไม่เจอ ให้ส่งปุ่ม PageDown ไปที่หน้าจอเพื่อเลื่อนลง
                # (ส่งไปที่ window หลัก เพราะโฟกัสอยู่ที่รายการแล้ว)
                log(f"   [...] ไม่เจอในหน้านี้ -> เลื่อนลง (รอบที่ {i+1})")
                window.type_keys("{PGDN}") 
                time.sleep(0.8)
        except Exception as e:
            log(f"[!] Error ขณะเลื่อนหา: {e}")
            break
            
    log(f"[X] หาไม่เจอ หรือ เลื่อนจนสุดแล้ว")
    return False