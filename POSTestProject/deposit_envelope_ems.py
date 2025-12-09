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
    [NEW] ฟังก์ชันช่วย Debug รายงานปุ่มบนหน้าจอ
    """
    log("!!! DEBUG: รายงานโครงสร้างหน้าจอ (UI Report) !!!")
    try:
        # สแกนหา ListItem และ Button
        elements = window.descendants(control_type="ListItem") + window.descendants(control_type="Button")
        
        log(f"-> พบ Element ทั้งหมด {len(elements)} รายการ (คัดเฉพาะที่มองเห็น):")
        visible_elements = []
        
        for i, item in enumerate(elements):
            if item.is_visible():
                rect = item.rectangle()
                area = rect.width() * rect.height()
                txt = item.window_text()
                # เก็บข้อมูลไว้เรียงลำดับ
                visible_elements.append({
                    'index': i,
                    'text': txt,
                    'width': rect.width(),
                    'height': rect.height(),
                    'area': area,
                    'item': item
                })
        
        # แสดงผลโดยเรียงจากขนาดใหญ่ไปเล็ก (เพื่อให้เห็นปุ่ม EMS ที่น่าจะใหญ่สุดก่อน)
        visible_elements.sort(key=lambda x: x['area'], reverse=True)
        
        for e in visible_elements[:10]: # แสดง 10 อันดับแรก
            log(f"   [Size: {e['width']}x{e['height']}] Text: '{e['text']}'")
            
        return visible_elements # ส่งกลับไปใช้ต่อได้

    except Exception as e:
        log(f"Debug Error: {e}")
        return []
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

def click_button_containing_text(window, search_texts):
    """
    [NEW] ค้นหาข้อความ แล้วย้อนหาปุ่มแม่ (Parent Button/ListItem) เพื่อคลิก
    วิธีนี้แม่นยำกว่าการกดที่ข้อความตรงๆ หรือกดตามขนาด
    """
    if isinstance(search_texts, str): search_texts = [search_texts]
    log(f"...กำลังค้นหาปุ่มที่มีข้อความ: {search_texts}...")

    try:
        # ดึงทุก Element ออกมาสแกน (อาจจะเยอะหน่อยแต่มั่นใจ)
        all_elements = window.descendants()
        
        for text_keyword in search_texts:
            for child in all_elements:
                try:
                    # ตรวจสอบว่ามองเห็นและมีข้อความตรงกับที่เราหาไหม
                    if child.is_visible() and text_keyword in child.window_text():
                        log(f"   -> เจอข้อความ '{child.window_text()}' (Type: {child.element_info.control_type})")
                        
                        # Case 1: ตัวมันเองเป็นปุ่มอยู่แล้ว -> กดเลย
                        if child.element_info.control_type in ["Button", "ListItem"]:
                            log(f"[/] ตัว Element เป็นปุ่มอยู่แล้ว -> คลิกเลย")
                            child.click_input()
                            return True
                        
                        # Case 2: มันเป็น Text หรือ Image -> ให้ไต่ระดับขึ้นไปหาพ่อ (Parent) ที่เป็นปุ่ม
                        parent = child.parent()
                        attempts = 0
                        while parent and attempts < 3: # ลองหาขึ้นไป 3 ชั้น
                            ctype = parent.element_info.control_type
                            if ctype in ["Button", "ListItem", "Group"]: # เจอพ่อที่เป็นปุ่ม
                                log(f"[/] เจอ Parent เป็น {ctype} -> คลิกที่ Parent")
                                parent.click_input()
                                return True
                            
                            parent = parent.parent()
                            attempts += 1
                        
                        # Case 3: หาพ่อไม่เจอ -> คลิกที่ข้อความนั้นตรงๆ (Fallback)
                        log(f"[/] ไม่เจอ Parent ที่เป็นปุ่ม -> คลิกที่ข้อความโดยตรง")
                        child.click_input()
                        return True
                except: continue
                
    except Exception as e:
        log(f"Error in click_button_containing_text: {e}")
    
    log(f"[X] ไม่พบปุ่มที่มีข้อความ {search_texts}")
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

    # ================= [STEP 6: เลือกบริการ (KEYBOARD MODE)] =================
    log("STEP 6: เลือกบริการ (Keyboard Mode: Press E)")
    
    # 1. รอให้เข้าหน้า 'บริการหลัก' ชัวร์ๆ ก่อน (ตามที่ขอ)
    log("...รอตรวจสอบหน้า 'บริการหลัก'...")
    # รอได้สูงสุด 15 วินาที เพื่อให้แน่ใจว่าหน้าโหลดเสร็จจริง
    if wait_for_text(main_window, "บริการหลัก", timeout=15):
        log("[/] ตรวจพบหน้า 'บริการหลัก' เรียบร้อย")
        # เพิ่ม Wait อีกนิดเพื่อให้ UI พร้อมรับ Input จริงๆ
        log("...รอ UI พร้อม (2 วินาที)...")
        time.sleep(2)
        
        # 2. กดคีย์บอร์ด E
        log("...กดปุ่ม 'E' เพื่อเลือก EMS...")
        main_window.set_focus() # บังคับ Focus หน้าจอก่อนกด
        main_window.type_keys("E")
        time.sleep(2)

        # 3. ตรวจสอบผลลัพธ์
        # ถ้าหน้าจอยังมีคำว่า "บริการหลัก" แสดงว่ายังไม่ไป
        if not wait_for_text(main_window, "บริการหลัก", timeout=1):
            log("[SUCCESS] หน้าจอเปลี่ยนแล้ว (ผ่าน Step 6)")
            time.sleep(1)
            log("...กด 0 เพื่อยืนยัน...")
            main_window.type_keys("0")
        else:
            log("[WARN] กด E แล้วยังอยู่หน้าเดิม -> ลองกด Enter ย้ำ")
            main_window.type_keys("{ENTER}")
            time.sleep(1)
            
            if not wait_for_text(main_window, "บริการหลัก", timeout=1):
                 log("[SUCCESS] หน้าจอเปลี่ยนแล้วหลังกด Enter")
                 main_window.type_keys("0")
            else:
                 log("[FAIL] กด E ไม่ทำงาน (ติดอยู่ที่หน้าบริการหลัก)")
                 debug_ui_structure(main_window)
                 while True: time.sleep(5)
    else:
        log("[!] ไม่เจอหน้า 'บริการหลัก' (Timeout) - หยุดทำงาน")
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
            app = Application(backend="uia").connect(title_re=".*POS.*", timeout=15)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")