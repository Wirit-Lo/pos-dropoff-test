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