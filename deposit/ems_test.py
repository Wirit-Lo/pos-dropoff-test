import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. ส่วนจัดการ Config & Log =================
def load_config(filename='config.ini'):
    """โหลดค่าจากไฟล์ config.ini"""
    config = configparser.ConfigParser()
    if not os.path.exists(filename): 
        print(f"[Error] ไม่พบไฟล์ {filename}")
        return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    """แสดงผลการทำงานพร้อมเวลา"""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def debug_dump_ui(window):
    """(Debug) ลิสต์รายการ ID บนหน้าจอเมื่อหาปุ่มไม่เจอ"""
    log("!!! หาไม่เจอ -> กำลังลิสต์ ID ที่โปรแกรมมองเห็น (Debug) !!!")
    try:
        visible_items = []
        for child in window.descendants():
            if child.is_visible():
                aid = child.element_info.automation_id
                txt = child.window_text().strip()
                if aid: visible_items.append(f"ID: {aid}")
                elif txt: visible_items.append(f"Text: {txt}")
        
        unique_items = list(set(visible_items))
        log(f"Items ที่เจอ: {unique_items[:20]} ... (และอื่นๆ)")
    except: pass

# ================= 2. ฟังก์ชันช่วยเหลือ (Scroll, Click, Wait) =================
def force_scroll_down(window, scroll_dist=-5):
    """บังคับ Scroll หน้าจอลงด้านล่าง"""
    try:
        window.set_focus()
        rect = window.rectangle()
        # เลื่อนเมาส์ไปจุดที่ปลอดภัย (ขวา 72%, กลางจอ) แล้ว Scroll
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.2)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.8) # รอให้ UI ขยับ
    except: pass

def smart_click(window, criteria_list, timeout=5, optional=False):
    """ค้นหาและกดปุ่มจากชื่อ (Text)"""
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
    if not optional: log(f"[X] หาปุ่มชื่อ {criteria_list} ไม่เจอ!")
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    """ค้นหาปุ่มจากชื่อแบบมีการเลื่อนหน้าจอ (Scroll)"""
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
                # เช็คว่าปุ่มอยู่ต่ำเกินไปไหม (ติดขอบล่าง)
                elem_rect = found.rectangle()
                win_rect = window.rectangle()
                if elem_rect.bottom >= win_rect.bottom - 70:
                    force_scroll_down(window, -3) # ขยับนิดเดียว
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

# --- ฟังก์ชันกดด้วย ID (พระเอกของเรา) ---
def click_element_by_id(window, exact_id, timeout=5):
    """กดปุ่มด้วย AutomationID แบบระบุชื่อเป๊ะๆ (แม่นยำที่สุด)"""
    log(f"...พยายามกดปุ่ม ID: '{exact_id}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible():
                    child.click_input()
                    log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ!")
                    return True
        except: pass
        time.sleep(0.5)
    return False

def click_element_by_fuzzy_id(window, keyword_in_id, timeout=5):
    """กดปุ่มด้วย AutomationID แบบค้นหาบางส่วน (Fuzzy)"""
    log(f"...ค้นหาปุ่มที่มี ID มีคำว่า: '{keyword_in_id}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
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

def wait_until_service_page_ready(window, timeout=10):
    """รอให้หน้าบริการโหลดเสร็จ โดยเช็คว่ามีปุ่มตระกูล ShippingService โผล่มาหรือยัง"""
    log("...รอหน้าบริการหลักโหลด...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                aid = child.element_info.automation_id
                # เช็คคร่าวๆ ว่ามีปุ่มบริการไหม หรือเช็ค EMS โดยตรงเลย
                if aid and ("ShippingService" in aid) and child.is_visible():
                    log(f"[/] หน้าจอพร้อมแล้ว (เจอ {aid})")
                    return True
        except: pass
        time.sleep(1)
    
    log("[!] หมดเวลารอ (ไม่เจอปุ่มบริการใดๆ)")
    debug_dump_ui(window) 
    return False

# ================= 3. ฟังก์ชันกรอกข้อมูล =================
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
    # เช็ค Popup อ่านบัตรประชาชน
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3, optional=True): 
        time.sleep(1.5) 
        try:
            # หาช่องรหัสไปรษณีย์ผู้ส่ง ถ้าว่างให้เติม
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    if not edit.get_value():
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    break 
        except: pass
        
        # กรอกเบอร์โทร (เลื่อนหาถ้าจำเป็น)
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
    # เช็คหน้าสิ่งของต้องห้าม
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}")
                    return
        except: pass
        time.sleep(0.5)

# ================= 4. Main Scenario (ขั้นตอนการทำงานหลัก) =================
def run_smart_scenario(main_window, config):
    try:
        # อ่านค่าจาก Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.5))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
    except Exception as e: 
        log(f"[Error] อ่าน Config ผิดพลาด: {e}")
        return

    log(f"--- เริ่มต้นการทำงาน ---")
    time.sleep(0.5)

    # 1. กดเมนูรับฝาก
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. จัดการ Popup ผู้ส่ง (ถ้ามี)
    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    # 3. เลือกซองจดหมาย
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)

    # 4. เลือกออปชั่นพิเศษ (ถ้ามีใน config)
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            if opt: smart_click(main_window, opt.strip(), timeout=1, optional=True)
    
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 5. หน้าสิ่งของต้องห้าม
    handle_prohibited_items(main_window)
    
    # 6. กรอกน้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    # 7. กรอกรหัส ปณ. ปลายทาง
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)

    # 8. ตรวจสอบ Popup ทับซ้อน (สำคัญ)
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

    # --- 9. เข้าสู่ขั้นตอนเลือก EMS (ไฮไลท์สำคัญ) ---
    log("...กำลังไปที่หน้าบริการหลัก เพื่อเลือก EMS...")
    
    # รอให้หน้าจอพร้อม
    if not wait_until_service_page_ready(main_window, timeout=10):
        log("[!] หน้าจออาจจะยังไม่พร้อม แต่จะพยายามกด...")

    # [Priority 1] กดด้วย ID ที่ถูกต้อง 100% (จากที่เราหาเจอ)
    target_id = "ShippingService_EMSServices"
    
    if click_element_by_id(main_window, target_id):
        log(f"[SUCCESS] เลือกบริการ EMS เรียบร้อย (กดจาก ID: {target_id})")
        
    # [Priority 2] ถ้า ID เปลี่ยนนิดหน่อย ลองหาแบบ Fuzzy (EMSS)
    elif click_element_by_fuzzy_id(main_window, "EMSS"): 
        log("[SUCCESS] เลือกบริการ EMS เรียบร้อย (กดจาก Fuzzy ID)")
        
    else:
        # [Fail] ถ้าหาไม่เจอจริงๆ แจ้ง Error (ไม่กดพิกัดมั่ว)
        log(f"[ERROR] หาปุ่ม EMS ไม่เจอ! (ลองทั้ง ID '{target_id}' และ Fuzzy 'EMSS')")
        debug_dump_ui(main_window) # แสดง Debug Info เพื่อดูว่ามี ID อะไรบ้าง

    log("\n[SUCCESS] จบการทำงาน")
    print(">>> กด Enter เพื่อปิดโปรแกรม... <<<")
    input()

# ================= 5. เริ่มต้นโปรแกรม =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting to Application...")
        try:
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            # เชื่อมต่อกับโปรแกรมตามชื่อ Title ใน Config
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            win.set_focus()
            
            # เริ่มรัน Scenario
            run_smart_scenario(win, conf)
            
        except Exception as e:
            log(f"Error: {e}")
            log("คำแนะนำ: ตรวจสอบชื่อ WindowTitle ใน config.ini ว่าตรงกับโปรแกรมหรือไม่")
    else:
        print("กรุณาสร้างไฟล์ config.ini ก่อนเริ่มใช้งาน")