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
    [NEW] ฟังก์ชันช่วย Debug ดูว่าหน้าจอมี Element อะไรบ้าง
    """
    log("!!! DEBUG UI STRUCTURE !!!")
    log("...กำลังสแกนหน้าจอเพื่อหาปุ่มที่กดได้...")
    try:
        # ลองหา ListItem ก่อน
        items = window.descendants(control_type="ListItem")
        if items:
            log(f"-> เจอ ListItem ทั้งหมด {len(items)} รายการ:")
            for i, item in enumerate(items):
                # พยายามดึงข้อมูลให้มากที่สุด
                txt = item.window_text()
                rect = item.rectangle()
                log(f"   [{i}] Text: '{txt}', Size: {rect.width()}x{rect.height()}, Visible: {item.is_visible()}")
        
        # ลองหา Button
        buttons = window.descendants(control_type="Button")
        if buttons:
            log(f"-> เจอ Button ทั้งหมด {len(buttons)} ปุ่ม (แสดง 5 ปุ่มแรก):")
            for i, btn in enumerate(buttons[:5]):
                txt = btn.window_text()
                rect = btn.rectangle()
                log(f"   [{i}] Text: '{txt}', Size: {rect.width()}x{rect.height()}")

    except Exception as e:
        log(f"Debug Error: {e}")
    log("------------------------------------------")

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

def smart_click_by_text_location(window, target_text, y_offset=0):
    log(f"...พยายามหา Text: '{target_text}' เพื่อคลิก...")
    try:
        text_elements = window.descendants(control_type="Text")
        for txt in text_elements:
            if target_text in txt.window_text() and txt.is_visible():
                rect = txt.rectangle()
                click_x = rect.mid_point().x
                click_y = rect.mid_point().y + y_offset
                log(f"[/] เจอข้อความ '{target_text}' -> คลิกที่พิกัด ({click_x}, {click_y})")
                mouse.click(button='left', coords=(click_x, click_y))
                return True
    except: pass
    return False

def click_first_list_item(window):
    """
    [NEW] คลิก ListItem ตัวแรกที่เจอ (โดยไม่สน Text)
    เพราะปกติเมนู EMS จะเป็น ListItem อันแรกเสมอ
    """
    log("...พยายามหา ListItem ตัวแรก (ไม่ต้องพึ่งพิกัดหน้าจอ)...")
    try:
        list_items = window.descendants(control_type="ListItem")
        # กรองเฉพาะอันที่มีขนาดใหญ่หน่อย (ป้องกันไปกดโดน list เล็กๆ ที่มองไม่เห็น)
        valid_items = [item for item in list_items if item.rectangle().width() > 50 and item.rectangle().height() > 50]
        
        if valid_items:
            # เรียงตามตำแหน่ง (ซ้ายไปขวา, บนลงล่าง)
            # valid_items.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
            
            target = valid_items[0] # เอาอันแรกสุด
            log(f"[/] เจอ ListItem {len(valid_items)} รายการ -> คลิกรายการแรก (ขนาด {target.rectangle().width()}x{target.rectangle().height()})")
            target.click_input()
            return True
        else:
            log("[!] ไม่เจอ ListItem ที่มีขนาดใหญ่พอ")
            # ถ้าไม่เจอ ListItem ลองหา Custom ที่ขนาดใหญ่
            log("...ลองหา Custom Element ขนาดใหญ่แทน...")
            customs = window.descendants(control_type="Custom")
            valid_customs = [c for c in customs if c.rectangle().width() > 100 and c.rectangle().height() > 100]
            if valid_customs:
                log(f"[/] เจอ Custom Element ใหญ่ -> คลิกอันแรก")
                valid_customs[0].click_input()
                return True

    except Exception as e:
        log(f"Error clicking list item: {e}")
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
        # add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False').lower() == 'true'
        # insurance_amount = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except:
        weight, postal, special_options_str, phone, step_delay = '10', '10110', '', '0812345678', 1

    log(f"\n--- เริ่มต้น Scenario (Focus STEP 6) ---")
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

    # ================= [STEP 6: เลือกบริการ] =================
    log("STEP 6: เลือกบริการ (Testing Mode)")
    
    # 1. รอหน้าจอ (ลดความเข้มงวดลง เผื่อ text หาไม่เจอ)
    log("...รอหน้าจอ 2 วินาที...")
    time.sleep(2)
    
    # 2. ลองปริ้นท์ structure ดูก่อนว่ามีอะไรบ้าง (ถ้ากดไม่ได้เราจะใช้ log นี้แก้ต่อ)
    # debug_ui_structure(main_window) # <--- เปิดบรรทัดนี้ถ้าอยากเห็น Log Element ทั้งหมด
    
    success = False

    # วิธีที่ 1: หา ListItem ตัวแรก (น่าจะเป็น EMS) - **แนะนำสุด**
    if not success:
        success = click_first_list_item(main_window)

    # วิธีที่ 2: หา Text แล้วคลิก
    if not success:
        success = smart_click_by_text_location(main_window, "บริการอีเอ็มเอส", y_offset=40)

    # วิธีที่ 3: หา Text "EMS"
    if not success:
        success = smart_click_by_text_location(main_window, "EMS", y_offset=0)
    
    if success:
        log("[SUCCESS] กดเลือกบริการได้แล้ว (ผ่าน STEP 6)")
        time.sleep(1)
        log("...กด 0 เพื่อยืนยัน (ถ้ามี)...")
        main_window.type_keys("0")
    else:
        log("[FAIL] ยังกดเลือกบริการไม่ได้ -> แสดงโครงสร้างหน้าจอเพื่อ Debug")
        debug_ui_structure(main_window)
    
    log("--- จบการทำงาน (ตามที่ขอให้หยุดหลังเลือกบริการ) ---")
    return

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            app = Application(backend="uia").connect(title_re=".*POS.*", timeout=15)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")