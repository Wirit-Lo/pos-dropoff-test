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
        print(f"[Error] ไม่พบไฟล์ {filename} กรุณาสร้างไฟล์ก่อน")
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
                if aid: visible_items.append(f"ID: {aid}")
        log(f"Items ที่เจอ: {list(set(visible_items))[:20]}...")
    except: pass

# ================= 2. ฟังก์ชันช่วยเหลือ (Scroll, Click) =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        window.set_focus()
        rect = window.rectangle()
        # เลื่อนเมาส์ไปจุดที่ปลอดภัย (ขวา 72%, กลางจอ) แล้ว Scroll
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.2)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.8)
    except: pass

def smart_click(window, criteria_list, timeout=5):
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
    return False

def click_element_by_id(window, exact_id, timeout=5, index=0):
    """กดปุ่มด้วย AutomationID แบบระบุชื่อเป๊ะๆ (แม่นยำที่สุด)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            found_elements = []
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible():
                    found_elements.append(child)
            
            if len(found_elements) > index:
                found_elements[index].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ!")
                return True
        except: pass
        time.sleep(0.5)
    return False

def click_element_by_fuzzy_id(window, keyword, timeout=5):
    """กดปุ่มด้วย AutomationID แบบค้นหาบางส่วน (Fuzzy)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                aid = child.element_info.automation_id
                if child.is_visible() and aid and keyword in aid:
                    child.click_input()
                    log(f"[/] เจอ Fuzzy ID: '{aid}' -> กดสำเร็จ")
                    return True
        except: pass
        time.sleep(0.5)
    return False

def wait_until_id_appears(window, exact_id, timeout=10):
    """รอจนกว่า ID ที่ระบุจะปรากฏบนหน้าจอ"""
    log(f"...รอโหลด ID: {exact_id}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible():
                    return True
        except: pass
        time.sleep(1)
    return False

# ================= 3. ฟังก์ชัน Input =================
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
    if not smart_click(window, "ถัดไป", timeout=2):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone, postal):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input()
                        edit.type_keys(str(postal), with_spaces=True)
                    break 
        except: pass
        
        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input()
                        edit.type_keys(str(phone), with_spaces=True)
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

# ================= 4. Workflow หลัก =================
def run_smart_scenario(main_window, config):
    try:
        # อ่านค่า Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
    except: 
        log("[Error] อ่าน Config ไม่สำเร็จ")
        return

    log(f"--- เริ่มต้นการทำงาน ---")
    time.sleep(0.5)

    # 1. กดรับฝาก
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ข้อมูลผู้ส่ง
    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    # 3. เลือกซองจดหมาย
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)
    
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. สิ่งของต้องห้าม & น้ำหนัก
    handle_prohibited_items(main_window)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    # 5. รหัส ปณ. ปลายทาง
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. ตรวจสอบ Popup ทับซ้อน (ถ้ามี)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            txt = child.window_text()
            if "ทับซ้อน" in txt or "พื้นที่" in txt:
                log("[Popup] พบแจ้งเตือนทับซ้อน -> กด 'ดำเนินการ'")
                smart_click(main_window, "ดำเนินการ")
                found = True; break
        if found: break
        time.sleep(0.5)

    # --- เลือก EMS และ ใส่ประกัน ---
    log("...รอหน้าบริการหลัก...")
    if not wait_until_id_appears(main_window, "ShippingService_EMSServices", timeout=10):
        log("[!] ไม่เจอปุ่ม EMS (แต่จะพยายามต่อ)")

    # 7. กดเลือก EMS (จากเมนูหลัก)
    if click_element_by_id(main_window, "ShippingService_EMSServices"):
        log("[SUCCESS] เลือก EMS (Main) สำเร็จ")
    elif click_element_by_fuzzy_id(main_window, "EMSS"):
        log("[SUCCESS] เลือก EMS (Fuzzy) สำเร็จ")
    else:
        log("[ERROR] หาปุ่ม EMS ไม่เจอ")
        return

    # [สำคัญ] 8. กดเลือก 'EMS ในประเทศ' ซ้ำอีกครั้งเพื่อให้ Active (กรอบส้ม)
    time.sleep(2) 
    log("...กดเลือก 'EMS ในประเทศ' เพื่อ Activate...")
    
    # ใช้ ID ของการ์ดใบแรกในหน้านี้ (ShippingService_2572)
    inner_ems_id = "ShippingService_2572" 
    
    if click_element_by_id(main_window, inner_ems_id):
        log("[SUCCESS] Activate 'EMS ในประเทศ' เรียบร้อย")
    else:
        log(f"[WARN] ไม่เจอ ID '{inner_ems_id}' -> ลองกด Fuzzy 'ShippingService'")
        click_element_by_fuzzy_id(main_window, "ShippingService")

    time.sleep(1)

    # 9. กดปุ่มบวก (+) เพื่อใส่ประกัน
    log(f"...กดปุ่มบวก (+) ใส่วงเงินประกัน {insurance_amt}...")
    if click_element_by_id(main_window, "CoverageButton"):
        
        # 10. รอช่องกรอกเงิน
        if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
            log("[Popup] เจอช่องกรอกเงิน -> กำลังพิมพ์...")
            
            # หาช่อง CoverageAmount แล้วพิมพ์
            for child in main_window.descendants():
                if child.element_info.automation_id == "CoverageAmount":
                    child.click_input()
                    child.type_keys(str(insurance_amt), with_spaces=True)
                    break
            
            time.sleep(0.5)
            
            # 11. กดถัดไปใน Popup (LocalCommand_Submit ตัวบน)
            log("...กด 'ถัดไป' เพื่อปิด Popup...")
            submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
            # เรียงจากบนลงล่าง (Y น้อย -> มาก)
            submits.sort(key=lambda x: x.rectangle().top)
            
            if submits:
                submits[0].click_input() # กดตัวบน (Popup)
                log("[SUCCESS] ปิด Popup วงเงินเรียบร้อย")
            else:
                main_window.type_keys("{ENTER}")
        else:
            log("[ERROR] ไม่เจอช่องกรอกเงิน CoverageAmount")
    else:
        log("[WARN] หาปุ่ม (+) CoverageButton ไม่เจอ (ข้ามการใส่ประกัน)")

    # 12. กดถัดไป (Footer) เพื่อจบขั้นตอน
    time.sleep(1)
    log("...กด 'ถัดไป' (Footer)...")
    submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
    submits.sort(key=lambda x: x.rectangle().top)
    
    if submits:
        submits[-1].click_input() # กดตัวล่างสุด
        log("[SUCCESS] กดถัดไป (Footer) เรียบร้อย")
    else:
        main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")
    input(">>> กด Enter เพื่อปิด... <<<")

# ================= 5. เริ่มต้นโปรแกรม =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=wait)
            run_smart_scenario(app.top_window(), conf)
        except Exception as e:
            log(f"Error: {e}")