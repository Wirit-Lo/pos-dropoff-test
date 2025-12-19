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
    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        window.set_focus()
        rect = window.rectangle()
        center_x = rect.left + int(rect.width() * 0.5)
        center_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.2)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
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
    log(f"...ค้นหา '{criteria}' (Scroll)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found = child; break
        except: pass
        if found:
            try:
                elem_rect = found.rectangle()
                win_rect = window.rectangle()
                if elem_rect.bottom >= win_rect.bottom - 70:
                    force_scroll_down(window, -3); time.sleep(0.5); continue 
                found.click_input()
                log(f"   [/] เจอและกด '{criteria}' สำเร็จ")
                return True
            except: pass
        if i < max_scrolls: force_scroll_down(window, scroll_dist)
    return False

def click_element_by_id(window, exact_id, timeout=5, index=0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if len(found) > index:
                found[index].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
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
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(1)
    return False

def wait_for_text(window, text_list, timeout=5):
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible(): return True
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
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def check_error_popup(window, delay=0.5):
    """เช็ค Popup และกดปิด"""
    if delay > 0: time.sleep(delay)
    try:
        # 1. เช็คหน้าต่าง Popup
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2): return True
                else: window.type_keys("{ENTER}"); return True
        # 2. เช็ค Text บนหน้าจอ
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ", "Connect failed"], timeout=0.1): 
             log("[WARN] พบข้อความ Error บนหน้าจอ")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2): return True
             window.type_keys("{ENTER}"); return True
    except: pass
    return False

# [NEW] Helper Functions สำหรับ Logic ใหม่
def safe_type_keys(element, value):
    """ฟังก์ชันช่วยพิมพ์แบบปลอดภัย ป้องกันการพิมพ์เมื่อ Element หาย"""
    try:
        element.set_focus()
        element.click_input()
        # ใช้การเลือกทั้งหมดแล้วพิมพ์ทับ เพื่อป้องกันค่าเก่าค้าง
        element.type_keys("^a{DELETE}", set_foreground=False) 
        element.type_keys(str(value), with_spaces=True, set_foreground=False)
        return True
    except Exception as e:
        log(f"[Warn] พิมพ์ข้อมูลล้มเหลว: {e}")
        return False

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    """ค้นหาและกรอกข้อมูล (Optimized Version)"""
    try:
        if not value or str(value).strip() == "": return True # ข้ามถ้าไม่มีข้อมูล

        target_elem = None
        all_elements = window.descendants() # ดึงครั้งเดียวเพื่อความเร็ว

        for child in all_elements:
            if not child.is_visible(): continue
            aid = child.element_info.automation_id
            name = child.element_info.name
            
            match_name = target_name and name and target_name in name
            match_id = target_id_keyword and aid and target_id_keyword in aid
            
            if match_name or match_id:
                target_elem = child
                if match_name: break 

        if target_elem:
            log(f"   -> เจอช่อง '{target_name or target_id_keyword}' -> กำลังกรอก...")
            try:
                edits = target_elem.children(control_type="Edit")
                if edits: target_elem = edits[0]
            except: pass
            return safe_type_keys(target_elem, value)
        else:
            log(f"[WARN] หาช่อง '{target_name or target_id_keyword}' ไม่เจอ")
            return False
    except Exception as e:
        log(f"[!] Error find_and_fill: {e}")
        return False

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, postal):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input(); edit.type_keys(str(postal), with_spaces=True)
                    break 
        except: pass
        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input(); edit.type_keys(str(phone), with_spaces=True)
                        found_phone = True; break
            except: pass
            if found_phone: break
            force_scroll_down(window, -5)
        smart_next(window)

def handle_prohibited_items(window):
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}"); return
        except: pass
        time.sleep(0.5)

def smart_input_weight(window, value):
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input(); edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

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

# [REPLACED] Logic ใหม่สำหรับการค้นหาที่อยู่ (คืนค่า is_manual_mode)
def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- [Step 1] ค้นหาที่อยู่: {address_keyword} ---")
    
    # 1. เช็ค Popup ค้าง
    if check_error_popup(window, delay=1.0):
        log("[Warn] พบ Popup ค้างจากรอบก่อน -> ปิดแล้ว")

    # 2. หาช่องค้นหาและพิมพ์
    search_box = None
    for _ in range(5):
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            for edit in edits:
                if "ที่อยู่" in str(edit.element_info.name) or "Search" in str(edit.element_info.automation_id) or not edit.get_value():
                    search_box = edit
                    break
            if search_box: break
        except: pass
        time.sleep(0.5)

    if search_box:
        safe_type_keys(search_box, address_keyword)
        log("...กด Enter เพื่อค้นหา...")
        smart_next(window)
    else:
        log("[Warn] ไม่เจอช่องค้นหาที่อยู่ -> อาจต้อง Manual")

    # 3. รอผลลัพธ์
    log("...รอผลลัพธ์ (Popup/List)...")
    is_manual_mode = False
    
    for _ in range(20):
        if check_error_popup(window, delay=0.1):
            log("[Info] เจอ Popup แจ้งเตือน -> เข้า Manual Mode")
            is_manual_mode = True
            break
            
        list_items = [i for i in window.descendants(control_type="ListItem") 
                      if i.is_visible() and i.rectangle().height() > 30]
        
        if list_items:
            valid_items = [i for i in list_items if i.rectangle().top > 150]
            if valid_items:
                target = valid_items[0]
                try:
                    log(f"[/] เลือกที่อยู่อัตโนมัติ: {target.window_text()[:30]}...")
                    target.click_input()
                    time.sleep(1.0)
                    return False # เจอ Auto แล้ว
                except: pass
        time.sleep(0.5)

    if not is_manual_mode:
        log("[Warn] ไม่เจอรายการเลือก -> บังคับเข้า Manual Mode")
        is_manual_mode = True
        smart_next(window)

    return is_manual_mode

# [REPLACED] Logic ใหม่สำหรับกรอกรายละเอียด (รองรับ Manual Mode ในตัว)
def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    log(f"--- [Step 2] รายละเอียดผู้รับ (Manual: {is_manual_mode}) ---")
    
    # รอฟอร์มโหลด
    for _ in range(10):
        if check_error_popup(window): continue
        try:
             if window.descendants(control_type="Edit"): break
        except: pass
        time.sleep(0.5)

    # 1. ชื่อ-นามสกุล (Auto/Manual ต้องกรอกเสมอ)
    find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)
    find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

    # 2. กรอกที่อยู่ (เฉพาะ Manual Mode)
    if is_manual_mode:
        log("...[Manual Mode] กำลังกรอกที่อยู่ละเอียด...")
        # key ต้องตรงกับ configparser (ระวังตัวพิมพ์เล็กใหญ่)
        fields_map = [
            ("จังหวัด", "AdministrativeArea", manual_data.get('Province')),
            ("เขต/อำเภอ", "Locality", manual_data.get('District')),
            ("แขวง/ตำบล", "DependentLocality", manual_data.get('SubDistrict')),
            ("ที่อยู่ 1", "StreetAddress1", manual_data.get('Address1') or manual_data.get('address1')),
            ("ที่อยู่ 2", "StreetAddress2", manual_data.get('Address2') or manual_data.get('address2')),
        ]
        for name_kw, id_kw, val in fields_map:
            find_and_fill_smart(window, name_kw, id_kw, val)

    # 3. เบอร์โทร
    force_scroll_down(window, -5)
    if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
         find_and_fill_smart(window, "โทร", "Phone", phone)

    log("...เสร็จสิ้นหน้าข้อมูลผู้รับ -> กดถัดไป...")
    smart_next(window)
    time.sleep(1.0)
    for i in range(2): 
        smart_next(window); time.sleep(1.0)

def process_repeat_transaction(window, should_repeat):
    """
    จัดการ popup และส่งค่ากลับ (Return) ว่าสรุปแล้วคือการทำรายการซ้ำหรือไม่
    """
    log("--- หน้า: ทำรายการซ้ำ (รอ Popup) ---")
    
    # 1. ตีความค่า Config ให้ชัดเจน (ลบ Space, ลบ Quote, ตัวเล็ก)
    clean_flag = str(should_repeat).strip().lower().replace("'", "").replace('"', "")
    is_repeat_intent = clean_flag in ['true', 'yes', 'on', '1']
    
    found_popup = False
    for i in range(30):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=0.5):
            found_popup = True; break
        time.sleep(0.5)
        
    if found_popup:
        log("...เจอ Popup ทำรายการซ้ำ...")
        time.sleep(1.0)
        
        target = "ใช่" if is_repeat_intent else "ไม่"
        log(f"...Config: {should_repeat} -> Intent: {is_repeat_intent} -> เลือก: '{target}'")
        
        if not smart_click(window, target, timeout=3):
            if target == "ไม่": window.type_keys("{ESC}")
            else: window.type_keys("{ENTER}")
    else: 
        log("[WARN] ไม่พบ Popup ทำรายการซ้ำ (Timeout)")

    # สำคัญ: ส่งค่าความตั้งใจกลับไปบอกฟังก์ชันหลัก
    return is_repeat_intent


def process_payment(window, payment_method, received_amount):
    log("--- ขั้นตอนการชำระเงิน ---")
    # 1. กดรับเงิน (หน้าหลัก)
    log("...ค้นหาปุ่ม 'รับเงิน'...")
    # รอให้หน้าจอพร้อมสักนิดหลังปิด Popup Repeat
    time.sleep(1.5)
    if smart_click(window, "รับเงิน"):
        time.sleep(1.5) # รอหน้าชำระเงิน
    else:
        log("[WARN] หาปุ่มรับเงินไม่เจอ")
        return

    # 2. เลือกวิธีชำระเงิน
    log(f"...เลือกวิธีชำระเงิน: {payment_method}...")
    wait_for_text(window, "รับชำระเงิน", timeout=5)
    if not smart_click(window, payment_method):
        log(f"[WARN] ไม่เจอ '{payment_method}' -> เลือก 'เงินสด' แทน")
        smart_click(window, "เงินสด")
    time.sleep(1.0)

    # 3. กรอกจำนวนเงิน (Popup)
    log(f"...กรอกจำนวนเงิน: {received_amount}...")
    try:
        # รอ Edit box
        for _ in range(10):
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                edits[0].click_input()
                edits[0].type_keys(str(received_amount), with_spaces=True)
                break
            time.sleep(0.5)
        window.type_keys("{ENTER}") # กดถัดไป
    except: log("[!] Error กรอกเงิน")
    time.sleep(1.5)

    # 4. หน้าเงินทอน (จบ)
    log("...หน้าเงินทอน -> กด Enter จบรายการ...")
    wait_for_text(window, ["เปลี่ยนแปลงจำนวนเงิน", "เงินทอน"], timeout=5)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', 'A')
        rcv_lname = config['RECEIVER_DETAILS'].get('LastName', 'B')
        rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '081')
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
        
        # Payment Config
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'
        
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        wait_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))

        manual_data = {
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '') if 'MANUAL_ADDRESS_FALLBACK' in config else ''
        }
    except: log("[Error] อ่าน Config ไม่สำเร็จ"); return

    log(f"--- เริ่มต้นการทำงาน ---")
    time.sleep(0.5)

    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    process_sender_info_popup(main_window, phone, postal) 
    time.sleep(step_delay)
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            if opt: smart_click(main_window, opt.strip(), timeout=2)
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)
    handle_prohibited_items(main_window)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ"); found = True; break
        if found: break
        time.sleep(0.5)

    log("...รอหน้าบริการหลัก...")
    wait_until_id_appears(main_window, "ShippingService_2580", timeout=wait_timeout)
     # คลิก 1 ครั้ง
    if not click_element_by_id(main_window, "ShippingService_2580"):
        log("[Error] หาปุ่มบริการไม่เจอ (ShippingService_2580)")
        return

    # [เพิ่ม] กด Enter (ถัดไป) เพื่อเรียก Popup ขึ้นมา
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(0.5)
    main_window.type_keys("{ENTER}")

    # 2. เริ่มกระบวนการจัดการ Popup
    # ดึงค่าจาก Config ตามที่ต้องการ
    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (จะใส่เลขจาก Config: {qty})...")
    
    time.sleep(1.5) # รอ Animation Popup เด้ง

    # --- [DEBUG MODE] ค้นหา Popup ---
    popup_window = None
    
    # วิธีที่ 1: หาจาก Child Window ของ Main
    try:
        children = main_window.children(control_type="Window")
        if children:
            popup_window = children[0]
            log(f"-> เจอ Child Window: {popup_window.window_text()}")
    except: pass

    # วิธีที่ 2: ถ้าไม่เจอ ให้ใช้ Top Window (หน้าต่างที่อยู่บนสุดของ Windows)
    if not popup_window:
        try:
            # เชื่อมต่อกับ Window ที่ Active อยู่ (น่าจะเป็น Popup)
            app_top = Application(backend="uia").connect(active_only=True).top_window()
            log(f"-> ตรวจสอบ Top Window: {app_top.window_text()}")
            # ตรวจสอบชื่อหน้าต่างว่าน่าจะเป็น Popup ไหม (บางทีไม่มีชื่อ แต่เป็น Dialog)
            if "จำนวน" in app_top.window_text() or "Escher" in app_top.window_text() or app_top.element_info.control_type == "Window":
                popup_window = app_top
        except Exception as e:
            log(f"-> Error หา Top Window: {e}")

    # --- เริ่มเจาะหาช่อง Edit ---
    if popup_window:
        try:
            popup_window.set_focus()
        except: pass
        
        log("...กำลังสแกนหาช่อง Edit ใน Popup...")
        
        target_edit = None
        
        # ดึง Edit ทั้งหมดออกมาดู
        try:
            edits = popup_window.descendants(control_type="Edit")
            visible_edits = [e for e in edits if e.is_visible()]
            
            log(f"-> พบ Edit ทั้งหมด: {len(edits)} ช่อง (Visible: {len(visible_edits)})")
            
            if visible_edits:
                # กรองช่องที่เล็กเกินไป (พวกปุ่มซ่อน)
                valid_edits = [e for e in visible_edits if e.rectangle().width() > 30]
                
                if valid_edits:
                    target_edit = valid_edits[0]
                    log(f"-> เป้าหมาย: {target_edit} (ID: {target_edit.element_info.automation_id})")
                else:
                    log("[!] เจอ Edit แต่ขนาดเล็กผิดปกติ")
            else:
                log("[!] ไม่เจอช่อง Edit ที่มองเห็นได้เลย")
        except Exception as e:
            log(f"Error สแกนหา Edit: {e}")

        # ถ้าเจอช่องแล้ว ให้กระทำการ
        if target_edit:
            try:
                # 1. Focus
                target_edit.click_input()
                time.sleep(0.2)
                
                # 2. Clear
                target_edit.type_keys("^a", pause=0.1)
                target_edit.type_keys("{DELETE}", pause=0.1)
                
                # 3. Type
                target_edit.type_keys(str(qty), with_spaces=True)
                log(f"-> พิมพ์เลข {qty} เรียบร้อย")
                time.sleep(0.5)
                
                # 4. Enter
                popup_window.type_keys("{ENTER}")
                log("-> กด Enter (ถัดไป) เรียบร้อย")
                
            except Exception as e:
                log(f"Error ขณะพิมพ์: {e}")
        else:
            # ถ้าหา Edit ไม่เจอจริงๆ ลองวิธีสุดท้าย: พิมพ์ดื้อๆ ใส่ Popup Window
            log("[Warning] หาช่องไม่เจอ -> ลองพิมพ์ใส่ Window โดยตรง (Blind Type)")
            popup_window.type_keys(str(qty), with_spaces=True)
            popup_window.type_keys("{ENTER}")

    else:
        log("[Error] หา Popup Window ไม่เจอเลย (อาจจะเด้งช้าหรือจับผิดตัว)")

    # --- จบส่วน Popup ---

    # --- [ส่วนตรวจจับการข้ามหน้า] ---
    log("...รอหน้าถัดไปโหลด (2.0s)...")
    time.sleep(2.0) 
    
    # รีเฟรช main_window เผื่อ Popup หายไปแล้ว focus เปลี่ยน
    try: main_window.set_focus()
    except: pass

    # เช็คว่าข้ามไปหน้า "ทำรายการซ้ำ" เลยไหม
    is_repeat_page = wait_for_text(main_window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=2)

    if not is_repeat_page:
        # Flow ปกติ: บริการพิเศษ -> ผู้ส่ง -> ผู้รับ
        if wait_for_text(main_window, ["บริการพิเศษ", "Special Services"], timeout=3):
             process_special_services(main_window, special_services)
        
        time.sleep(step_delay)
        process_sender_info_page(main_window)
        
        time.sleep(step_delay)
        # (แก้ไขให้รับตัวแปร is_manual_mode)
        log("...เข้าสู่ขั้นตอนค้นหาผู้รับ...")
        
        # [NEW] รับค่า is_manual_mode มาเก็บไว้
        is_manual_mode = process_receiver_address_selection(main_window, addr_keyword, manual_data)
        
        time.sleep(step_delay)
        
        # [NEW] ส่งค่า is_manual_mode และ manual_data เข้าไป
        process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone, is_manual_mode, manual_data)
        
        time.sleep(step_delay)
    else:
        log("...ระบบข้ามไปหน้า 'ทำรายการซ้ำ' ทันที (เจอ Popup ทำซ้ำ)...")
    
    # --- จบส่วนจัดการ Popup และ Flow กลาง ---
    
    # 1. เรียกฟังก์ชัน และรับค่ากลับมา (ตัวแปรนี้จะได้ค่า True/False จากจุดที่ 1)
    is_repeat_mode = process_repeat_transaction(main_window, repeat_flag)
    
    # 2. เช็คเลยว่า ถ้าเป็นจริง -> จบการทำงาน
    if is_repeat_mode:
        log("[Logic] ตรวจสอบพบโหมดทำรายการซ้ำ -> หยุดการทำงานทันที")
        return # ออกจากฟังก์ชันทันที
    
    # 3. ถ้าไม่เข้าเงื่อนไขบน ก็จะลงมาทำชำระเงินต่อ
    process_payment(main_window, pay_method, pay_amount)

    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

# ================= 5. Start App =================
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
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")
    