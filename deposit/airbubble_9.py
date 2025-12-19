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

# ================= 2. Helper Functions =================

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    try:
        if not value or str(value).strip() == "":
            return False

        target_elem = None
        for child in window.descendants():
            if not child.is_visible(): continue
            
            aid = child.element_info.automation_id
            name = child.element_info.name
            
            if target_name and name and target_name in name:
                target_elem = child
                break
            if target_id_keyword and aid and target_id_keyword in aid:
                target_elem = child
                break
        
        if target_elem:
            log(f"   -> เจอช่อง '{target_name}/{target_id_keyword}' -> กรอก: {value}")
            try:
                edits = target_elem.descendants(control_type="Edit")
                if edits:
                    target_elem = edits[0]
            except: pass

            target_elem.set_focus()
            target_elem.click_input()
            target_elem.type_keys(str(value), with_spaces=True)
            return True
        else:
            log(f"[WARN] หาช่อง '{target_name}' ไม่เจอ")
            return False
            
    except Exception as e:
        log(f"[!] Error find_and_fill: {e}")
        return False
    
def click_scroll_arrow_smart(window, direction='right', repeat=5):
    try:
        target_group = window.descendants(auto_id="ShippingServiceList")
        if target_group:
            target_group[0].set_focus()
        else:
            window.set_focus()

        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        keys_string = key_code * repeat
        window.type_keys(keys_string, pause=0.2, set_foreground=False)
        return True
    except Exception as e:
        try:
             key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
             window.type_keys(key_code * repeat, pause=0.05)
             return True
        except:
            return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}' (โหมด Scroll, Limit={max_rotations} รอบ)...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False 

        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            if rect.right < safe_limit:
                 log(f"   [{i}] ✅ เจอปุ่มใน Safe Zone -> กำลังกด...")
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else:
                 log(f"   [{i}] ⚠️ เจอปุ่มแต่โดนบัง/อยู่ขวาสุด -> ต้องเลื่อน")
                 should_scroll = True
        else:
            log(f"   [{i}] ไม่เจอปุ่มในหน้านี้ -> เลื่อนขวา...")
            should_scroll = True
        
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5):
                window.type_keys("{RIGHT}")
            time.sleep(1.0)
        
    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}'")
    return False

def force_scroll_down(window, scroll_dist=-5):
    try:
        rect = window.rectangle()
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.05) 
    except Exception as e:
        log(f"[!] Scroll Error: {e}")
        try: window.type_keys("{PGDN}")
        except: pass

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

def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    text_match = criteria in child.window_text().strip()
                    id_match = criteria in str(child.element_info.automation_id)
                    
                    if child.is_visible() and (text_match or id_match):
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.3)
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=20, scroll_dist=-10):
    log(f"...ค้นหา '{criteria}' (โหมด V10: Turbo)...")
    loop_limit = max_scrolls + 10 
    
    for i in range(loop_limit):
        found_element = None
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                text_ok = criteria in child.window_text()
                id_ok = criteria in str(child.element_info.automation_id)
                if text_ok or id_ok:
                    found_element = child
                    break
        except: pass

        if found_element:
            try:
                elem_rect = found_element.rectangle()
                win_rect = window.rectangle()
                safe_bottom_limit = win_rect.bottom - 80
                
                if elem_rect.bottom >= safe_bottom_limit:
                    log(f"   [Turbo] เจอปุ่มอยู่ลึก -> กระชากขึ้นแรงๆ")
                    force_scroll_down(window, -60) 
                    time.sleep(0.1)
                    continue 
                
                found_element.click_input()
                log(f"   [/] เจอและกดปุ่ม '{criteria}' สำเร็จ")
                return True
            except Exception as e:
                log(f"   [!] Error: {e}")

        if i < loop_limit:
            if not found_element:
                force_scroll_down(window, scroll_dist)
            
    log(f"[X] หมดระยะเลื่อนหาแล้ว ไม่เจอปุ่ม '{criteria}'")
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
    if delay > 0: time.sleep(delay)
    try:
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2): return True
                else: window.type_keys("{ENTER}"); return True
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ", "Connect failed"], timeout=0.1): 
             log("[WARN] พบข้อความ Error บนหน้าจอ")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2): return True
             window.type_keys("{ENTER}"); return True
    except: pass
    return False

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, sender_postal):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input(); edit.type_keys(str(sender_postal), with_spaces=True)
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

def smart_input_generic(window, value, description="ข้อมูล"):
    log(f"...กำลังกรอก {description}: {value}...")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def process_special_services(window, services_str):
    log("--- หน้า: บริการพิเศษ ---")
    time.sleep(1.0) 
    if wait_for_text(window, ["บริการพิเศษ", "Services", "Special"], timeout=5):
        if services_str.strip():
            for s in services_str.split(','):
                s = s.strip()
                if s: 
                    log(f"...เลือกบริการเสริม: {s}")
                    smart_click_with_scroll(window, s, max_scrolls=5)
    else:
        log("[WARN] ไม่พบหน้าบริการพิเศษ หรือข้ามไปแล้ว")
    smart_next(window)

def process_sender_info_page(window):
    log("--- หน้า: ข้อมูลผู้ส่ง (ข้าม) ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    smart_next(window)

def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    is_manual_mode = False

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
            log("...เข้าสู่โหมดกรอกเอง (Manual Mode) -> รอส่งข้อมูลหน้าถัดไป...")
            is_manual_mode = True
            time.sleep(1.0)
            
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
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการ -> สันนิษฐานว่าเข้าหน้ากรอกเอง")
            is_manual_mode = True
            smart_next(window)

    return is_manual_mode

def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")
    time.sleep(2.0)

    if not wait_until_id_appears(window, "CustomerFirstName", timeout=15):
        log("[WARN] รอนานเกินไป ช่องชื่อยังไม่โผล่! (จะพยายามหาต่อ)")

    for _ in range(10):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            time.sleep(1.0)
        
        found = False
        for child in window.descendants():
            if "ชื่อ" in child.window_text() or "CustomerFirstName" in str(child.element_info.automation_id):
                found = True; break
        if found: break
        time.sleep(0.5)

    try:
        find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)
        find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

        need_force_fill = False
        if not is_manual_mode:
            try:
                edits = window.descendants(control_type="Edit")
                for edit in edits:
                    if "AdministrativeArea" in str(edit.element_info.automation_id) or "จังหวัด" in edit.element_info.name:
                        if not edit.get_value():
                            log("[Auto-Detect] พบช่องจังหวัดว่าง! -> บังคับเข้าโหมดกรอกเอง")
                            need_force_fill = True
                        break
            except: pass

        if is_manual_mode or need_force_fill:
            log("...[Manual/Force Mode] เริ่มกรอกที่อยู่ (ตามลำดับ 3-7)...")
            addr1 = manual_data.get('Address1', '')
            addr2 = manual_data.get('Address2', '')
            province = manual_data.get('Province', '')
            district = manual_data.get('District', '')
            subdistrict = manual_data.get('SubDistrict', '')

            if not find_and_fill_smart(window, "จังหวัด", "AdministrativeArea", province):
                window.type_keys("{TAB}"); window.type_keys(province, with_spaces=True)
            if not find_and_fill_smart(window, "เขต/อำเภอ", "Locality", district):
                window.type_keys("{TAB}"); window.type_keys(district, with_spaces=True)
            if not find_and_fill_smart(window, "แขวง/ตำบล", "DependentLocality", subdistrict):
                window.type_keys("{TAB}"); window.type_keys(subdistrict, with_spaces=True)
            find_and_fill_smart(window, "ที่อยู่ 1", "StreetAddress1", addr1)
            find_and_fill_smart(window, "ที่อยู่ 2", "StreetAddress2", addr2)

        force_scroll_down(window, -5)
        if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
             find_and_fill_smart(window, "โทร", "Phone", phone)

    except Exception as e: log(f"[!] Error Details: {e}")

    log("...จบขั้นตอนข้อมูลผู้รับ -> พยายามกด 'ถัดไป'...")
    for i in range(3):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=2.0):
             log("   [!] เจอ Popup 'ทำรายการซ้ำ' แล้ว -> หยุดกดถัดไปทันที")
             time.sleep(1.0) 
             break

        if check_error_popup(window, delay=0.5):
            log(f"   [!] พบ Popup แจ้งเตือน (รอบที่ {i+1}) -> ปิดและดำเนินการต่อ")
            
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window)
        time.sleep(2.0)

def process_repeat_transaction(window, should_repeat):
    log("--- หน้า: ทำรายการซ้ำ (ตรวจสอบ) ---")
    clean_flag = str(should_repeat).strip().lower().replace("'", "").replace('"', "")
    is_repeat_intent = clean_flag in ['true', 'yes', 'on', '1']
    found_popup = False
    
    for i in range(30):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=0.5):
            found_popup = True; break
        time.sleep(0.5)
        
    if found_popup:
        log("...เจอ Popup ทำรายการซ้ำ! กำลังเลือก...")
        time.sleep(1.0)
        target = "ใช่" if is_repeat_intent else "ไม่"
        if not smart_click(window, target, timeout=3):
            log("   [Click Fail] คลิกไม่โดน -> ใช้ Keyboard Shortcut (Fallback)")
            if target == "ไม่": window.type_keys("{ESC}")
            else: window.type_keys("{ENTER}")
        time.sleep(1.0)
    else: 
        log("[INFO] ไม่พบ Popup ทำรายการซ้ำ (ข้ามไปขั้นตอนถัดไป)")
    return is_repeat_intent

def process_payment(window, payment_method, received_amount):
    log("--- ขั้นตอนการชำระเงิน ---")
    if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=1.0):
        process_repeat_transaction(window, False)
        time.sleep(2.0)
    
    log("...ค้นหาปุ่ม 'รับเงิน'...")
    time.sleep(1.5)
    if smart_click(window, "รับเงิน"):
        time.sleep(1.5) 
    else:
        log("[WARN] หาปุ่มรับเงินไม่เจอ")
        return

    log(f"...เลือกวิธีชำระเงิน: {payment_method}...")
    wait_for_text(window, "รับชำระเงิน", timeout=5)
    if not smart_click(window, payment_method):
        log(f"[WARN] ไม่เจอ '{payment_method}' -> เลือก 'เงินสด' แทน")
        smart_click(window, "เงินสด")
    time.sleep(1.0)

    log(f"...กรอกจำนวนเงิน: {received_amount}...")
    try:
        for _ in range(10):
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                edits[0].click_input()
                edits[0].type_keys(str(received_amount), with_spaces=True)
                break
            time.sleep(0.5)
        window.type_keys("{ENTER}") 
    except: log("[!] Error กรอกเงิน")
    time.sleep(1.5)

    log("...หน้าเงินทอน -> กด Enter จบรายการ...")
    wait_for_text(window, ["เปลี่ยนแปลงจำนวนเงิน", "เงินทอน"], timeout=5)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main =================
def run_smart_scenario(main_window, config):
    try:
        category_name = "กล่องฟองอากาศ / โฟม" 
        category_id_fallback = "MailPieceShape_SubParent_CockFightingEquipments"
        product_detail = "วัสดุกันกระแทก (Air bubble) แบบม้วน 65+65+43 ซม."
        
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        width = config['DEPOSIT_ENVELOPE'].get('Width', '10')
        length = config['DEPOSIT_ENVELOPE'].get('Length', '20')
        height = config['DEPOSIT_ENVELOPE'].get('Height', '10')
        
        receiver_postal = config['DEPOSIT_ENVELOPE'].get('ReceiverPostalCode', '10110')
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')

        

        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', 'A')
        rcv_lname = config['RECEIVER_DETAILS'].get('LastName', 'B')
        rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '081')
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
        # อ่านค่า Config ประกัน (ปรับ Section ตามไฟล์ Config ของคุณ)
        # ถ้าอยู่ใน [DEPOSIT_ENVELOPE] หรือ [INSURANCE] ก็แก้ตรงนี้ได้เลย
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'

        manual_data = {
            'Address1': config['MANUAL_ADDRESS_FALLBACK'].get('Address1', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Address2': config['MANUAL_ADDRESS_FALLBACK'].get('Address2', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '') if 'MANUAL_ADDRESS_FALLBACK' in config else ''
        }
        
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log(f"--- เริ่มต้นการทำงาน (Full Flow) ---")
    time.sleep(0.5)

    # 1. เลือก รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    
    process_sender_info_popup(main_window, phone, sender_postal)
    time.sleep(step_delay)

    # 2. EMS สินค้าสำเร็จรูป
    if not smart_click_with_scroll(main_window, "EMS สินค้าสำเร็จรูป", scroll_dist=scroll_dist): 
        log("[Error] ไม่เจอเมนู EMS สินค้าสำเร็จรูป")
        return
    time.sleep(step_delay)

    # 3. เลือกหมวดหมู่ (รูป 1)
    log(f"...[Step 3] เลือกหมวดหมู่: {category_name}")
    time.sleep(2.0)
    
    found_category = False
    if smart_click_with_scroll(main_window, category_name, max_scrolls=10, scroll_dist=scroll_dist):
        found_category = True
        time.sleep(1.5) 
    elif smart_click_with_scroll(main_window, category_id_fallback, max_scrolls=10, scroll_dist=scroll_dist):
        found_category = True
        time.sleep(1.5)
        
    if not found_category:
        log(f"[WARN] หาหมวดหมู่ '{category_name}' ไม่เจอ -> จะพยายามกดถัดไป (เผื่อเลือก default)")
        smart_next(main_window)
    else:
        log("[OK] เลือกหมวดหมู่สำเร็จ -> (ข้ามการกดถัดไป เพื่อป้องกันการกดซ้ำที่หน้าถัดไป)")
        # [แก้ไขจุดที่ 1] ไม่กด smart_next() ตรงนี้ เพราะการคลิกเลือกมักจะพาไปหน้าถัดไปอยู่แล้ว
        # หรือถ้าไม่ไป ก็ปล่อยให้ Timeout หน้าถัดไปจัดการ หรือถ้าจำเป็นให้ uncomment บรรทัดล่างนี้
        # smart_next(main_window) 
        pass

    time.sleep(step_delay)

    # 4. เลือกรุปร่างชิ้นจดหมาย (รูป 2)
    log(f"...[Step 4] เลือกสินค้า: {product_detail}")
    # [แก้ไขจุดที่ 1 เพิ่มเติม] รอจนกว่าข้อความสินค้าจะขึ้นจริงๆ ก่อนกด เพื่อป้องกันการกดพลาด
    wait_for_text(main_window, product_detail[:10], timeout=5) 
    time.sleep(1.5)
    
    found_product = smart_click_with_scroll(main_window, product_detail, max_scrolls=20, scroll_dist=scroll_dist)
    if found_product:
        time.sleep(1.0) 
        log("[OK] เลือกสินค้าสำเร็จ -> กดถัดไป")
        smart_next(main_window)
    else:
        log(f"[WARN] หาสินค้า '{product_detail}' ไม่เจอ")
        # ถ้าหาไม่เจอ ก็กดถัดไปเผื่อฟลุ๊ค
        smart_next(main_window)
    
    time.sleep(step_delay)

    # 5. หน้า น้ำหนัก (รูป 3)
    log(f"...[Step 5] กรอกน้ำหนัก: {weight}")
    smart_input_generic(main_window, weight, "น้ำหนัก")
    smart_next(main_window)
    time.sleep(step_delay)

    # [แก้ไขจุดที่ 2] ลบ smart_next(main_window) ที่ซ้ำซ้อนตรงนี้ออก 
    # เพราะมันทำให้กดข้ามไปหน้า เลข ปณ (Step 7) ทันทีโดยไม่ได้ตั้งตัว
    # smart_next(main_window) <--- ลบออกแล้ว
    # time.sleep(step_delay)

    # 7. หน้า เลข ปณ ปลายทาง (รูป 4/5)
    log(f"...[Step 7] กรอก ปณ ปลายทาง: {receiver_postal}")
    # รอให้หน้าจอพร้อมรับค่าเล็กน้อย
    time.sleep(1.0)
    try: main_window.type_keys(str(receiver_postal), with_spaces=True)
    except: pass
    
    smart_next(main_window)
    time.sleep(step_delay)

    # --- ส่วนที่เชื่อมต่อกับโค้ดตัวอย่าง ---
    
    log("...เข้าสู่กระบวนการเดิม (ตรวจสอบพื้นที่ทับซ้อน/บริการขนส่ง)...")
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ"); found = True; break
        if found: break
        time.sleep(0.5)
    
    # =========================================================
    # [NEW LOGIC] จัดการ Popup ทับซ้อน และ Popup Error ที่ไปต่อไม่ได้
    # =========================================================
    log("...ตรวจสอบ Popup (พื้นที่ทับซ้อน / ไปต่อไม่ได้)...")
    
    # วนลูปเช็คประมาณ 3 วินาที (6 รอบ x 0.5s) เผื่อ Popup เด้งขึ้นมา
    for _ in range(6):
        try:
            # 1. เช็ค Popup "ไม่สามารถดำเนินการต่อไปได้" (Fatal Error)
            # ถ้าเจอ -> กดตกลง -> จบการทำงาน (Return)
            if wait_for_text(main_window, "ไม่สามารถดำเนินการต่อไปได้", timeout=0.2):
                log("[CRITICAL] พบแจ้งเตือน 'ไม่สามารถดำเนินการต่อไปได้' -> กำลังปิดและจบงาน")
                # พยายามกดปุ่มปิด/ตกลง
                if not smart_click(main_window, ["ตกลง", "OK", "ปิด"]):
                    main_window.type_keys("{ENTER}") # ถ้าหาปุ่มไม่เจอ กด Enter แทน
                
                log("!!! STOP PROCESS (จบการทำงานทันที) !!!")
                return # <--- คำสั่งนี้จะหยุดและออกจากฟังก์ชันทันที
            
            # 2. เช็ค Popup "พื้นที่ทับซ้อน" (Warning)
            # ถ้าเจอ -> กดดำเนินการ -> ไปต่อ
            found_overlap = False
            for child in main_window.descendants(control_type="Window"):
                txt = child.window_text()
                if "ทับซ้อน" in txt or "พื้นที่" in txt:
                    log(f"[Info] พบ Popup พื้นที่ทับซ้อน -> กด 'ดำเนินการ'")
                    if smart_click(main_window, "ดำเนินการ"):
                        found_overlap = True
                    else:
                        # ถ้าหาปุ่มไม่เจอ ลองกด Enter
                        main_window.type_keys("{ENTER}")
                        found_overlap = True
                    break
            
            if found_overlap:
                time.sleep(1.0) # รอหน้าจอโหลดหลังกดดำเนินการ
                continue # วนกลับไปเช็คอีกรอบ (เผื่อมี Error เด้งตามมาหลังกดดำเนินการ)

        except: pass
        time.sleep(0.5)
    # =========================================================

    wait_until_id_appears(main_window, "ShippingService_363244", timeout=15)
    if find_and_click_with_rotate_logic(main_window, "ShippingService_363244"):
        main_window.type_keys("{ENTER}")
    

    if add_insurance_flag.lower() in ['true', 'yes']:
        log(f"...ใส่วงเงิน {insurance_amt}...")
        if click_element_by_id(main_window, "CoverageButton"):
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
                for child in main_window.descendants():
                    if child.element_info.automation_id == "CoverageAmount":
                        child.click_input(); child.type_keys(str(insurance_amt), with_spaces=True); break
                time.sleep(0.5)
                submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
                submits.sort(key=lambda x: x.rectangle().top)
                if submits: submits[0].click_input()
                else: main_window.type_keys("{ENTER}")
    
    time.sleep(1)
    smart_next(main_window)
    time.sleep(step_delay)

    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    process_sender_info_page(main_window)
    time.sleep(step_delay)
    
    is_manual_mode = process_receiver_address_selection(main_window, addr_keyword, manual_data)
    time.sleep(step_delay)
    
    process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone, is_manual_mode, manual_data)
    time.sleep(step_delay)
    
    is_repeat_mode = process_repeat_transaction(main_window, repeat_flag)
    if is_repeat_mode:
        log("[Logic] ตรวจสอบพบโหมดทำรายการซ้ำ -> หยุดการทำงานทันที")
        return
    
    process_payment(main_window, pay_method, pay_amount)
    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

if __name__ == "__main__":
    target_config = 'config.ini' 
    conf = load_config(target_config)
    if conf:
        log(f"Connecting... (Using Config: {target_config})")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to Title: {app_title}")
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