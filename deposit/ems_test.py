import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def debug_dump_ui(window):
    log("!!! หาไม่เจอ -> กำลังลิสต์ข้อความ (Debug) !!!")
    try:
        visible_texts = []
        for child in window.descendants():
            if child.is_visible():
                txt = child.window_text().strip()
                if txt: visible_texts.append(txt)
        log(f"Text ที่เจอ: {list(set(visible_texts))}")
    except: pass

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        window.set_focus()
        rect = window.rectangle()
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.2)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.8) 
    except: pass

def smart_click(window, criteria_list, timeout=5, optional=False):
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
    if not optional: log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    log(f"...ค้นหา '{criteria}' (Scroll Mode)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found = child
                    break
        except: pass

        if found:
            try:
                elem_rect = found.rectangle()
                win_rect = window.rectangle()
                if elem_rect.bottom >= win_rect.bottom - 70:
                    force_scroll_down(window, -3)
                    time.sleep(0.5)
                    continue 
                found.click_input()
                log(f"   [/] เจอและกด '{criteria}' สำเร็จ")
                return True
            except: pass
        
        if i < max_scrolls:
            force_scroll_down(window, scroll_dist)
            
    log(f"[X] หมดความพยายามหา '{criteria}'")
    return False

# [NEW] ฟังก์ชันกดปุ่มด้วย ID (แม่นยำที่สุด)
def click_element_by_id(window, auto_id, timeout=5):
    log(f"...พยายามกดปุ่มด้วย ID: '{auto_id}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            # ค้นหา Element ที่มี AutomationId ตรงเป๊ะๆ
            for child in window.descendants():
                if child.element_info.automation_id == auto_id and child.is_visible():
                    child.click_input()
                    log(f"[/] กดปุ่ม ID '{auto_id}' สำเร็จ!")
                    return True
        except: pass
        time.sleep(0.5)
    
    log(f"[X] หาปุ่ม ID '{auto_id}' ไม่เจอ")
    return False

def wait_until_id_appears(window, auto_id, timeout=10):
    log(f"...รอโหลดหน้าจอ (รอ ID: {auto_id})...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == auto_id and child.is_visible():
                    log(f"[/] หน้าจอพร้อมแล้ว (เจอ {auto_id})")
                    return True
        except: pass
        time.sleep(1)
    return False

# ================= 3. Input Helpers =================
def smart_input_weight(window, value):
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number, default_postal):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3, optional=True): 
        time.sleep(2) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    if not edit.get_value():
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    break 
        except: pass
        
        # กรอกเบอร์โทร (แบบ Scroll หา)
        found_phone = False
        for i in range(3):
            try:
                edits = window.descendants(control_type="Edit")
                for edit in edits:
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input()
                        edit.type_keys(str(phone_number), with_spaces=True)
                        found_phone = True
                        break
            except: pass
            if found_phone: break
            force_scroll_down(window, -5)
            
        smart_next(window)

def handle_prohibited_items(window):
    # ใช้ wait loop สั้นๆ เช็คหน้าสิ่งของต้องห้าม
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}")
                    return
        except: pass
        time.sleep(0.5)

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.5))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
    except: return

    log(f"--- เริ่มต้น ---")
    time.sleep(0.5)

    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)

    if special_options_str.strip():
        for opt in special_options_str.split(','):
            if opt: smart_click(main_window, opt.strip(), timeout=1, optional=True)
    
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    handle_prohibited_items(main_window)
    
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    # รอหน้ากรอก ปณ. ปลายทาง
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)

    # ตรวจสอบ Popup ทับซ้อน
    log("...ตรวจสอบ Popup หลังใส่รหัส ปณ...")
    for _ in range(3):
        found_popup = False
        for child in main_window.descendants():
            txt = child.window_text()
            if "ทับซ้อน" in txt or "พื้นที่" in txt:
                log("[Popup] พบแจ้งเตือน -> กด 'ดำเนินการ'")
                smart_click(main_window, "ดำเนินการ", timeout=2)
                found_popup = True
                break
        if found_popup: break
        time.sleep(0.5)

    # --- เข้าสู่ขั้นตอนเลือก EMS ---
    log("...กำลังไปที่หน้าบริการหลัก...")
    
    # 1. รอให้ปุ่ม EMS โผล่มา (เช็คจาก ID)
    wait_until_id_appears(main_window, "ShippingService_EMSS", timeout=10)

    # 2. กดปุ่ม EMS ด้วย ID (ชัวร์ที่สุด)
    if click_element_by_id(main_window, "ShippingService_EMSS"):
        log("[SUCCESS] เลือกบริการ EMS เรียบร้อย")
    else:
        # Fallback: ถ้า ID เปลี่ยน หรือหาไม่เจอ ลองหาคำว่า "บริการ" แทน
        log("[!] ไม่เจอ ID ลองหาคำว่า 'อีเอ็มเอส' แทน")
        smart_click_with_scroll(main_window, "อีเอ็มเอส")

    log("\n[SUCCESS] จบการทำงาน")
    print(">>> กด Enter เพื่อปิดโปรแกรม... <<<")
    input()

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")