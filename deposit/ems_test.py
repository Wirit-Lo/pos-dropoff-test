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
    log("!!! หาไม่เจอ -> กำลังลิสต์ ID ที่โปรแกรมมองเห็น (Debug) !!!")
    try:
        visible_items = []
        for child in window.descendants():
            if child.is_visible():
                aid = child.element_info.automation_id
                txt = child.window_text().strip()
                if aid: visible_items.append(f"ID: {aid}")
                elif txt: visible_items.append(f"Text: {txt}")
        
        # ตัดรายการซ้ำและปริ้นท์
        unique_items = list(set(visible_items))
        log(f"Items ที่เจอ: {unique_items[:20]} ... (แสดงบางส่วน)")
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

# [UPDATED] ฟังก์ชันกดปุ่มด้วย ID แบบยืดหยุ่น (Fuzzy Match)
def click_element_by_fuzzy_id(window, keyword_in_id, timeout=5):
    log(f"...ค้นหาปุ่มที่มี ID มีคำว่า: '{keyword_in_id}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            # วนหา Element ทั้งหมด
            for child in window.descendants():
                aid = child.element_info.automation_id
                if child.is_visible() and aid and keyword_in_id in aid:
                    log(f"[/] เจอ ID: '{aid}' -> กำลังกด...")
                    child.click_input()
                    return True
        except: pass
        time.sleep(0.5)
    
    log(f"[X] หาปุ่มที่มี ID '{keyword_in_id}' ไม่เจอ")
    return False

# [NEW] ฟังก์ชันกดที่พิกัด (ไม้ตายสุดท้าย)
def click_by_coordinate(window, x, y):
    log(f"...[ไม้ตาย] สั่งกดที่พิกัด ({x}, {y})...")
    try:
        window.set_focus()
        # คำนวณตำแหน่งสัมพัทธ์หรือกด Absolute เลยก็ได้
        # ในที่นี้ใช้ Absolute coordinate จากที่ Debug มา
        mouse.click(coords=(x, y))
        log("[/] กดพิกัดเรียบร้อย")
        return True
    except Exception as e:
        log(f"[!] กดพิกัดล้มเหลว: {e}")
        return False

def wait_until_service_page_ready(window, timeout=10):
    log("...รอหน้าบริการหลักโหลด (เช็คจากปุ่ม ShippingService)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            # เช็คว่ามีปุ่มใดๆ ที่ขึ้นต้นด้วย ShippingService โผล่มาไหม
            for child in window.descendants():
                aid = child.element_info.automation_id
                if aid and "ShippingService" in aid and child.is_visible():
                    log(f"[/] หน้าจอพร้อมแล้ว (เจอ {aid})")
                    return True
        except: pass
        time.sleep(1)
    
    log("[!] หมดเวลารอ (ไม่เจอปุ่มบริการใดๆ)")
    debug_dump_ui(window) # ปริ้นท์ Debug ให้ดูว่าเห็นอะไรบ้าง
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
        
        # กรอกเบอร์โทร
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
    
    # 1. รอให้หน้าจอโหลดเสร็จ (เช็คว่ามีปุ่ม Service โผล่มาหรือยัง)
    if not wait_until_service_page_ready(main_window, timeout=10):
        log("[!] หาปุ่มบริการไม่เจอ อาจจะยังอยู่หน้าเดิม หรือหน้าจอโหลดไม่เสร็จ")
    
    # 2. ลองกดด้วย Fuzzy ID (หาปุ่มที่มีคำว่า "EMSS" หรือ "EMS" ใน ID)
    if click_element_by_fuzzy_id(main_window, "EMSS"):
        log("[SUCCESS] เลือกบริการ EMS เรียบร้อย (เจอจาก ID)")
        
    elif click_element_by_fuzzy_id(main_window, "EMS"): # ลองหาแค่ EMS
        log("[SUCCESS] เลือกบริการ EMS เรียบร้อย (เจอจาก ID แบบสั้น)")
        
    else:
        # 3. [ไม้ตาย] ถ้าหา ID ไม่เจอเลย ให้กดที่พิกัดเดิมที่เราเคยเห็น
        log("[!] ไม่เจอ ID -> ใช้ไม้ตาย กดที่พิกัด (216, 278)")
        click_by_coordinate(main_window, 216, 278)

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