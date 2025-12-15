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

def fill_manual_address(window, manual_data):
    """กรอกที่อยู่เองเมื่อเกิด Error/Popup (ดึงค่าจาก Config)"""
    log("...เข้าสู่โหมดกรอกที่อยู่ด้วยตนเอง (Manual Fallback)...")
    province = manual_data.get('Province', '')
    district = manual_data.get('District', '')
    subdistrict = manual_data.get('SubDistrict', '')
    log(f"   -> ข้อมูล: {province} > {district} > {subdistrict}")
    try:
        log("...รอโหลดช่องกรอกข้อมูล...")
        address_edits = []
        for _ in range(10): 
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            curr_edits = [e for e in edits if e.rectangle().top < 500]
            if len(curr_edits) >= 4: address_edits = curr_edits; break
            time.sleep(0.5)

        address_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
        
        def check_and_fill(edit_elem, value, name):
            try:
                curr_val = edit_elem.get_value()
                if curr_val and len(str(curr_val).strip()) > 0:
                    log(f"...ช่อง '{name}' มีข้อมูลแล้ว ({curr_val}) -> ข้าม")
                else:
                    log(f"...ช่อง '{name}' ว่าง -> กรอก: {value}")
                    edit_elem.click_input(); edit_elem.type_keys(str(value), with_spaces=True)
            except:
                edit_elem.click_input(); edit_elem.type_keys(str(value), with_spaces=True)

        if len(address_edits) >= 4:
            # [0]=Zip, [1]=Province, [2]=District, [3]=SubDistrict
            check_and_fill(address_edits[1], province, "จังหวัด")
            check_and_fill(address_edits[2], district, "เขต/อำเภอ")
            check_and_fill(address_edits[3], subdistrict, "แขวง/ตำบล")
        else:
            log("[!] หาช่องกรอกไม่ครบ -> ใช้การกด Tab")
            window.type_keys("{TAB}")
            window.type_keys(province, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(district, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(subdistrict, with_spaces=True)
    except Exception as e:
        log(f"[!] Error กรอกที่อยู่เอง: {e}")

def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        try:
            search_ready = False
            for _ in range(10):
                edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
                if edits: search_ready = True; break
                time.sleep(0.5)
            
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    edit.click_input(); edit.type_keys(str(address_keyword), with_spaces=True)
                    filled = True; break
            if not filled and len(edits) > 1:
                edits[1].click_input(); edits[1].type_keys(str(address_keyword), with_spaces=True)
        except: pass

        log("...กด Enter/ถัดไป เพื่อค้นหารายการ...")
        smart_next(window)
        time.sleep(1.0) 
        
        log("...ตรวจสอบผลลัพธ์ (Popup/List)...")
        found_popup = False; found_list = False
        
        for _ in range(40): 
            if check_error_popup(window, delay=0.0):
                log("[WARN] ตรวจพบ Popup คำเตือน! -> ปิดแล้วเข้าสู่โหมดกรอกเอง")
                found_popup = True; break
            list_items = [i for i in window.descendants(control_type="ListItem") 
                          if i.is_visible() and i.rectangle().top > 200]
            if list_items: found_list = True; break
            time.sleep(0.25)

        if found_popup:
            time.sleep(1.0)
            fill_manual_address(window, manual_data)
            smart_next(window) # Manual ต้องกดถัดไป
            
        elif found_list:
            log("...เจอรายการที่อยู่ -> เลือกรายการแรกสุด...")
            time.sleep(1.0)
            try:
                all_list_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible()]
                valid_items = [i for i in all_list_items if i.rectangle().top > 200 and i.rectangle().height() > 50]
                if valid_items:
                    valid_items.sort(key=lambda x: x.rectangle().top)
                    target_item = valid_items[0]
                    log(f"[/] Click รายการที่: (Y={target_item.rectangle().top})")
                    try: target_item.set_focus()
                    except: pass
                    target_item.click_input()
                    log("...เลือกรายการแล้ว รอโหลดข้อมูล (2.0s)...")
                    time.sleep(2.0) 
                else: log("[!] เจอ List แต่กรองความสูงไม่ผ่าน")
            except: pass
            # เลือก List แล้ว ไม่ต้องกด Next ซ้ำ
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการ -> ลองกดถัดไป")
            smart_next(window)

def process_receiver_details_form(window, fname, lname, phone):
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด...")
    for i in range(15):
        if wait_for_text(window, ["ชื่อ", "นามสกุล", "คำนำหน้า"], timeout=1): break
        time.sleep(0.5)
    check_error_popup(window); time.sleep(1.0)

    try:
        log("...ตรวจสอบช่องกรอกชื่อ/นามสกุล...")
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        top_edits = [e for e in edits if 150 < e.rectangle().top < 550]
        top_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
        
        name_edit, surname_edit = None, None
        if len(top_edits) >= 2:
            first_y = top_edits[0].rectangle().top
            first_row = [e for e in top_edits if abs(e.rectangle().top - first_y) < 15]
            if len(first_row) >= 3: name_edit = first_row[1]; surname_edit = first_row[-1]
            elif len(first_row) == 2: name_edit = first_row[0]; surname_edit = first_row[1]
            else: name_edit = top_edits[0]; surname_edit = top_edits[1]

        def fill_if_empty(edit_ui, value, field_name):
            if edit_ui:
                val = edit_ui.get_value()
                if val and len(str(val).strip()) > 0:
                    log(f"...ช่อง '{field_name}' มีข้อมูลแล้ว ({val}) -> ข้าม")
                else:
                    log(f"...ช่อง '{field_name}' ว่าง -> กรอก: {value}")
                    edit_ui.click_input(); edit_ui.type_keys(value, with_spaces=True)

        if name_edit and surname_edit:
            fill_if_empty(name_edit, fname, "ชื่อ")
            fill_if_empty(surname_edit, lname, "นามสกุล")
        else: log("[WARN] ระบุช่องชื่อ/นามสกุลไม่ชัดเจน -> ข้าม")

        log("...เลื่อนลงเพื่อตรวจสอบเบอร์โทร...")
        force_scroll_down(window, -10); time.sleep(1)
        
        found_phone = False
        visible_edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        for edit in visible_edits:
            if "โทร" in edit.element_info.name or "Phone" in edit.element_info.automation_id:
                fill_if_empty(edit, phone, "เบอร์โทร")
                found_phone = True; break
        if not found_phone:
            log("[!] หาช่องเบอร์ไม่เจอ -> ลองกด Tab")
            window.type_keys("{TAB}"*3); window.type_keys(phone, with_spaces=True)
    except Exception as e: log(f"[!] Error Details: {e}")

    log("...จบขั้นตอนข้อมูลผู้รับ -> กด 'ถัดไป' 3 ครั้ง...")
    for i in range(3):
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window); time.sleep(1.8)

def process_repeat_transaction(window, should_repeat):
    log("--- หน้า: ทำรายการซ้ำ (รอ Popup) ---")
    found_popup = False
    for i in range(30):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=0.5):
            found_popup = True; break
        time.sleep(0.5)
        
    if found_popup:
        log("...เจอ Popup ทำรายการซ้ำ...")
        time.sleep(1.0)
        target = "ใช่" if str(should_repeat).lower() in ['true', 'yes', 'on', '1'] else "ไม่"
        log(f"...Config: {should_repeat} -> เลือก: '{target}'")
        if not smart_click(window, target, timeout=3):
            if target == "ไม่": window.type_keys("{ESC}")
            else: window.type_keys("{ENTER}")
    else: log("[WARN] ไม่พบ Popup ทำรายการซ้ำ (Timeout)")

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
        # ใช้ EMSS หรือคำค้นหาสำรองกรณีหา ID ตรงๆ ไม่เจอ
        if not click_element_by_fuzzy_id(main_window, "EMSS"): return
    
    # ลบการกด Enter ทิ้งไปก่อนหน้านี้ เพราะเราจะไปจัดการใน Popup แทน
    # main_window.type_keys("{ENTER}") <--- ลบบรรทัดนี้ออก หรือ comment ไว้
    
    log("...รอ Popup จำนวน...")
    time.sleep(1.5) # รอ Animation Popup เด้งนานขึ้นนิดนึง

    # --- [UPDATED] ส่วนจัดการ Popup จำนวน (แก้ไขใหม่) ---
    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    
    found_popup = False
    # ลองหา 5 รอบ (ประมาณ 5 วินาที)
    for i in range(5): 
        try:
            # 1. หาช่อง Edit ที่ Visible ทั้งหมดบนหน้าจอ ณ ตอนนั้น
            # การหาแบบนี้จะเจอช่อง Edit บน Popup เพราะ Popup บังหน้าจออื่นอยู่
            all_edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
            
            # กรองเฉพาะช่องที่ขนาดสมเหตุสมผล (ไม่เล็กเกินไปจนมองไม่เห็น)
            valid_edits = [e for e in all_edits if e.rectangle().height() > 10 and e.rectangle().width() > 20]

            if valid_edits:
                # ปกติช่องกรอกจำนวนจะเป็นช่อง Edit ตัวแรก หรือตัวเดียวที่ Active อยู่บน Popup
                target_edit = valid_edits[0]
                
                log(f"...เจอช่องกรอกจำนวน (Run {i+1}) -> คลิกและกรอกค่า {qty}...")
                
                # A. คลิกที่ช่องเพื่อให้ Focus (แก้ปัญหาหน้าจอเปลี่ยนขนาด)
                try: target_edit.click_input()
                except: pass
                
                # B. สั่ง Focus โดยตรง (เผื่อ Click ไม่ติด)
                try: target_edit.set_focus()
                except: pass
                
                time.sleep(0.3)
                
                # C. ล้างค่าเก่า (Ctrl+A -> Delete)
                target_edit.type_keys("^a{DELETE}", pause=0.1)
                time.sleep(0.2)
                
                # D. พิมพ์เลขใหม่
                target_edit.type_keys(str(qty), with_spaces=True)
                time.sleep(0.5)
                
                # E. กด Enter ที่ช่องนั้นเลย (เหมือนกดปุ่มถัดไปใน Popup)
                target_edit.type_keys("{ENTER}")
                
                found_popup = True
                break
            else:
                log(f"Run {i+1}: ยังไม่เจอช่อง Edit ใน Popup... รอสักครู่")

        except Exception as e:
            log(f"Error หา Popup: {e}")
        
        time.sleep(0.8)

    if not found_popup:
        log("Warning: ไม่เจอ Popup จำนวน หรือหาช่องกรอกไม่เจอ -> ลองกด Enter เผื่อผ่าน")
        main_window.type_keys("{ENTER}")
    
    # --- [สำคัญ] รอให้ Popup หายไปและหน้าใหม่โหลดเสร็จ ---
    log("...รอหน้าถัดไปโหลด (ป้องกันการกดข้าม)...")
    time.sleep(2.0) 
    
    # [NEW LOGIC] ตรวจสอบว่าข้ามไปหน้า "ทำรายการซ้ำ" เลยหรือไม่
    # ถ้าบริการนี้ (เช่น ซองจดหมาย) ข้ามขั้นตอนกลางไปเลย เราจะเช็คหน้า "ทำรายการซ้ำ" ก่อน
    is_repeat_page = wait_for_text(main_window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=2)

    if not is_repeat_page:
        # ถ้ายังไม่เจอหน้าทำรายการซ้ำ แสดงว่าเป็น Flow ปกติ -> ทำขั้นตอน Sender/Receiver ตามเดิม
        
        # เช็คว่าอยู่หน้าบริการพิเศษจริงไหม ก่อนกดถัดไป
        if wait_for_text(main_window, ["บริการพิเศษ", "Special Services"], timeout=3):
             process_special_services(main_window, special_services)
        else:
             log("[Info] ไม่เจอคำว่า 'บริการพิเศษ' -> อาจจะข้ามหน้านี้ไปแล้ว")

        time.sleep(step_delay)
        process_sender_info_page(main_window)
        
        time.sleep(step_delay)
        # เพิ่ม Timeout ในการรอหน้าข้อมูลผู้รับ เพราะบางทีเน็ตช้า
        log("...เข้าสู่ขั้นตอนค้นหาผู้รับ...")
        process_receiver_address_selection(main_window, addr_keyword, manual_data)
        
        time.sleep(step_delay)
        process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone)
        
        time.sleep(step_delay)
    else:
        log("...ระบบข้ามไปหน้า 'ทำรายการซ้ำ' ทันที (Skip Intermediate Steps)...")
    
    # --- จบส่วนจัดการ Popup และ Flow กลาง ---
    
    # ทำรายการซ้ำ (กด ใช่/ไม่)
    process_repeat_transaction(main_window, repeat_flag)
    
    # ชำระเงิน (ต่อจากทำรายการซ้ำ)
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