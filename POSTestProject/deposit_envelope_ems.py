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

def click_largest_element(window):
    """
    [NEW] คลิก Element ที่มีขนาดใหญ่ที่สุดบนหน้าจอ (แก้ไขปัญหาไปกดโดนปุ่ม Back เล็กๆ)
    """
    log("...ค้นหาปุ่มที่มีขนาดใหญ่ที่สุด (Smart Select)...")
    try:
        # เรียกใช้ฟังก์ชัน Debug เพื่อดึงรายการ Element ที่เรียงตามขนาดมาแล้ว
        elements = debug_ui_structure(window)
        
        if elements:
            # เลือกตัวที่ใหญ่ที่สุด (ตัวแรกใน list เพราะ sort มาแล้ว)
            target = elements[0]
            
            # กรองความปลอดภัย: ปุ่มบริการหลักควรมีขนาดใหญ่ (เช่น กว้าง > 200)
            if target['width'] > 200 and target['height'] > 100:
                log(f"[/] เลือกคลิกปุ่มขนาดใหญ่สุด: '{target['text']}' (Size: {target['width']}x{target['height']})")
                target['item'].click_input()
                return True
            else:
                log(f"[!] ปุ่มใหญ่สุดที่เจอมีขนาดเล็กเกินไป ({target['width']}x{target['height']}) - ไม่กล้ากด")
                
    except Exception as e:
        log(f"Error clicking largest element: {e}")
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

    # ================= [STEP 6: เลือกบริการ] =================
    log("STEP 6: เลือกบริการ (ตรวจสอบและค้างหน้าจอถ้าไม่ผ่าน)")
    
    log("...รอหน้าจอโหลด 2 วินาที...")
    time.sleep(2)
    
    # 1. พยายามกดปุ่มที่ใหญ่ที่สุด (น่าจะเป็น EMS)
    success = click_largest_element(main_window)

    # 2. ถ้ากดไม่เจอ ลองกด Text "EMS"
    if not success:
        log("...ไม่เจอปุ่มใหญ่ -> ลองหา Text 'บริการอีเอ็มเอส'...")
        success = smart_click_by_text_location(main_window, "บริการอีเอ็มเอส", y_offset=40)

    # ================= [CHECK: ผ่านหรือไม่?] =================
    time.sleep(2)
    
    # ตรวจสอบว่ายังอยู่หน้า "บริการหลัก" หรือไม่ (ถ้ายังอยู่แสดงว่ากดไม่ไป)
    still_on_main = wait_for_text(main_window, "บริการหลัก", timeout=1)
    
    if success and not still_on_main:
        log("[SUCCESS] หน้าจอเปลี่ยนแล้ว (น่าจะผ่าน Step 6)")
        time.sleep(1)
        log("...กด 0 เพื่อยืนยัน...")
        main_window.type_keys("0")
    else:
        log("\n[!!! PAUSED !!!] เกิดปัญหา: กดแล้วไม่ไป หรือ ยังอยู่หน้าเดิม")
        log(">> สคริปต์จะหยุดค้างอยู่ที่นี่เพื่อให้คุณตรวจสอบหน้าจอ")
        log(">> กด Ctrl+C ใน Terminal เพื่อปิดโปรแกรม")
        
        # วนลูปค้างไว้ตามที่ขอ
        while True:
            time.sleep(5)
            # สามารถ uncomment บรรทัดล่างถ้าอยากให้มัน report ซ้ำเรื่อยๆ
            # debug_ui_structure(main_window) 
            
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