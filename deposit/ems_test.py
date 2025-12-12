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

def wait_for_text(window, text_list, timeout=5):
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible():
                        return True
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
        # 1. เช็คหน้าต่าง Popup (Window Control)
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2):
                    return True
                else:
                    window.type_keys("{ENTER}")
                    return True
        # 2. เช็ค Text บนหน้าจอ
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ", "Connect failed"], timeout=0.1): 
             log("[WARN] พบข้อความ Error บนหน้าจอ")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2):
                 return True
             window.type_keys("{ENTER}") 
             return True
    except: pass
    return False

# ================= 3. Logic หลัก =================

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
    """ฟังก์ชันกรอกที่อยู่เอง (ทำงานเมื่อมี Popup แจ้งเตือน)"""
    log("...เข้าสู่โหมดกรอกที่อยู่ด้วยตนเอง (Manual Fallback)...")
    
    province = manual_data.get('Province', '')
    district = manual_data.get('District', '')
    subdistrict = manual_data.get('SubDistrict', '')
    
    log(f"   -> ข้อมูลจาก Config: {province} > {district} > {subdistrict}")

    try:
        # รอโหลดช่องกรอกข้อมูล
        log("...รอโหลดช่องกรอกข้อมูล...")
        address_edits = []
        for _ in range(10): 
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            curr_edits = [e for e in edits if e.rectangle().top < 500]
            if len(curr_edits) >= 4:
                address_edits = curr_edits
                break
            time.sleep(0.5)

        address_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
        
        # ฟังก์ชันช่วยเช็คและกรอก (ป้องกันการกรอกซ้ำ)
        def check_and_fill(edit_elem, value, name):
            try:
                curr_val = edit_elem.get_value()
                if curr_val and len(str(curr_val).strip()) > 0:
                    log(f"...ช่อง '{name}' มีข้อมูลแล้ว ({curr_val}) -> ข้าม")
                else:
                    log(f"...ช่อง '{name}' ว่าง -> กรอก: {value}")
                    edit_elem.click_input()
                    edit_elem.type_keys(str(value), with_spaces=True)
            except:
                log(f"[!] ตรวจสอบค่าไม่ได้ -> ลองกรอกทับ")
                edit_elem.click_input()
                edit_elem.type_keys(str(value), with_spaces=True)

        if len(address_edits) >= 4:
            # [0]=Zip, [1]=Province, [2]=District, [3]=SubDistrict
            check_and_fill(address_edits[1], province, "จังหวัด")
            check_and_fill(address_edits[2], district, "เขต/อำเภอ")
            check_and_fill(address_edits[3], subdistrict, "แขวง/ตำบล")
        else:
            log("[!] หาช่องกรอกไม่ครบ 4 ช่อง -> ใช้การกด Tab")
            window.type_keys("{TAB}")
            window.type_keys(province, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(district, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(subdistrict, with_spaces=True)
            
    except Exception as e:
        log(f"[!] Error กรอกที่อยู่เอง: {e}")

def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    
    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        # 1. หาช่องค้นหาและกรอกคำค้น
        try:
            search_ready = False
            for _ in range(10):
                edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
                if edits:
                    search_ready = True
                    break
                time.sleep(0.5)
            
            if not search_ready: log("[WARN] หาช่องค้นหาไม่เจอ")
            
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    edit.click_input()
                    edit.type_keys(str(address_keyword), with_spaces=True)
                    filled = True
                    break
            if not filled and len(edits) > 1:
                edits[1].click_input()
                edits[1].type_keys(str(address_keyword), with_spaces=True)
        except: pass

        # กด Enter/ถัดไป เพื่อเริ่มค้นหา (เรียกหน้า List หรือ Popup)
        log("...กด Enter/ถัดไป เพื่อค้นหารายการ...")
        smart_next(window)
        time.sleep(1.0) 
        
        # 2. วนลูปรอผลลัพธ์ (Popup หรือ List)
        log("...กำลังตรวจสอบผลลัพธ์ (Popup/List)...")
        found_popup = False
        found_list = False
        
        for _ in range(40): # รอประมาณ 10 วินาที
            # เช็ค Popup
            if check_error_popup(window, delay=0.0):
                log("[WARN] ตรวจพบ Popup คำเตือน! -> ปิดแล้วเข้าสู่โหมดกรอกเอง")
                found_popup = True
                break
            
            # เช็ค List (ต้องอยู่ต่ำกว่า Header Y>200)
            list_items = [i for i in window.descendants(control_type="ListItem") 
                          if i.is_visible() and i.rectangle().top > 200]
            if list_items:
                found_list = True
                break
            
            time.sleep(0.25)

        # 3. ตัดสินใจทำงานต่อ
        if found_popup:
            # กรณีเจอ Popup -> ปิดแล้วกรอกที่อยู่เอง
            time.sleep(1.0)
            fill_manual_address(window, manual_data)
            # ไม่กด smart_next() เพราะต้องกรอกรายละเอียดต่อในหน้าเดียวกัน
            log("...กรอกที่อยู่แบบ Manual เสร็จสิ้น (ไปขั้นตอนตรวจสอบชื่อต่อ)...")
            
        elif found_list:
            # กรณีเจอ List -> เลือกอันแรก
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
                else:
                    log("[!] เจอ List แต่กรองความสูงไม่ผ่าน")
            except: pass
            
            # ไม่กด smart_next() ซ้ำ ตามคำขอ
            log("...เลือกรายการเสร็จสิ้น...")
            
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการ (Timeout) -> ลองกดถัดไปเผื่อระบบค้าง")
            smart_next(window)

def process_receiver_details_form(window, fname, lname, phone):
    log("--- หน้า: รายละเอียดผู้รับ (ตรวจสอบชื่อ/เบอร์) ---")
    log("...รอหน้าจอโหลด...")
    
    page_ready = False
    for i in range(15):
        if wait_for_text(window, ["ชื่อ", "นามสกุล", "คำนำหน้า"], timeout=1):
            page_ready = True
            break
        if i == 5: log("...ยังรอหน้าจออยู่ (5s)...")
        time.sleep(0.5)
    
    check_error_popup(window)
    time.sleep(1.0)

    try:
        log("...ตรวจสอบช่องกรอกชื่อ/นามสกุล...")
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        
        # กรองช่องที่อยู่ในโซนบน (150 < Y < 550) เพื่อหาแถวของชื่อ
        top_edits = [e for e in edits if 150 < e.rectangle().top < 550]
        # เรียงลำดับ Y (แถว) -> X (คอลัมน์)
        top_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
        
        name_edit = None
        surname_edit = None

        # Logic การหาช่องชื่อและนามสกุลที่แม่นยำขึ้น (ดูจากจำนวนช่องในแถวแรก)
        if len(top_edits) >= 2:
            first_y = top_edits[0].rectangle().top
            # หาเพื่อนร่วมแถว (ค่า Y ใกล้เคียงกัน +/- 10 pixel)
            first_row = [e for e in top_edits if abs(e.rectangle().top - first_y) < 15]
            
            if len(first_row) >= 3:
                # กรณี 3-4 ช่อง: [0]คำนำหน้า, [1]ชื่อ, [2]ชื่อกลาง(อาจไม่มี), [Last]นามสกุล
                # สมมติว่าเป็น [Title, Name, Middle, Surname] หรือ [Title, Name, Surname]
                name_edit = first_row[1] # ช่องที่ 2 คือชื่อ
                surname_edit = first_row[-1] # ช่องสุดท้ายคือนามสกุล
            elif len(first_row) == 2:
                # กรณี 2 ช่อง: [0]ชื่อ, [1]นามสกุล (อาจไม่มีคำนำหน้า)
                name_edit = first_row[0]
                surname_edit = first_row[1]
            else:
                # Fallback: ใช้ตามลำดับที่เจอ
                name_edit = top_edits[0]
                surname_edit = top_edits[1]

        # ฟังก์ชันกรอก (เช็คก่อน)
        def fill_if_empty(edit_ui, value, field_name):
            if edit_ui:
                val = edit_ui.get_value()
                if val and len(str(val).strip()) > 0:
                    log(f"...ช่อง '{field_name}' มีข้อมูลแล้ว ({val}) -> ข้าม")
                else:
                    log(f"...ช่อง '{field_name}' ว่าง -> กรอก: {value}")
                    edit_ui.click_input()
                    edit_ui.type_keys(value, with_spaces=True)

        if name_edit and surname_edit:
            fill_if_empty(name_edit, fname, "ชื่อ")
            fill_if_empty(surname_edit, lname, "นามสกุล")
        else:
            log("[WARN] ไม่สามารถระบุตำแหน่งช่องชื่อ/นามสกุลได้ชัดเจน -> ข้ามการกรอกชื่อ")

        # ตรวจสอบเบอร์โทร
        log("...เลื่อนลงเพื่อตรวจสอบเบอร์โทร...")
        force_scroll_down(window, -10)
        time.sleep(1)
        
        found_phone = False
        visible_edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        for edit in visible_edits:
            # หาจาก Automation ID หรือ Name
            if "โทร" in edit.element_info.name or "Phone" in edit.element_info.automation_id:
                fill_if_empty(edit, phone, "เบอร์โทร")
                found_phone = True
                break
        
        if not found_phone:
            log("[!] หาช่องเบอร์อัตโนมัติไม่เจอ -> ลองกด Tab")
            window.type_keys("{TAB}"*3)
            window.type_keys(phone, with_spaces=True)

    except Exception as e:
        log(f"[!] Error process_receiver_details: {e}")

    # [ACTION] กดถัดไป (Enter) 3 ครั้ง
    log("...จบขั้นตอนข้อมูลผู้รับ -> กด 'ถัดไป' 3 ครั้ง...")
    for i in range(3):
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window)
        time.sleep(1.5) # หน่วงเวลาให้หน้าจอโหลดทัน

def process_repeat_transaction(window, should_repeat):
    log("--- หน้า: ทำรายการซ้ำ ---")
    if wait_for_text(window, ["ทำรายการซ้ำ", "ซ้ำ"], timeout=8):
        target = "ใช่" if should_repeat.lower() in ['true', 'yes', 'on'] else "ไม่"
        log(f"...เลือก: {target}...")
        smart_click(window, target)
        if target == "ไม่": window.type_keys("{LEFT}{ENTER}")
        else: window.type_keys("{ENTER}")
    else:
        log("[WARN] ไม่พบหน้าทำรายการซ้ำ")

# ================= 4. Run Function (Partial) =================
def run_partial_test(main_window, config):
    # Load vars from Config
    special_services = config['SPECIAL_SERVICES'].get('Services', '')
    addr_keyword = config['RECEIVER'].get('AddressKeyword', '')
    rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', '')
    rcv_lname = config['RECEIVER_DETAILS'].get('LastName', '')
    rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '')
    repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
    step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))

    # Load Manual Address Data
    if 'MANUAL_ADDRESS_FALLBACK' in config:
        manual_data = {
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', ''),
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', ''),
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '')
        }
    else:
        manual_data = {'Province': '', 'District': '', 'SubDistrict': ''}

    log("!!! เริ่มการทดสอบแบบย่อ (เริ่มที่หน้าบริการพิเศษ) !!!")
    time.sleep(2)

    # 11. หน้าบริการพิเศษ
    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    # 12. หน้าข้อมูลผู้ส่ง (ข้าม)
    process_sender_info_page(main_window)
    time.sleep(step_delay)

    # 13. หน้าข้อมูลผู้รับ (เลือกที่อยู่ / Manual)
    process_receiver_address_selection(main_window, addr_keyword, manual_data)
    time.sleep(step_delay)
    
    # 14. หน้ารายละเอียดผู้รับ (ตรวจสอบชื่อ/เบอร์ -> กด Next 3 ครั้ง)
    process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone)
    time.sleep(step_delay)

    # 15. หน้าคำแนะนำใบเสร็จ (ถูกข้ามไปแล้ว)
    
    # 16. หน้าทำรายการซ้ำ
    process_repeat_transaction(main_window, repeat_flag)

    log("[SUCCESS] จบการทดสอบแบบย่อ")

# ================= 5. Main =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting to App...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            
            run_partial_test(main_window, conf)
            
        except Exception as e:
            log(f"Error: {e}")
    input("\n>>> กด Enter เพื่อปิด... <<<")