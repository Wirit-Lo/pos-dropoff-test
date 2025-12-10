import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): 
        # Create Dummy config if not exists for testing
        return {'DEPOSIT_ENVELOPE': {}, 'TEST_DATA': {}, 'SETTINGS': {}, 'APP': {'WindowTitle': 'Riposte POS Application'}} 
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def debug_ui_structure(window):
    """
    [NEW] ฟังก์ชันช่วย Debug รายงาน ID และคุณสมบัติของปุ่มแบบละเอียด
    """
    log("\n!!! DEBUG: รายงานโครงสร้างหน้าจอ (UI Report - Full IDs) !!!")
    try:
        # ดึง Element ทั้งหมดที่มองเห็น
        elements = window.descendants()
        
        found_count = 0
        for i, item in enumerate(elements):
            try:
                if item.is_visible():
                    ctype = item.element_info.control_type
                    
                    # กรองเฉพาะ Control ที่น่าจะเป็นปุ่มหรือเมนู
                    if ctype in ["Button", "ListItem", "Image", "Text", "Group", "Pane", "Custom"]:
                        rect = item.rectangle()
                        txt = item.window_text()
                        auto_id = item.element_info.automation_id
                        name = item.element_info.name
                        
                        # เงื่อนไขการแสดงผล: ต้องมี ID หรือ มีข้อความ หรือเป็นปุ่ม
                        if (auto_id or txt.strip() or ctype in ["Button", "ListItem"]) and rect.width() > 0:
                            found_count += 1
                            log(f"   [{ctype}] Text:'{txt}' | ID:'{auto_id}' | Name:'{name}' | Size:{rect.width()}x{rect.height()}")
            except: pass
        
        log(f"-> สแกนเสร็จสิ้น พบ {found_count} รายการที่น่าสนใจ")

    except Exception as e:
        log(f"Debug Error: {e}")
    log("------------------------------------------\n")

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except: pass

def smart_click(window, criteria_list, timeout=5, optional=False):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.5)
    
    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value):
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    for i in range(scroll_times + 1):
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    return True
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass
        if i < scroll_times:
            force_scroll_down(window)
    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง")
        time.sleep(1)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้าม")

def wait_for_text(window, text, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except:
        weight, postal, special_options_str, phone, step_delay = '10', '10110', '', '0812345678', 1

    log(f"\n--- เริ่มต้น Scenario ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # ผู้ฝากส่ง
    process_sender_info(main_window, phone)
    time.sleep(step_delay)

    # 2. ซองจดหมาย
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. เลือกหมวดหมู่
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            smart_click(main_window, opt.strip(), timeout=2, optional=True)
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    wait_for_text(main_window, "รหัสไปรษณีย์")

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    main_window.type_keys(str(postal), with_spaces=True)
    smart_next(main_window)
    time.sleep(2)

    # Check Popup ทับซ้อน
    if smart_click(main_window, "ดำเนินการ", timeout=2, optional=True):
        time.sleep(1)
    else:
        main_window.type_keys("{ENTER}")

    # ================= [STEP 6: เลือกบริการ (DEBUG MODE)] =================
    log("STEP 6: เลือกบริการ (ตรวจสอบ ID)")
    
    log("...รอหน้าจอ 'บริการหลัก'...")
    if wait_for_text(main_window, "บริการหลัก", timeout=15):
        log("[/] หน้าจอพร้อมแล้ว (รออีก 2 วินาที)")
        time.sleep(2)
        
        # ลองกด E ดูก่อน
        log("...ลองกด E...")
        main_window.set_focus()
        main_window.type_keys("E")
        time.sleep(2)

        if not wait_for_text(main_window, "บริการหลัก", timeout=1):
             log("[SUCCESS] กด E ผ่านแล้ว (หน้าจอเปลี่ยน)")
             main_window.type_keys("0")
        else:
             log("\n[FAIL] กด E ไม่ผ่าน -> เริ่มสร้าง Report เพื่อหา ID ปุ่ม...")
             
             # เรียกฟังก์ชัน Debug เพื่อดู ID
             debug_ui_structure(main_window)
             
             log("[!!! PAUSED !!!] หยุดค้างหน้าจอเพื่อให้ตรวจสอบ Log ด้านบน")
             while True: time.sleep(5)
    else:
        log("[!] Timeout: หาหน้าบริการหลักไม่เจอ")
        debug_ui_structure(main_window)
        while True: time.sleep(5)
            
    log("--- จบการทำงาน ---")
    return

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            # [FIXED] เพิ่ม found_index=0 เพื่อแก้ปัญหาเจอ 2 หน้าต่าง
            app = Application(backend="uia").connect(title_re=".*POS.*", found_index=0, timeout=15)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")