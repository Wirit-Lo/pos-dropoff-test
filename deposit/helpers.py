# ไฟล์: helpers.py
import time
import sys
import functools
import datetime
from pywinauto import mouse

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def stop_script_immediately(reason):
    """
    ฟังก์ชันสั่งตาย: หยุดโปรแกรมทันทีเมื่อถูกเรียก
    """
    log(f"\n{'='*40}")
    log(f"[!!! CRITICAL ERROR - หยุดฉุกเฉิน !!!]")
    log(f"สาเหตุ: {reason}")
    log(f"{'='*40}\n")
    
    print("\a") # ส่งเสียงเตือน
    input(">>> กด Enter เพื่อปิดโปรแกรม... <<<")
    sys.exit(1)

def strict_check(func):
    """
    🛡️ Decorator: ตัวคุมกัน Error อัตโนมัติ
    วิธีใช้: แปะ @strict_check ไว้บนหัวฟังก์ชันที่ต้องการ
    ผลลัพธ์: ถ้าฟังก์ชันนั้น return False ระบบจะสั่งหยุดทันที
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 1. เรียกใช้ฟังก์ชันจริง
        result = func(*args, **kwargs)
        
        # 2. ตรวจสอบผลลัพธ์
        if result is False:
            # ดึงชื่อฟังก์ชันและข้อมูลมาโชว์ตอน Error
            func_name = func.__name__
            # พยายามดึงชื่อ Target (Argument ตัวที่ 2) มาโชว์เพื่อให้รู้ว่า error ที่ปุ่มไหน
            target_info = f" (Target: {args[1]})" if len(args) > 1 else ""
            
            # เรียกสั่งตายทันที!
            stop_script_immediately(f"ฟังก์ชัน '{func_name}' ทำงานไม่สำเร็จ{target_info}")
            
        return result
    return wrapper

# --- ส่วน Wait & Check ---
@strict_check
def wait_for_text(window, text_list, timeout=60):
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

@strict_check
def wait_until_id_appears(window, exact_id, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(1)
    return False

# --- ส่วน Click & Fill ---
@strict_check
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

@strict_check
def click_element_by_id(window, exact_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if found:
                found[0].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except: pass
        time.sleep(0.5)
    return False

@strict_check
def find_and_fill_smart(window, target_name, target_id_keyword, value, timeout=15):
    if not value or str(value).strip() == "": return False
    log(f"...รอช่อง '{target_name}' (Max {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            target_elem = None
            for child in window.descendants():
                if not child.is_visible(): continue
                aid, name = child.element_info.automation_id, child.element_info.name
                if target_name and name and target_name in name: target_elem = child; break
                if target_id_keyword and aid and target_id_keyword in aid: target_elem = child; break
            
            if target_elem:
                try: 
                    edits = target_elem.descendants(control_type="Edit")
                    if edits: target_elem = edits[0]
                except: pass
                target_elem.set_focus(); target_elem.click_input(); time.sleep(0.5)
                target_elem.type_keys(str(value), with_spaces=True)
                log(f"   [/] กรอก '{target_name}' เรียบร้อย")
                return True
        except: pass
        time.sleep(0.5)
    log(f"[WARN] หาช่อง '{target_name}' ไม่เจอ")
    return False

@strict_check  
def smart_next(window):
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป'")
        return True # <--- ต้องเพิ่มบรรทัดนี้
    else:
        window.type_keys("{ENTER}")
        log("   [/] กด Enter (แทนปุ่มถัดไป)") # เพิ่ม log เพื่อความชัดเจน
        return True # <--- ต้องเพิ่มบรรทัดนี้

# --- ฟังก์ชันเฉพาะทาง ---
@strict_check
def click_toggle_inside_parent(window, parent_id):
    parents = [c for c in window.descendants() if c.element_info.automation_id == parent_id]
    if parents:
        thumbs = [c for c in parents[0].descendants() if c.element_info.automation_id == "SwitchThumb"]
        if thumbs: thumbs[0].click_input(); return True
    return False

@strict_check
def click_scroll_arrow_smart(window, direction='right', repeat=5):
    """ใช้ช่วยเลื่อนหน้าจอในฟังก์ชัน Rotate Logic"""
    try:
        target_group = [c for c in window.descendants() if c.element_info.automation_id == "ShippingServiceList"]
        if target_group: target_group[0].set_focus()
        else: window.set_focus()
        
        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        window.type_keys(key_code * repeat, pause=0.2, set_foreground=False)
        return True
    except: return False

@strict_check
def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    """(สำคัญ) ใช้หาปุ่มบริการ 'ธนาณัติธรรมดา' ที่อาจหลบอยู่"""
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False
        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            if rect.right < safe_limit:
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else: should_scroll = True
        else: should_scroll = True
        
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5): window.type_keys("{RIGHT}")
            time.sleep(1.0)
    log(f"[X] หาปุ่มไม่เจอ: {target_id}")
    return False

@strict_check
def select_item_from_dropdown_list(window, combo_id, target_text):
    """
    ฟังก์ชันเลือก Dropdown (ฉบับใช้ F4 ล้วน): ตัดการคลิกเมาส์ออก เพื่อแก้ปัญหา Focus
    """
    log(f"...กำลังจัดการ Dropdown ID: '{combo_id}' เลือก: '{target_text}'...")

    # 1. หาตัวแม่หรือตัวลูกเหมือนเดิม
    parent_id = f"{combo_id}_UserControlBase"
    target_element = None
    
    parents = [c for c in window.descendants() if c.element_info.automation_id == parent_id and c.is_visible()]
    if parents:
        log(f"   [Debug] เจอ Parent ID: '{parent_id}' -> จะใช้ตัวนี้ในการกด")
        target_element = parents[0]
    else:
        candidates = [c for c in window.descendants() if c.element_info.automation_id == combo_id and c.is_visible()]
        if candidates:
            log(f"   [Debug] เจอ ID ตรงตัว: '{combo_id}' -> จะใช้ตัวนี้ในการกด")
            target_element = candidates[0]

    # 2. ปฏิบัติการเปิดกล่อง (แก้ใหม่: ใช้ F4 อย่างเดียว)
    if target_element:
        # แค่ Set Focus ก็พอ ไม่ต้อง click_input() ที่ทำให้เกิด Error
        target_element.set_focus()
        
        # ส่งปุ่ม F4 เพื่อกางรายการทันที
        log("   [/] สั่งกด F4 เพื่อกางรายการ (ข้ามการคลิกเมาส์)...")
        target_element.type_keys("{F4}")
        time.sleep(1.5) 
    else:
        log(f"[WARN] หา Dropdown ไม่เจอทั้งตัวแม่และตัวลูก")
        return False

    # 3. วนลูปหา 'ListItem' (ส่วนนี้เหมือนเดิม)
    for i in range(15): 
        try:
            found_item = None
            for child in window.descendants():
                if child.is_visible() and target_text in child.window_text():
                    found_item = child
                    break
            
            if found_item:
                log(f"   [/] เจอรายการ '{target_text}' -> คลิกเลือก")
                found_item.set_focus()
                found_item.click_input()
                return True
            else:
                window.type_keys("{PGDN}") 
                time.sleep(0.8)
        except Exception as e:
            log(f"[!] Error ขณะเลื่อนหา: {e}")
            break
            
    log(f"[X] หาไม่เจอ หรือ เลื่อนจนสุดแล้ว")
    return False

@strict_check
def select_first_list_item_in_group(window, group_id, timeout=5):
    """
    รอให้ Group (เช่น 'SpecificPostOffice') ปรากฏ
    แล้วคลิก ListItem ตัวแรกสุดที่อยู่ข้างใน
    """
    log(f"...กำลังรอเลือกรายการแรกในกลุ่ม ID: '{group_id}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            # 1. หาตัวแม่ (Group)
            groups = [c for c in window.descendants() if c.element_info.automation_id == group_id and c.is_visible()]
            
            if groups:
                parent_group = groups[0]
                # 2. หาตัวลูก (ListItem) ทั้งหมดในกลุ่มนี้
                items = [c for c in parent_group.descendants() if c.element_info.control_type == 'ListItem']
                
                if items:
                    target_item = items[0] # เลือกตัวแรกเสมอ [0]
                    item_name = target_item.window_text()
                    
                    # คลิกเลย
                    target_item.set_focus()
                    target_item.click_input()
                    log(f"   [/] เลือกรายการแรกสำเร็จ: '{item_name}'")
                    return True
        except Exception as e:
            # กัน error กรณี ui เปลี่ยนกะทันหัน
            pass
        
        time.sleep(0.5)
        
    log(f"[WARN] ไม่พบรายการให้เลือกในกลุ่ม '{group_id}' (หรืออาจเลือกไปแล้ว)")
    return False

@strict_check
def robust_fill_and_verify(window, target_id, value, timeout=15):
    """
    ฟังก์ชันกรอกแบบ 'กัดไม่ปล่อย' (100% Guarantee)
    1. วนหาช่อง
    2. สั่งพิมพ์
    3. เช็คค่าในช่องว่าตรงกับที่พิมพ์ไหม ถ้าไม่ตรง -> พิมพ์ใหม่
    """
    log(f"...กำลังกรอก '{value}' ลงใน ID '{target_id}' (โหมดตรวจสอบ)...")
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            # 1. หา Element
            elems = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
            if not elems:
                time.sleep(0.5) # ยังไม่เจอ ให้รอ
                continue
            
            target = elems[0]
            
            # กรณีเจอ Edit Control ซ้อนข้างใน
            if target.element_info.control_type != 'Edit':
                edits = target.descendants(control_type="Edit")
                if edits: target = edits[0]

            # 2. เช็คค่าปัจจุบันก่อน (ถ้ามีอยู่แล้วและถูกแล้ว ก็จบเลย ไม่ต้องพิมพ์ซ้ำ)
            current_val = target.window_text().strip()
            if str(value) in current_val:
                log(f"   [/] ข้อมูล '{value}' มีอยู่แล้วถูกต้อง")
                return True

            # 3. ถ้ายังไม่ถูก ให้ Focus และพิมพ์
            target.set_focus()
            target.click_input()
            target.type_keys("^a{DELETE}", pause=0.1) # ลบของเก่า (Ctrl+A -> Del)
            target.type_keys(str(value), with_spaces=True, pause=0.1) # พิมพ์ช้าๆ
            
            # 4. (สำคัญ) รอเช็คผลลัพธ์ทันที
            time.sleep(0.5) 
            if str(value) in target.window_text():
                log(f"   [/] กรอกและตรวจสอบแล้ว: '{value}'")
                return True
            else:
                log(f"   [Retry] พิมพ์ไปแล้วแต่ค่าไม่เข้า... ลองใหม่")
        
        except Exception as e:
            log(f"   [Retry] เกิด Error ระหว่างกรอก: {e}")
            pass
            
        time.sleep(1.0) # รอ 1 วิ ก่อนวนลูปใหม่

    log(f"[X] หมดเวลา! ไม่สามารถกรอก '{value}' ได้")
    return False

@strict_check
def wait_and_select_first_item_strict(window, group_id, timeout=10):
    """
    รอจนกว่า 'รายการ' จะโผล่มาจริงๆ (ไม่ใช่แค่กรอบ Group)
    แล้วกดเลือกตัวแรก
    """
    log(f"...รอรายการตัวเลือกใน '{group_id}'...")
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            # 1. หา Group แม่
            groups = [c for c in window.descendants() if c.element_info.automation_id == group_id and c.is_visible()]
            
            if groups:
                parent = groups[0]
                # 2. นับจำนวนลูก (ListItem)
                items = [c for c in parent.descendants() if c.element_info.control_type == 'ListItem']
                
                # ถ้าเจอรายการ (มากกว่า 0) แปลว่าโหลดเสร็จแล้ว
                if len(items) > 0:
                    target_item = items[0]
                    target_text = target_item.window_text()
                    
                    # 3. กดเลือก
                    target_item.set_focus()
                    target_item.click_input()
                    log(f"   [/] รายการโหลดเสร็จ -> เลือก: '{target_text}'")
                    return True
                else:
                    # เจอ Group แต่ข้างในยังว่างเปล่า (กำลังหมุนติ้วๆ)
                    # log("   ...รายการยังไม่มา (Loading)...")
                    pass
        except:
            pass
            
        time.sleep(0.5) # รอแป๊บนึงแล้วเช็คใหม่
        
    log("[X] รอนานเกินไป รายการไม่ขึ้น")
    return False

@strict_check
def process_excess_cash_flow(window):
    """
    จัดการ Flow เงินเกินลิ้นชัก:
    1. Popup แจ้งเตือน (กด AcceptButton)
    2. หน้าโอนเงินสด (กด Next)
    3. Popup ยืนยัน (กด Yes)
    4. หน้าพิมพ์ (กด PrintYes)
    """
    log("--- เริ่มกระบวนการจัดการเงินเกินลิ้นชัก (Excess Cash Flow) ---")

    # 1. รอและกดปุ่ม 'ตกลง' (AcceptButton) ที่ Popup แจ้งเตือน
    # ใช้ wait_until_id_appears เพื่อรอให้ Popup เด้งขึ้นมาแน่นอน
    wait_until_id_appears(window, "AcceptButton")
    click_element_by_id(window, "AcceptButton")
    
    # 2. รอเข้าหน้า 'การโอนเงินสด/เช็ค' และกด 'ถัดไป' (LocalCommand_Submit)
    # รอข้อความหัวข้อเพื่อให้แน่ใจว่าหน้าโหลดเสร็จ
    wait_for_text(window, "การโอนเงินสด")
    smart_next(window) # ฟังก์ชันนี้กด LocalCommand_Submit ให้เอง

    # 3. รอและกดปุ่ม 'ใช่' (Yes) ที่ Popup ยืนยันการโอน
    wait_until_id_appears(window, "Yes")
    click_element_by_id(window, "Yes")

    # 4. รอและกดปุ่ม 'พิมพ์' (PrintYes) ที่หน้าสุดท้าย
    wait_until_id_appears(window, "PrintYes")
    click_element_by_id(window, "PrintYes")

    log("   [/] จบขั้นตอนการโอนเงินเกินและสั่งพิมพ์")
    return True

# --- แก้ไขในไฟล์ helpers.py ---

@strict_check
def select_dropdown_using_pagedown(window, box_id, target_text, max_pages=20):
    """
    ฟังก์ชันเลือก Dropdown (ฉบับกด PageDown + ค้นหาด้วย ID):
    1. กด F4 เปิดกล่อง
    2. วนหา ListItem ที่มี AutomationId ตรงกับ target_text
    3. ถ้าไม่เจอ -> กด PageDown
    """
    log(f"...กำลังค้นหา ID '{target_text}' ในช่อง '{box_id}' (โหมด PageDown)...")
    
    # 1. หาและ Focus ที่กล่อง
    try:
        # หาตัวกล่อง Dropdown ก่อน
        found_box = [c for c in window.descendants() if c.element_info.automation_id == box_id and c.is_visible()]
        if not found_box:
            log(f"[Error] หาช่อง Dropdown ID: {box_id} ไม่เจอ")
            return False
        
        target_box = found_box[0]
        target_box.set_focus()
    except: return False

    # 2. กด F4 เพื่อกางรายการ
    log("   [/] กด F4 เพื่อกางรายการ")
    target_box.type_keys("{F4}")
    time.sleep(2.0) # รอให้รายการเด้งออกมา

    # 3. วนลูปค้นหา
    for i in range(max_pages):
        try:
            # --- [จุดที่แก้ไข] ---
            # 1. ใช้ window.descendants() แทน top_window() เพื่อแก้ Error
            # 2. เช็คที่ automation_id โดยตรง (ตามคำแนะนำ)
            # 3. หาเฉพาะ ListItem ที่ Visible (มองเห็น)
            found_items = [c for c in window.descendants(control_type="ListItem") 
                           if c.element_info.automation_id == target_text 
                           and c.is_visible()]
            
            if found_items:
                target_item = found_items[0]
                log(f"   [/] เจอ ID '{target_text}' แล้ว (รอบที่ {i})")
                
                # คลิกเลือกทันที
                target_item.set_focus()
                target_item.click_input()
                return True
            
            # ถ้ายังไม่เจอ -> กด PageDown ที่กล่องหลัก
            log(f"   ...ยังไม่เจอ ID '{target_text}' -> กด PageDown (รอบที่ {i+1})")
            target_box.type_keys("{PGDN}") 
            time.sleep(1.0) # รอให้รายการเลื่อน

        except Exception as e:
            log(f"[!] Error ขณะค้นหา: {e}")
            pass
            
    log(f"[X] กด PageDown ไป {max_pages} รอบแล้วยังไม่เจอ ID '{target_text}'")
    return False

@strict_check
def fill_receiver_details_with_sms(window, fname, lname, send_sms=False, phone=""):
    """
    กรอกข้อมูลผู้รับ + จัดการเรื่อง SMS (ถ้าเปิด)
    """
    log(f"--- กรอกข้อมูลผู้รับ: {fname} {lname} (SMS: {send_sms}) ---")
    
    # 1. รอหน้าจอ
    wait_for_text(window, ["ผู้รับ", "ชื่อ", "นามสกุล"])

    # 2. กรอกชื่อและนามสกุล
    find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)
    find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

    # 3. จัดการ SMS (ถ้าเปิด)
    if send_sms:
        log("   [SMS Mode] กำลังกรอกเบอร์โทรศัพท์...")
        if phone:
            # พยายามหาช่องเบอร์โทร (ใช้ ID: PhoneNumber หรือ Text: เบอร์โทร)
            if not find_and_fill_smart(window, "เบอร์โทร", "PhoneNumber", phone):
                 # Fallback: ลองหาคำว่า "โทรศัพท์"
                 find_and_fill_smart(window, "โทรศัพท์", "Phone", phone)
        else:
            log("   [Warn] เปิดโหมด SMS แต่ไม่มีเบอร์โทรระบุมา")

    # 4. กดถัดไป
    smart_next(window)
    time.sleep(1.0) # รอหน้าเปลี่ยน
    return True

# --- เพิ่มใน helpers.py ---

@strict_check
def handle_sms_step(window, send_sms=False):
    """
    Step 6: จัดการหน้ายอดเงิน และกดปิด SMS (เพราะค่าเดิมเป็น 'ใช่')
    """
    log("--- Step 6: ตรวจสอบยอดเงิน & SMS ---")
    
    # 1. รอหน้าจอ "ยอดเงินที่ส่ง"
    wait_for_text(window, ["ยอดเงินที่ส่ง"])

    # รอให้ปุ่ม SwitchThumb โผล่มา (สำคัญ: ต้องรอก่อนตัดสินใจกด)
    wait_until_id_appears(window, "SwitchThumb", timeout=5)

    # 2. Logic เปิด/ปิด SMS
    # กรณี: ค่าเริ่มต้นของระบบคือ "เปิด (ใช่)" อยู่แล้ว
    
    if not send_sms:
        # ถ้า Config = No (ไม่ส่ง) -> ต้องกด Switch 1 ที เพื่อ "ปิด"
        log("   [Config] ไม่ต้องการส่ง SMS (แต่ค่าเดิมเป็น 'ใช่') -> กำลังกดปิด Switch...")
        
        if click_element_by_id(window, "SwitchThumb"):
            log("   [/] กดปิด SMS เรียบร้อย (เปลี่ยนเป็น 'ไม่')")
        else:
            log("   [Warn] หาปุ่ม SwitchThumb ไม่เจอ (อาจจะปิดไม่ได้)")
            
    else:
        # ถ้า Config = Yes (ส่ง) -> ไม่ต้องทำอะไร (เพราะค่าเดิมเป็น 'ใช่' อยู่แล้ว)
        log("   [Config] ต้องการส่ง SMS (ตรงกับค่าเดิม) -> ไม่ต้องกดอะไร")

    # 3. กดถัดไป
    smart_next(window)
    time.sleep(1.0) # รอหน้าเปลี่ยน
    return True

# --- เพิ่มใน helpers.py ---

@strict_check
def fill_amount_and_destination(window, amount, postal_code):
    """
    Step 5: กรอกจำนวนเงิน และ เลือกปลายทาง (รหัสไปรษณีย์)
    """
    log(f"--- Step 5: กรอกยอดเงิน ({amount}) & ปลายทาง ({postal_code}) ---")
    
    # 1. รอหน้าจอ
    wait_for_text(window, ["ปลายทาง", "จำนวนเงิน"])
    
    # 2. กรอกจำนวนเงิน (ใช้ find_and_fill_smart ตามเดิม)
    find_and_fill_smart(window, "จำนวนเงิน", "CurrencyAmount", amount)
    
    # 3. กรอกรหัสไปรษณีย์ (ใช้ตัวตรวจสอบผลลัพธ์: robust_fill_and_verify)
    # มันจะวนรอบจนกว่าเลขจะเข้าไปอยู่ในช่องจริงๆ
    if robust_fill_and_verify(window, "SpecificPostOfficeFilter", postal_code, timeout=15):
        
        # 4. รอและเลือกรายการ (รอจนกว่าลูกจะเกิดแล้วค่อยกด)
        # ระบบจะรอจนกว่ารายการแรก (เช่น พระโขนง) จะโผล่มาให้กด
        wait_and_select_first_item_strict(window, "SpecificPostOffice")
        
    else:
        log(f"[Error] กรอกรหัสไปรษณีย์ '{postal_code}' ไม่สำเร็จ (Timeout)")
        return False # ส่งค่ากลับว่าล้มเหลว

    # 5. กดถัดไป (จบ Step นี้)
    smart_next(window)
    time.sleep(1.0) # รอหน้าเปลี่ยน
    return True

################################# ธนาณัติ #################################

@strict_check
def handle_car_tax_step(window, config_tax):
    """
    Step 5: จัดการหน้าภาษีรถยนต์ (Smart Check: มีช่องไหน กรอกช่องนั้น)
    """
    log("--- Step 5: คำนวณค่าภาษีรถยนต์ ---")
    
    wait_for_text(window, ["ประเภทรถ", "วันครบกำหนด"])

    # =======================================================
    # 1. เลือกประเภทรถหลัก (Main Type) - จุดเริ่มต้นของทุกคัน
    # =======================================================
    main_type_name = config_tax.get('VehicleType', '')
    
    if main_type_name:
        log(f"   [Main] กำลังเลือกประเภทรถ: {main_type_name}")

        # Map ชื่อไทย -> ID (ครบ 8 ประเภทตามที่คุณแจ้ง)
        VEHICLE_ID_MAP = {
            "(รย.๑๔) รถบดถนน": "THP_SendMoney_CarType_ConstructionTruck_DisplayName",
            "(รย.๒) รถยนต์นั่งส่วนบุคคลเกิน 7 คน": "THP_SendMoney_CarType_Greaterthan7_DisplayName",
            "(รย.๑) รถยนต์นั่งส่วนบุคคลไม่เกิน 7 คน": "THP_SendMoney_CarType_Lessthan7_DisplayName",
            "(รย.๑๒) รถจักรยานยนต์ส่วนบุคคล": "THP_SendMoney_CarType_Motorcycle_DisplayName",
            "รถพ่วงข้างของรถจักรยานยนต์ส่วนบุคคล": "THP_SendMoney_CarType_MotorCycleWithTrailer_DisplayName",
            "รถพ่วงอื่นนอกจากรถพ่วงข้างของรถจักรยานยนต์ส่วนบุคคล": "THP_SendMoney_CarType_OtherTrailer_DisplayName",
            "รถใช้งานเกษตรกรรม": "THP_SendMoney_CarType_Tractor_DisplayName",
            "(รย.๓) รถบรรทุกส่วนบุคคล": "THP_SendMoney_CarType_Truck_DisplayName"
        }

        target_key = VEHICLE_ID_MAP.get(main_type_name, main_type_name)
        select_dropdown_using_pagedown(window, "Element", target_key)
        
        # รอให้ฟอร์มเปลี่ยนรูป (สำคัญ)
        time.sleep(3.0) 
    else:
        log("[Error] ไม่ได้ระบุ VehicleType ใน Config")
        return False

    # =======================================================
    # 2. กรอกข้อมูล Dynamic (ใช้ Smart Check เช็คก่อนทำ)
    # =======================================================
    
    # --- [Element 1] ขนาดซีซี (สำหรับ รย.1) ---
    cc_val = config_tax.get('EngineCC', '')
    if cc_val:
        # เช็คว่ามีช่อง Element1 ไหม? (timeout สั้นๆ พอ ไม่ต้องรอนาน)
        if window.child_window(auto_id="Element1").exists(timeout=1):
            find_and_fill_smart(window, "ซีซี", "Element1", cc_val)
        # ถ้าไม่มี (เช่น รย.14) -> โค้ดจะผ่านไปเฉยๆ ไม่ Error

    # --- [Element 2] ปีที่จดทะเบียน (สำหรับ รย.1) ---
    year_val = config_tax.get('RegYear', '')
    if year_val:
        if window.child_window(auto_id="Element2").exists(timeout=1):
            find_and_fill_smart(window, "ปีที่จด", "Element2", year_val)

    # --- [Element 3] น้ำหนัก (สำหรับ รย.2, รย.3) ---
    weight_val = config_tax.get('VehicleWeight', '')
    if weight_val:
        if window.child_window(auto_id="Element3").exists(timeout=1):
            find_and_fill_smart(window, "น้ำหนัก", "Element3", weight_val)

    # --- [Element 4] ประเภทเจ้าของ (สำหรับ รย.1) ---
    owner_type = config_tax.get('OwnerType', '')
    if owner_type:
        # เช็คก่อนว่ามี Dropdown Element4 ไหม
        if window.child_window(auto_id="Element4").exists(timeout=1):
            log(f"   [Select] เลือกเจ้าของ (Element4): {owner_type}")
            OWNER_ID_MAP = {
                "นิติบุคคล": "THP_SendMoney_OwnerType_Juristic_DisplayName",
                "ส่วนตัว": "THP_SendMoney_OwnerType_Private_DisplayName",
                "ส่วนบุคคล": "THP_SendMoney_OwnerType_Private_DisplayName" 
            }
            target_owner_id = OWNER_ID_MAP.get(owner_type, owner_type)
            select_dropdown_using_pagedown(window, "Element4", target_owner_id)
        else:
             # กรณีรถบางรุ่นไม่มีช่องนี้ ระบบจะแค่แจ้ง Log แล้วไปต่อ
             pass

    # --- [Element 5] ประเภทจักรยานยนต์ (สำหรับ รย.12) ---
    moto_type = config_tax.get('MotorcycleType', '')
    if moto_type:
        if window.child_window(auto_id="Element5").exists(timeout=1):
            log(f"   [Select] เลือก จยย. (Element5): {moto_type}")
            MOTO_ID_MAP = {
                "ไฟฟ้า": "THP_SendMoney_MotorcycleType_Electric_DisplayName",
                "น้ำมัน": "THP_SendMoney_MotorcycleType_Petrol_DisplayName"
            }
            target_moto_id = MOTO_ID_MAP.get(moto_type, moto_type)
            select_dropdown_using_pagedown(window, "Element5", target_moto_id)

    # =======================================================
    # 3. ข้อมูลพื้นฐาน (มีทุกคัน 1-8)
    # =======================================================

    # --- [SwitchThumb] ค่าธรรมเนียมเปลี่ยนเล่ม ---
    fee_config = config_tax.get('ChangeBookFee', 'No').lower()
    if fee_config in ['yes', 'true', 'on']:
        # เช็ค Switch เผื่อบางหน้าไม่มี
        if window.child_window(auto_id="SwitchThumb").exists(timeout=2):
            log("   [Switch] กดเปิดเปลี่ยนเล่ม")
            click_element_by_id(window, "SwitchThumb")

    # --- [Element 7] วันครบกำหนดภาษี (พระเอกของเรา มีทุกคัน) ---
    due_date = config_tax.get('TaxDueDate', '')
    if due_date:
        # ค้นหา Element7 ทั้งหมดที่มีในระบบ
        candidates = [c for c in window.descendants() 
                      if c.element_info.automation_id == "Element7" 
                      and c.is_visible()] # 🔥 กรองเฉพาะตัวที่มองเห็น
        
        if candidates:
            log(f"   [Fill] กรอกวันครบกำหนด: {due_date}")
            # เลือกตัวแรกที่มองเห็น (Safe ที่สุด)
            target_box = candidates[0]
            target_box.click_input() # คลิกก่อนพิมพ์เพื่อความชัวร์
            target_box.type_keys(due_date, with_spaces=True)
        else:
            log("[Warn] หาช่องวันครบกำหนด (Element7) ไม่เจอ (หรือถูกซ่อนอยู่)")

    # =======================================================
    # 4. จบการทำงาน
    # =======================================================
    smart_next(window)
    time.sleep(1.0)
    return True

################################# จบธนาณัติ #################################
