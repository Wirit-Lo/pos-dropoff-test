import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    config = configparser.ConfigParser(strict=False)
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

# ================= 2. Core Helper Functions =================

def force_scroll_down(window, scroll_dist=-5):
    """สั่ง Scroll Mouse โดยตรง (เร็วและแม่นยำ)"""
    try:
        rect = window.rectangle()
        # Scroll ตรงกลางค่อนขวาเล็กน้อย
        scrollbar_x = rect.left + int(rect.width() * 0.6)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.1) 
    except: pass

def wait_while_processing(window, timeout=10):
    """รอจนกว่า Popup 'กำลังดำเนินการ' หรือ 'Loading' จะหายไป"""
    start = time.time()
    while time.time() - start < timeout:
        found_loading = False
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                txt = child.window_text()
                if "กำลังดำเนินการ" in txt or "กรุณารอสักครู่" in txt or "Processing" in txt:
                    found_loading = True; break
        except: pass
        
        if not found_loading: return True
        time.sleep(0.5)
    return False

def check_error_popup(window, delay=0.2):
    """ตรวจจับและปิด Popup แจ้งเตือน/Error ต่างๆ"""
    if delay > 0: time.sleep(delay)
    try:
        # เช็คหน้าต่าง Popup (Window Control)
        for child in window.descendants(control_type="Window"):
            if not child.is_visible(): continue
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt or "ไม่สามารถ" in txt:
                log(f"[WARN] พบ Popup: {txt} -> กดปิด")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=1): return True
                else: child.type_keys("{ENTER}"); return True
    except: pass
    return False

def smart_click(window, criteria_list, timeout=5):
    """คลิกปุ่มโดยค้นหาจาก Text หรือ AutomationId"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if not child.is_visible(): continue
                    # เช็คทั้ง Text และ ID
                    txt_match = criteria in child.window_text().strip()
                    id_match = criteria in str(child.element_info.automation_id)
                    name_match = criteria in str(child.element_info.name)
                    
                    if txt_match or id_match or name_match:
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.2)
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=15, scroll_dist=-10):
    """ค้นหาปุ่มและคลิก ถ้าไม่เจอจะ Scroll หา (Turbo Mode)"""
    log(f"...ค้นหา '{criteria}' (Scroll Mode)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                if criteria in child.window_text() or criteria in str(child.element_info.automation_id):
                    found = child; break
        except: pass

        if found:
            try:
                # ถ้าเจอแต่อยู่ต่ำเกินไป ให้ Scroll ดีดขึ้นมาก่อนกด
                rect = found.rectangle()
                win_rect = window.rectangle()
                if rect.bottom > win_rect.bottom - 50:
                    force_scroll_down(window, -20); time.sleep(0.2)
                
                found.click_input()
                log(f"[/] เจอและกด '{criteria}' สำเร็จ")
                return True
            except: pass
        
        if i < max_scrolls:
            force_scroll_down(window, scroll_dist)
            
    log(f"[X] หาไม่เจอ: '{criteria}'")
    return False

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    """ค้นหาช่องกรอกข้อมูล (Text/ID) แล้วกรอกค่า"""
    try:
        if not value or str(value).strip() == "": return False

        target_elem = None
        # วนลูปหา 2 รอบ (รอบแรกหาเลย, รอบสอง Scroll นิดนึงแล้วหา)
        for _ in range(2):
            for child in window.descendants():
                if not child.is_visible(): continue
                aid = str(child.element_info.automation_id)
                name = str(child.element_info.name)
                
                if (target_name and target_name in name) or (target_id_keyword and target_id_keyword in aid):
                    target_elem = child; break
            
            if target_elem: break
            force_scroll_down(window, -5); time.sleep(0.2) # ไม่เจอให้ลองเลื่อน

        if target_elem:
            log(f"   -> เจอช่อง '{target_name}' -> กรอก: {value}")
            try:
                edits = target_elem.descendants(control_type="Edit")
                if edits: target_elem = edits[0]
            except: pass
            
            target_elem.set_focus()
            target_elem.click_input()
            target_elem.type_keys(str(value), with_spaces=True)
            return True
        else:
            return False
    except: return False

def wait_until_id_appears(window, exact_id, timeout=10):
    """รอจนกว่า Element ID นี้จะปรากฏ"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(0.5)
    return False

def wait_for_text(window, text_list, timeout=5):
    """รอจนกว่าข้อความ (หรือรายการข้อความ) จะปรากฏ"""
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                txt = child.window_text()
                for t in text_list:
                    if t in txt: return True
        except: pass
        time.sleep(0.5)
    return False

def smart_next(window):
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        window.type_keys("{ENTER}")

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, sender_postal):
    """จัดการ Popup ข้อมูลผู้ส่ง (หน้าแรก)"""
    if smart_click(window, "อ่านบัตรประชาชน", timeout=2): 
        time.sleep(1.5)
        # ลองกรอกรหัสไปรษณีย์ถ้าว่าง
        try:
            edits = [e for e in window.descendants(control_type="Edit") if "รหัสไปรษณีย์" in e.element_info.name]
            if edits and not edits[0].get_value():
                edits[0].click_input(); edits[0].type_keys(str(sender_postal), with_spaces=True)
        except: pass
        
        # ลองกรอกเบอร์โทร
        if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
            force_scroll_down(window, -5)
            find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone)
            
        smart_next(window)

def process_receiver_address_selection(window, address_keyword, manual_data):
    """หน้าค้นหาที่อยู่: คืนค่า True ถ้าต้องไปกรอกเอง (Manual Mode)"""
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    is_manual_mode = False

    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        # 1. กรอกคำค้นหา
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                # พยายามหาช่องที่ว่างหรือช่องแรก
                target = next((e for e in edits if not e.get_value()), edits[0])
                target.click_input()
                target.type_keys(str(address_keyword), with_spaces=True)
        except: pass

        smart_next(window) # กดค้นหา
        time.sleep(1.0)
        
        # 2. เช็คผลลัพธ์ (Popup หรือ List)
        found_popup = False; found_list = False
        for _ in range(20): # รอเช็คผลลัพธ์
            if check_error_popup(window, delay=0):
                found_popup = True; break
            
            # เช็คว่ามีรายการ ListItem โผล่มาไหม
            list_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible() and i.rectangle().top > 200]
            if list_items: found_list = True; break
            time.sleep(0.25)

        if found_popup:
            log("[Detect] เจอ Popup แจ้งเตือน -> เข้าโหมดกรอกเอง")
            is_manual_mode = True
            time.sleep(1.0)
        elif found_list:
            log("[Detect] เจอรายการที่อยู่ -> เลือกรายการแรก")
            try:
                # กรองรายการที่อยู่ (ตัด Header ด้านบนออก)
                valid_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible() and i.rectangle().top > 200]
                if valid_items:
                    valid_items.sort(key=lambda x: x.rectangle().top)
                    valid_items[0].click_input()
                    time.sleep(1.5) # รอโหลดข้อมูล
            except: pass
        else:
            log("[Detect] ไม่เจออะไรเลย -> สันนิษฐานว่าต้องกรอกเอง")
            is_manual_mode = True
            smart_next(window)

    return is_manual_mode

def process_special_services(window, services_str):
    log("--- หน้า: บริการพิเศษ ---")
    if wait_for_text(window, "บริการพิเศษ", timeout=5):
        if services_str.strip():
            for s in services_str.split(','):
                if s: smart_click(window, s.strip())
    smart_next(window)

def process_sender_info_page(window):
    log("--- หน้า: ข้อมูลผู้ส่ง (ข้าม) ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    smart_next(window)

def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    """หน้ากรอกรายละเอียดผู้รับ (และที่อยู่ถ้าจำเป็น)"""
    log("--- หน้า: รายละเอียดผู้รับ ---")
    
    # รอหน้าจอโหลดและเคลียร์ Popup เก่า
    wait_while_processing(window, timeout=5)
    check_error_popup(window)

    # 1. กรอกชื่อ-นามสกุล (พื้นฐาน)
    find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)
    find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

    # 2. เช็คว่าต้องกรอกที่อยู่เองหรือไม่? (Auto-Detect)
    # ถ้าช่อง "จังหวัด" ว่างแปลว่าต้องกรอกเอง แม้ is_manual_mode จะเป็น False ก็ตาม
    need_fill_address = is_manual_mode
    if not need_fill_address:
        try:
            # ลองหาช่องจังหวัด ถ้าค่าว่าง = ต้องกรอก
            prov_box = [c for c in window.descendants(control_type="Edit") if "AdministrativeArea" in str(c.element_info.automation_id)]
            if prov_box and (not prov_box[0].get_value() or str(prov_box[0].get_value()).strip() == ""):
                log("[Auto-Detect] ช่องจังหวัดว่าง -> บังคับเข้าโหมด Manual Fill")
                need_fill_address = True
        except: pass

    # 3. กรอกที่อยู่ (ถ้าจำเป็น)
    if need_fill_address:
        log("...เริ่มกรอกที่อยู่ (Manual)...")
        # เลื่อนลงก่อนเลย เพื่อกันการหาช่องไม่เจอ
        force_scroll_down(window, -10)
        time.sleep(0.5)

        # เรียงลำดับการกรอก: จังหวัด -> เขต -> แขวง -> ที่อยู่
        data_map = [
            ("จังหวัด", "AdministrativeArea", manual_data.get('Province', '')),
            ("เขต", "Locality", manual_data.get('District', '')),
            ("แขวง", "DependentLocality", manual_data.get('SubDistrict', '')),
            ("ที่อยู่ 1", "StreetAddress1", manual_data.get('Address1', '')),
            ("ที่อยู่ 2", "StreetAddress2", manual_data.get('Address2', ''))
        ]

        for label, aid, val in data_map:
            if not find_and_fill_smart(window, label, aid, val):
                # ถ้าหาช่องไม่เจอ ลองกด Tab แล้วพิมพ์ (Fallback)
                window.type_keys("{TAB}"); window.type_keys(str(val), with_spaces=True)

    # 4. กรอกเบอร์โทร (อยู่ล่างสุดเสมอ)
    force_scroll_down(window, -5)
    if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
        find_and_fill_smart(window, "โทร", "Phone", phone)

    log("...กดถัดไปเพื่อจบหน้าผู้รับ...")
    smart_next(window); time.sleep(1.0)
    smart_next(window); time.sleep(1.0) # กดเผื่อ

def process_repeat_transaction(window, should_repeat):
    """จัดการ Popup ทำรายการซ้ำ"""
    log("--- หน้า: ตรวจสอบการทำรายการซ้ำ ---")
    
    # แปลง Config เป็น Boolean
    is_repeat_intent = str(should_repeat).strip().lower() in ['true', 'yes', 'on', '1']
    
    found_popup = False
    # รอ Popup นานหน่อย (เพราะบางทีต้องรอโหลดข้อมูลก่อน Popup จะเด้ง)
    log("...รอ Popup (Max 15s)...")
    for _ in range(30):
        # หาจากข้อความ
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำ", "ยืนยัน"], timeout=0.2):
            found_popup = True; break
        # หรือหาปุ่ม Yes/No โดยตรง (กรณีข้อความไม่ชัด)
        if smart_click(window, "Check_Yes", timeout=0.1): # ลองหาปุ่ม Test
             found_popup = True; break
        time.sleep(0.5)

    if found_popup:
        log("...เจอ Popup!...")
        target = "ใช่" if is_repeat_intent else "ไม่"
        log(f"...เลือก: '{target}' (ตาม Config)")
        
        # พยายามกดปุ่ม
        if not smart_click(window, target, timeout=3):
            # Fallback (ภาษาอังกฤษ หรือ ปุ่มกด)
            if is_repeat_intent: window.type_keys("{ENTER}")
            else: window.type_keys("{ESC}")
        
        # [สำคัญ] รอให้ Popup หายไป
        log("...รอระบบประมวลผล (4s)...")
        time.sleep(4.0)
        wait_while_processing(window)
        return is_repeat_intent # คืนค่าความตั้งใจ (True=หยุด, False=ไปต่อ)
    else:
        log("[Info] ไม่พบ Popup ทำรายการซ้ำ -> ดำเนินการต่อ")
        return False # ไม่เจอ Popup ก็ถือว่าไม่ทำซ้ำ ไปจ่ายเงินเลย

def process_payment(window, payment_method, received_amount):
    """ขั้นตอนการชำระเงิน"""
    log("--- ขั้นตอนการชำระเงิน ---")
    wait_while_processing(window)
    
    # 1. กดรับเงิน
    if not smart_click(window, "รับเงิน", timeout=5):
        log("[WARN] หาปุ่มรับเงินไม่เจอ (อาจจะอยู่หน้าอื่น)")
        return

    # 2. รอหน้าชำระเงินโหลด (สังเกตจากข้อความ)
    log("...รอหน้าชำระเงิน...")
    if not wait_for_text(window, ["รับชำระเงิน", "ยอดเงินสุทธิ", "เงินทอน"], timeout=10):
        log("[WARN] ไม่มั่นใจว่าอยู่หน้าชำระเงินหรือไม่ -> ลองกดปุ่มเงินสดดู")

    # 3. เลือกวิธีจ่ายเงิน
    if not smart_click(window, payment_method, timeout=3):
        smart_click(window, "เงินสด")
    
    # 4. กรอกยอดเงิน (Popup)
    time.sleep(1.0)
    try:
        # หา Edit Box ที่ Active อยู่
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(received_amount), with_spaces=True)
        window.type_keys("{ENTER}")
    except: pass
    
    # 5. จบรายการ
    time.sleep(1.5)
    log("...จบรายการ (Enter)...")
    window.type_keys("{ENTER}")

# ================= 4. Workflow Main =================
def run_smart_scenario(main_window, config):
    try:
        # Config Values
        category_name = "อุปกรณ์ไก่ชน" 
        category_id_fallback = "MailPieceShape_SubParent_CockFightingEquipments"
        product_detail = "อุปกรณ์ไก่ชน ม้วนพรมไก่ ไม่เกิน 1 ผืน"
        
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        width = config['DEPOSIT_ENVELOPE'].get('Width', '10')
        length = config['DEPOSIT_ENVELOPE'].get('Length', '20')
        height = config['DEPOSIT_ENVELOPE'].get('Height', '10')
        
        receiver_postal = config['DEPOSIT_ENVELOPE'].get('ReceiverPostalCode', '10110')
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')

        # Read Extra Options from Config
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '0')

        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
        
        # Data & Settings
        manual_data = {
            'Address1': config['MANUAL_ADDRESS_FALLBACK'].get('Address1', ''),
            'Address2': config['MANUAL_ADDRESS_FALLBACK'].get('Address2', ''),
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', ''),
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', ''),
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '')
        }
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        
    except Exception as e: log(f"[Error] Config Error: {e}"); return

    log("--- เริ่มต้นการทำงาน ---")
    time.sleep(0.5)

    # 1. เข้าเมนูรับฝาก & ข้อมูลผู้ส่ง
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    process_sender_info_popup(main_window, phone, sender_postal)
    time.sleep(step_delay)

    # 2. เลือก EMS
    if not smart_click_with_scroll(main_window, "EMS สินค้าสำเร็จรูป", scroll_dist=scroll_dist): 
        log("[Error] ไม่เจอเมนู EMS"); return
    time.sleep(step_delay)

    # 2.5 [NEW] เลือก Special Options (ถ้ามีใน Config) ก่อนเข้าสู่ Step 3
    if special_options_str.strip():
        log(f"...เลือกตัวเลือกพิเศษ: {special_options_str}")
        for opt in special_options_str.split(','):
            if opt: smart_click(main_window, opt.strip(), timeout=2)
        time.sleep(0.5)

    # 3. เลือกหมวดหมู่ (ไก่ชน)
    if not smart_click_with_scroll(main_window, category_name, max_scrolls=10):
        smart_click_with_scroll(main_window, category_id_fallback, max_scrolls=5)
    smart_next(main_window)
    time.sleep(step_delay)

    # 4. เลือกรุปร่าง
    smart_click_with_scroll(main_window, product_detail, max_scrolls=20)
    smart_next(main_window)
    time.sleep(step_delay)

    # 5. น้ำหนัก & ปริมาตร
    find_and_fill_smart(main_window, "น้ำหนัก", "Weight", weight)
    smart_next(main_window); time.sleep(step_delay)
    
    # ปริมาตร (ใช้ Tab เพราะไม่มีชื่อช่องชัดเจน)
    log(f"...กรอกปริมาตร: {width}x{length}x{height}")
    try:
        main_window.set_focus()
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            main_window.type_keys(f"{width}{{TAB}}{length}{{TAB}}{height}", with_spaces=True)
    except: pass
    smart_next(main_window); time.sleep(step_delay)

    # 6. ปณ. ปลายทาง
    main_window.type_keys(str(receiver_postal), with_spaces=True)
    smart_next(main_window); time.sleep(step_delay)

    # 7. จัดการ Popup พื้นที่/บริการขนส่ง
    log("...ตรวจสอบ Popup พื้นที่ทับซ้อน...")
    for _ in range(3):
        if wait_for_text(main_window, ["ทับซ้อน", "พื้นที่"], timeout=1):
            smart_click(main_window, "ดำเนินการ")
    
    # เลือก Service
    wait_until_id_appears(main_window, "ShippingService_2579", timeout=15)
    smart_click(main_window, "ShippingService_2579") # คลิกเลือกบริการก่อน
    time.sleep(0.5)

    # 7.5 [NEW] ตรวจสอบและใส่วงเงินประกัน (Insurance) ถ้า Config เปิดไว้
    if str(add_insurance_flag).lower() in ['true', 'yes', 'on', '1']:
        log(f"...[Insurance] เปิดใช้งานประกันภัย: {insurance_amt}")
        if smart_click(main_window, ["CoverageButton", "ประกัน"], timeout=3):
            # หาช่องกรอกเงิน (CoverageAmount)
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=3):
                find_and_fill_smart(main_window, "Amount", "CoverageAmount", insurance_amt)
                main_window.type_keys("{ENTER}") # ยืนยันยอดเงิน
        else:
            log("[WARN] หาปุ่มประกันภัยไม่เจอ")

    # กด Enter เพื่อไปต่อ
    main_window.type_keys("{ENTER}")
    
    time.sleep(1); smart_next(main_window); time.sleep(step_delay)

    # 8. บริการพิเศษ & ข้อมูลผู้ส่ง (หน้าเต็ม)
    process_special_services(main_window, special_services)
    time.sleep(step_delay)
    process_sender_info_page(main_window) # ข้าม
    time.sleep(step_delay)
    
    # 9. ผู้รับ (Address & Details)
    # ค้นหาที่อยู่ (จะได้สถานะว่าต้องกรอกเองไหม)
    is_manual = process_receiver_address_selection(main_window, addr_keyword, manual_data)
    time.sleep(step_delay)
    
    # กรอกรายละเอียด (ส่ง manual_data ไปด้วยเผื่อต้องใช้)
    rcv_first = config['RECEIVER_DETAILS'].get('FirstName', 'A')
    rcv_last = config['RECEIVER_DETAILS'].get('LastName', 'B')
    process_receiver_details_form(main_window, rcv_first, rcv_last, phone, is_manual, manual_data)
    time.sleep(step_delay)
    
    # 10. ทำรายการซ้ำ (จุดตัดสินใจ)
    is_stop = process_repeat_transaction(main_window, repeat_flag)
    if is_stop:
        log("[SUCCESS] จบการทำงาน (เลือกทำรายการซ้ำ)")
        return
    
    # 11. ชำระเงิน (ถ้าไม่หยุด)
    pay_method = config['PAYMENT'].get('Method', 'เงินสด')
    pay_amt = config['PAYMENT'].get('ReceivedAmount', '1000')
    process_payment(main_window, pay_method, pay_amt)

    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

# ================= 5. Start App =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: เปิดโปรแกรม POS หรือยัง?")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")