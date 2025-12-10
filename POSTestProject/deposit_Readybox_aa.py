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

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    """ฟังก์ชันช่วยเลื่อนหน้าจอลง"""
    log(f"...กำลังเลื่อนหน้าจอลง ({scroll_dist})...")
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except Exception as e:
        log(f"[!] Scroll failed: {e}")
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            child.click_input()
                            log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                            return True
                        except:
                            child.click_input(double=True)
                            log(f"[/] Double Click '{criteria}'")
                            return True
            except: pass
        time.sleep(0.5)

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def smart_input_weight(window, value):
    """กรอกน้ำหนัก"""
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอกน้ำหนัก '{value}' สำเร็จ")
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    """กรอกข้อมูลแบบเลื่อนหา (สำหรับเบอร์โทร/ปณ)"""
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    for i in range(scroll_times + 1):
        try:
            # 1. หา Edit Box โดยตรง
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    log(f"[/] กรอก {label_text} สำเร็จ")
                    return True
            
            # 2. หา Label แล้วกด Tab
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass

        if i < scroll_times:
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)
    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def wait_for_text(window, text, timeout=5):
    """รอข้อความปรากฏ (ใช้เช็คหน้าสิ่งของต้องห้าม)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

# ================= 3. Business Logic Functions =================

def process_sender_info(window, phone_number, default_postal):
    """จัดการหน้าผู้ฝากส่ง (อ่านบัตร -> เช็ค ปณ. -> กรอกเบอร์)"""
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตร")
        time.sleep(3) 

        # --- ตรวจสอบและเติมรหัสไปรษณีย์ ---
        try:
            found_postal = False
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    current_val = edit.get_value() 
                    if current_val is None or str(current_val).strip() == "":
                        log(f"   [Auto-Fix] เติม ปณ. {default_postal}")
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    found_postal = True
                    break
        except Exception as e:
            log(f"   [Error] Check Postal: {e}")

        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง (ข้าม)")

def handle_prohibited_items_warning(window):
    """
    [NEW] ฟังก์ชันจัดการหน้า 'สิ่งของต้องห้าม'
    ตรวจสอบว่ามีข้อความเตือนหรือไม่ ถ้ามีให้กด 'ยืนยัน'
    """
    log("...ตรวจสอบการแจ้งเตือนสิ่งของต้องห้าม...")
    
    # รอเช็คว่ามีคำว่า "สิ่งของต้องห้าม" หรือ "Confirm" โผล่มาไหม
    if wait_for_text(window, "สิ่งของต้องห้าม", timeout=3):
        log("[Detect] พบหน้าแจ้งเตือนสิ่งของต้องห้าม!")
        time.sleep(0.5)
        
        # พยายามกดปุ่มยืนยัน
        if smart_click(window, "ยืนยัน", timeout=3):
            log("[/] กดปุ่ม 'ยืนยัน' เรียบร้อย")
        else:
            log("[!] เจอหน้าเตือน แต่หาปุ่มยืนยันไม่เจอ (ลองกด Enter)")
            window.type_keys("{ENTER}")
    else:
        log("[Skip] ไม่พบหน้าแจ้งเตือนสิ่งของต้องห้าม (ไปต่อ)")

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: return

    log(f"\n--- เริ่มต้น Scenario ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ผู้ฝากส่ง
    process_sender_info(main_window, phone, postal)
    time.sleep(step_delay)

    # 3. เลือกประเภทสิ่งของ (เช่น ซอง A4)
    if not smart_click(main_window, "ซอง A4 เอกสาร"): return
    time.sleep(step_delay)

    # 4. เลือก Options พิเศษ
    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        log(f"...เลือกรายการพิเศษ: {options}")
        for opt in options:
            if opt: 
                smart_click(main_window, opt, timeout=2, optional=True)
                time.sleep(0.5)

    log("...กด Enter เพื่อไปหน้าถัดไป")
    main_window.type_keys("{ENTER}")
    time.sleep(1) # รอการเปลี่ยนหน้าสักครู่

    # =========================================================
    # [NEW STEP] ดักหน้า "สิ่งของต้องห้าม" ตรงนี้ ก่อนเข้าหน้าน้ำหนัก
    # =========================================================
    handle_prohibited_items_warning(main_window)
    time.sleep(step_delay)
    # =========================================================

    # 5. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    wait_for_text(main_window, "รหัสไปรษณีย์")
    time.sleep(0.5) 

    # 6. รหัสไปรษณีย์ปลายทาง
    try:
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(postal))
        else:
            main_window.type_keys(str(postal), with_spaces=True)
    except:
        main_window.type_keys(str(postal), with_spaces=True)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # 7. จบงาน
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' สำเร็จ")
    
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=3, optional=True)
    main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")

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