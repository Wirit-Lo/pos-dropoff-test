import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. ส่วนจัดการ Config & Log =================
def load_config(filename='config.ini'):
    """โหลดค่าจากไฟล์ config.ini"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
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
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.2)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.8)
    except: pass

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
    return False

def click_element_by_id(window, exact_id, timeout=5, index=0):
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

def wait_for_text(window, text, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
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
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input() # ตัวล่างสุด
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def process_sender_info_popup(window, phone, postal):
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
        
        if not smart_click(window, "ถัดไป", timeout=2):
            window.type_keys("{ENTER}")

def handle_prohibited_items(window):
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}")
                    return
        except: pass
        time.sleep(0.5)

# --- ฟังก์ชันสำหรับหน้าใหม่ ---
def process_special_services(window, services_str):
    log("--- เข้าสู่หน้า: บริการพิเศษ ---")
    if wait_for_text(window, "บริการพิเศษ", timeout=5):
        if services_str.strip():
            services = [s.strip() for s in services_str.split(',')]
            for s in services:
                if s:
                    log(f"...เลือกบริการ: {s}")
                    if not smart_click(window, s):
                        log(f"   [X] หาบริการ {s} ไม่เจอ")
        else:
            log("...ไม่มีบริการพิเศษที่ต้องเลือก")
    else:
        log("[WARN] ไม่พบหน้าบริการพิเศษ (อาจข้ามไปแล้ว)")
    smart_next(window)

def process_sender_info_page(window):
    log("--- เข้าสู่หน้า: ข้อมูลผู้ส่ง ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    log("...กดถัดไป (ข้าม)...")
    smart_next(window)

def process_receiver_info_page(window, address):
    log("--- เข้าสู่หน้า: ข้อมูลผู้รับ ---")
    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        time.sleep(1)
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                # หาช่องที่อยู่ (มักจะว่างอยู่)
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    log(f"...กรอกที่อยู่: {address[:20]}...")
                    edit.click_input()
                    edit.type_keys(str(address), with_spaces=True)
                    filled = True
                    break
            
            if not filled and len(edits) > 1:
                log("...กรอกช่องสำรอง...")
                edits[1].click_input()
                edits[1].type_keys(str(address), with_spaces=True)
        except Exception as e:
            log(f"[!] Error กรอกที่อยู่: {e}")
    smart_next(window)

def handle_final_warning(window):
    log("...รอ Popup แจ้งเตือนสุดท้าย...")
    if wait_for_text(window, "แจ้งเตือน", timeout=5) or wait_for_text(window, "ไม่มีผลลัพธ์", timeout=2):
        log("[Popup] พบแจ้งเตือน -> กด 'ตกลง/OK'")
        if not smart_click(window, ["ตกลง", "OK"]):
            window.type_keys("{ENTER}")
    else:
        log("...ไม่พบ Popup แจ้งเตือน")

# ================= 4. Workflow หลัก =================
def run_smart_scenario(main_window, config):
    try:
        # อ่านค่าจาก Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '25')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10220')
        phone = config['TEST_DATA'].get('PhoneNumber', '0899998888')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        
        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        receiver_address = config['RECEIVER'].get('Address', 'Bangkok')
        
        step_delay = float(config['SETTINGS'].get('StepDelay', 3))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -20))
        wait_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))
        
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log(f"--- เริ่มต้นการทำงาน (Delay: {step_delay}s) ---")
    time.sleep(1)

    # 1. กดรับฝาก
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ข้อมูลผู้ส่ง (หน้าแรก)
    process_sender_info_popup(main_window, phone, postal) 
    time.sleep(step_delay)

    # 3. เลือกซองจดหมาย
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)
    
    # 4. เลือกออปชั่นพิเศษ (LQ, FR)
    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        for opt in options:
            if opt: smart_click(main_window, opt, timeout=2)
    
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 5. หน้าสิ่งของต้องห้าม & น้ำหนัก
    handle_prohibited_items(main_window)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    # 6. รหัส ปณ. ปลายทาง
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)

    # 7. ตรวจสอบ Popup ทับซ้อน
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ")
                found = True; break
        if found: break
        time.sleep(0.5)

    # --- เลือก EMS และ ใส่ประกัน ---
    log("...รอหน้าบริการหลัก...")
    if not wait_until_id_appears(main_window, "ShippingService_EMSServices", timeout=wait_timeout):
        log("[!] ไม่เจอปุ่ม EMS (แต่จะพยายามต่อ)")

    # 8. กดเลือก EMS
    if click_element_by_id(main_window, "ShippingService_EMSServices"):
        log("[SUCCESS] เลือก EMS (Main) สำเร็จ")
    elif click_element_by_fuzzy_id(main_window, "EMSS"):
        log("[SUCCESS] เลือก EMS (Fuzzy) สำเร็จ")
    else:
        log("[ERROR] หาปุ่ม EMS ไม่เจอ")
        return

    # 9. กดเลือก 'EMS ในประเทศ' ซ้ำเพื่อให้ Active
    time.sleep(step_delay) 
    log("...กดเลือก 'EMS ในประเทศ' เพื่อ Activate...")
    inner_ems_id = "ShippingService_2572" 
    if click_element_by_id(main_window, inner_ems_id):
        log("[SUCCESS] Activate 'EMS ในประเทศ' เรียบร้อย")
    else:
        log(f"[WARN] ไม่เจอ ID '{inner_ems_id}' -> ลองกด Fuzzy")
        click_element_by_fuzzy_id(main_window, "ShippingService")

    time.sleep(1)

    # 10. ใส่ประกัน (ตาม Config)
    if add_insurance_flag.lower() == 'true':
        log(f"...ต้องการประกัน -> กดปุ่มบวก ใส่ยอด {insurance_amt}...")
        if click_element_by_id(main_window, "CoverageButton"):
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
                for child in main_window.descendants():
                    if child.element_info.automation_id == "CoverageAmount":
                        child.click_input()
                        child.type_keys(str(insurance_amt), with_spaces=True)
                        break
                time.sleep(0.5)
                # ปิด Popup
                submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
                submits.sort(key=lambda x: x.rectangle().top)
                if submits: submits[0].click_input()
                else: main_window.type_keys("{ENTER}")
            else:
                log("[ERROR] ไม่เจอช่องกรอกเงิน")
        else:
            log("[WARN] หาปุ่ม (+) ไม่เจอ")
    else:
        log("[INFO] AddInsurance = False -> ข้าม")

    # 11. กดถัดไป (Footer)
    time.sleep(step_delay)
    smart_next(main_window)
    time.sleep(step_delay)

    # --- ส่วนที่เพิ่มใหม่ ---

    # 12. หน้าบริการพิเศษ
    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    # 13. หน้าข้อมูลผู้ส่ง (ข้าม)
    process_sender_info_page(main_window)
    time.sleep(step_delay)

    # 14. หน้าข้อมูลผู้รับ (กรอกที่อยู่)
    process_receiver_info_page(main_window, receiver_address)
    time.sleep(step_delay)

    # 15. Popup แจ้งเตือนสุดท้าย
    handle_final_warning(main_window)

    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

# ================= 5. เริ่มต้นโปรแกรม =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            
            log(f"Connecting to Title: {app_title} (Wait: {wait}s)")
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2:
                    main_window.restore()
                main_window.set_focus()
            
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง และชื่อ Title ตรงกับใน Config หรือไม่")
    
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")