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


def click_scroll_arrow_smart(window, direction='right', repeat=5):
    """
    ฟังก์ชันเลื่อนหน้าจอโดยใช้ "แป้นพิมพ์" (Keyboard Arrow Keys) ล้วน 100%
    """
    try:
        # 1. พยายามโฟกัสไปที่กล่องรายการสินค้าก่อน
        target_group = [c for c in window.descendants(
        ) if c.element_info.automation_id == "ShippingServiceList"]

        if target_group:
            target_group[0].set_focus()
        else:
            window.set_focus()

        # 2. กำหนดปุ่มที่จะกด
        if direction == 'right':
            key_code = '{RIGHT}'
        else:
            key_code = '{LEFT}'

        # 3. สร้างคำสั่งกดปุ่มรัวๆ
        keys_string = key_code * repeat

        # 4. ส่งคำสั่งคีย์บอร์ด (ปรับความเร็วตรง pause=0.2 เพื่อให้ไม่หลุด)
        window.type_keys(keys_string, pause=0.2, set_foreground=False)

        return True

    except Exception as e:
        print(f"Keyboard Scroll Error: {e}")
        try:
            key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
            window.type_keys(key_code * repeat, pause=0.05)
            return True
        except:
            return False


def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    """
    [Turbo] ค้นหาปุ่มบริการแบบวนลูป (เร่งความเร็วการเลื่อน + ลด Delay)
    """
    log(f"...ค้นหาปุ่ม ID: '{target_id}' (Fast Scroll Mode)...")

    # พยายามโฟกัสหน้าจอหลักก่อนเริ่ม
    try:
        window.set_focus()
    except:
        pass

    for i in range(1, max_rotations + 1):
        # 1. สแกนหาปุ่มเป้าหมาย
        found_elements = [c for c in window.descendants() if str(
            c.element_info.automation_id) == target_id and c.is_visible()]

        should_scroll = False

        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()

            # เช็คว่าปุ่มโผล่มาในจอหรือยัง (Safe Zone = เกือบเต็มจอ)
            is_visible_on_screen = rect.left < win_rect.right - 5

            if is_visible_on_screen:
                log(f"   [{i}] ✅ เจอปุ่ม '{target_id}' -> CLICK!")
                try:
                    target.set_focus()
                    target.click_input()
                except:
                    window.type_keys("{ENTER}")
                return True
            else:
                # เจอปุ่มแต่อยู่ขวาสุดๆ -> เลื่อนนิดหน่อยพอ (3 ครั้ง)
                log(f"   [{i}] เจอปุ่ม (ตกขอบ) -> เลื่อนขวานิดหน่อย")
                window.type_keys("{RIGHT}" * 3, pause=0.05)
                time.sleep(0.2)
                continue  # วนลูปเช็คใหม่ทันที
        else:
            should_scroll = True

        # 2. สั่งเลื่อนหน้าจอ (ถ้ายังไม่เจอ)
        if should_scroll:
            # ใช้การส่งปุ่มแบบรวดเร็ว (pause=0.05) และเลื่อนทีละ 7 ช่อง
            # หมายเหตุ: ไม่เรียก click_scroll_arrow_smart เพราะตัวนั้นหน่วงเวลาเยอะ
            log(f"   [{i}] ไม่เจอ -> เลื่อนขวาเร็ว (7x)")
            window.type_keys("{RIGHT}" * 7, pause=0.05)

            # รอหน้าจอขยับแค่ 0.3 วิ (จากเดิม 1.0 วิ)
            time.sleep(0.3)

    log(f"[X] หาไม่เจอหลังเลื่อน {max_rotations} รอบ")
    return False


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
    except:
        pass


def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str):
        criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text().strip():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except:
                pass
        time.sleep(0.3)
    return False


def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    log(f"...ค้นหา '{criteria}' (Scroll)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found = child
                    break
        except:
            pass
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
            except:
                pass
        if i < max_scrolls:
            force_scroll_down(window, scroll_dist)
    return False


def click_element_by_id(window, exact_id, timeout=5, index=0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants(
            ) if c.element_info.automation_id == exact_id and c.is_visible()]
            if len(found) > index:
                found[index].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except:
            pass
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
        except:
            pass
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
        except:
            pass
        time.sleep(1)
    return False


def wait_for_text(window, text_list, timeout=5):
    if isinstance(text_list, str):
        text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible():
                        return True
        except:
            pass
        time.sleep(0.5)
    return False


def smart_next(window):
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    submits = [c for c in window.descendants(
    ) if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")


def check_error_popup(window, delay=0.5):
    """เช็ค Popup และกดปิด"""
    if delay > 0:
        time.sleep(delay)
    try:
        # 1. เช็คหน้าต่าง Popup
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
    except:
        pass
    return False

# ================= 3. Business Logic Functions =================


def process_sender_info_popup(window, phone, sender_postal):
    """
    Popup ข้อมูลผู้ส่ง: ใช้เบอร์ผู้ส่ง และ รหัสไปรษณีย์ต้นทาง (Sender Postal)
    """
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3):
        time.sleep(1.5)
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        log(f"...กรอก ปณ. ต้นทาง: {sender_postal}")
                        edit.click_input()
                        edit.type_keys(str(sender_postal), with_spaces=True)
                    break
        except:
            pass

        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input()
                        edit.type_keys(str(phone), with_spaces=True)
                        found_phone = True
                        break
            except:
                pass
            if found_phone:
                break
            force_scroll_down(window, -5)
        smart_next(window)


def handle_prohibited_items(window):
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}")
                    return
        except:
            pass
        time.sleep(0.5)


def smart_input_weight(window, value):
    try:
        edits = [e for e in window.descendants(
            control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except:
        pass
    window.type_keys(str(value), with_spaces=True)
    return True


def process_special_services(window, services_str):
    log("--- หน้า: บริการพิเศษ ---")
    if wait_for_text(window, "บริการพิเศษ", timeout=5):
        if services_str.strip():
            for s in services_str.split(','):
                if s:
                    smart_click(window, s.strip())
    smart_next(window)


def process_sender_info_page(window):
    log("--- หน้า: ข้อมูลผู้ส่ง (ข้าม) ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    smart_next(window)

# ฟังก์ชันใหม่: ค้นหา Element แบบ Smart (Text หรือ ID)


def find_and_fill_smart(window, target_name, target_id_keyword, value):
    try:
        # [แก้ไข] ถ้าค่าว่าง ให้ข้ามเลย ไม่ต้องหาและไม่ต้องคลิก (เพื่อความเร็ว)
        if not value or str(value).strip() == "":
            return False

        target_elem = None
        # วนลูปหาแค่รอบเดียวเพื่อประสิทธิภาพ
        for child in window.descendants():
            # ข้าม Element ที่มองไม่เห็น
            if not child.is_visible():
                continue

            # ดึงค่า ID และ Name
            aid = child.element_info.automation_id
            name = child.element_info.name

            # 1. เช็คจากชื่อ (Name) - แม่นยำสุดสำหรับภาษาไทย
            if target_name and name and target_name in name:
                target_elem = child
                break

            # 2. เช็คจาก ID (Automation ID) - ถ้าชื่อไม่เจอ
            if target_id_keyword and aid and target_id_keyword in aid:
                target_elem = child
                break

        if target_elem:
            # ถ้าเจอแล้วว่าเป็น Container หรืออะไรก็ตาม พยายามหา Edit ข้างใน หรือคลิกเลย
            log(f"   -> เจอช่อง '{target_name}/{target_id_keyword}' -> กรอก: {value}")

            # พยายามหา Edit box ข้างในก่อน (เผื่อเป็น Container)
            try:
                edits = target_elem.descendants(control_type="Edit")
                if edits:
                    target_elem = edits[0]
            except:
                pass

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


def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    is_manual_mode = False

    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        try:
            search_ready = False
            for _ in range(10):
                edits = [e for e in window.descendants(
                    control_type="Edit") if e.is_visible()]
                if edits:
                    search_ready = True
                    break
                time.sleep(0.5)

            edits = [e for e in window.descendants(
                control_type="Edit") if e.is_visible()]
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
        except:
            pass

        log("...กด Enter/ถัดไป เพื่อค้นหารายการ...")
        smart_next(window)
        time.sleep(1.0)

        log("...ตรวจสอบผลลัพธ์ (ค้นหา ID: AddressResult)...")
        found_popup = False
        target_item = None  # เก็บปุ่มที่จะกด

        for _ in range(40):
            # 1. เช็ค Popup Error
            if check_error_popup(window, delay=0.0):
                log("[WARN] ตรวจพบ Popup คำเตือน! -> เข้าโหมด Manual")
                found_popup = True
                break

            # 2. [NEW] เช็คจาก Structure ID: AddressResult (ตาม Log ที่ให้มา)
            # วิธีนี้แม่นยำที่สุด ไม่ขึ้นกับขนาดจอ
            try:
                # หา Container แม่ก่อน
                address_groups = [c for c in window.descendants(
                ) if c.element_info.automation_id == "AddressResult"]

                if address_groups:
                    # ถ้าเจอแม่ ให้หาลูก (ListItem) ทั้งหมด
                    children_items = address_groups[0].descendants(
                        control_type="ListItem")

                    # กรองเฉพาะตัวที่มองเห็น
                    visible_items = [
                        i for i in children_items if i.is_visible()]

                    # [FIX] ตรวจสอบว่ารายการมี text content จริงๆ (ไม่ใช่แค่ element ว่างเปล่า)
                    valid_with_text = []
                    for item in visible_items:
                        try:
                            item_text = item.window_text().strip()
                            # เช็คว่ามี text ที่มีความหมาย (ยาวพอ = มีที่อยู่จริง)
                            if item_text and len(item_text) > 5:
                                valid_with_text.append(item)
                        except:
                            pass

                    if valid_with_text:
                        # *** เลือกตัวแรกสุดที่มี text จริง ***
                        target_item = valid_with_text[0]
                        log(
                            f"[/] เจอ ID 'AddressResult' และรายการย่อย {len(valid_with_text)} รายการ (มี text) -> ล็อคเป้าตัวแรก")
                        break
                    elif visible_items:
                        # เจอ ListItem แต่ไม่มี text = รายการว่าง -> ไม่ใช่ผลลัพธ์จริง
                        log("[WARN] เจอ AddressResult container แต่รายการไม่มี text -> ข้ามไป")
            except:
                pass

            # 3. [Fallback] แผนสำรอง: เผื่อหา ID ไม่เจอ ให้หากว้างๆ แบบเดิม (แต่ลดเงื่อนไขความสูงลง)
            if not target_item:
                try:
                    list_items = [i for i in window.descendants(
                        control_type="ListItem") if i.is_visible()]
                    # เอาแค่ Top > 80 (เผื่อจอเล็กมาก Header บัง)
                    valid_items = [
                        i for i in list_items if i.rectangle().top > 80]
                    # [FIX] กรองเฉพาะรายการที่มี text จริงๆ
                    valid_with_text = []
                    for item in valid_items:
                        try:
                            item_text = item.window_text().strip()
                            if item_text and len(item_text) > 5:
                                valid_with_text.append(item)
                        except:
                            pass

                    if valid_with_text:
                        valid_with_text.sort(key=lambda x: x.rectangle().top)
                        target_item = valid_with_text[0]
                        log(f"[/] เจอ ListItem (Fallback Mode) {len(valid_with_text)} รายการ -> ล็อคเป้าตัวแรก")
                        break
                except:
                    pass

            time.sleep(0.25)

        # --- ส่วนดำเนินการคลิก ---
        if found_popup:
            log("...เข้าสู่โหมดกรอกเอง (Manual Mode) จาก Popup...")
            is_manual_mode = True
            time.sleep(1.0)

        elif target_item:
            # เจอรายการ (ไม่ว่าจะจาก ID หรือ Fallback) -> คลิกเลย
            try:
                log(
                    f"...กำลังคลิกรายการแรก: {target_item.window_text().replace(chr(10), ' ').strip()[:30]}...")
                try:
                    target_item.set_focus()
                except:
                    pass

                target_item.click_input()

                log("...คลิกสำเร็จ -> รอโหลดข้อมูล (2.0s)...")
                is_manual_mode = False  # เจอรายการ = ไม่ต้องกรอกเอง
                time.sleep(2.0)
            except Exception as e:
                log(f"[!] Error ขณะคลิก: {e}")
                is_manual_mode = True  # คลิกไม่ได้ ก็กรอกเอง
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการที่อยู่ -> บังคับเข้า Manual Mode")
            is_manual_mode = True
            smart_next(window)

    return is_manual_mode


def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    """
    หน้ากรอกรายละเอียด: กรอกข้อมูลตามลำดับ 1-8 ที่ระบุมา
    """
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")

    # [FIX] ตัวแปรเพื่อติดตามว่าเจอ Error Popup หรือไม่
    found_error_popup = False

    # วนลูปเช็ค Popup และรอหน้าจอ
    for _ in range(30):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            found_error_popup = True  # [FIX] บันทึกว่าเจอ Error
            time.sleep(1.0)

        # ลองเช็คว่ามีช่องชื่อโผล่มาหรือยัง
        found = False
        for child in window.descendants():
            if "ชื่อ" in child.window_text() or "CustomerFirstName" in str(child.element_info.automation_id):
                found = True
                break
        if found:
            break
        time.sleep(0.5)

    # [FIX] ถ้าเจอ Error Popup = ที่อยู่ที่เลือกไม่ถูกต้อง -> บังคับเข้า Manual Mode
    if found_error_popup and not is_manual_mode:
        log("[FIX] เจอ Error Popup หลังเลือกที่อยู่ -> เปลี่ยนเป็น Manual Mode อัตโนมัติ")
        is_manual_mode = True

    # เริ่มกรอกข้อมูลตามลำดับที่ขอ
    try:
        # 1. ชื่อ (Name: ชื่อ, ID: CustomerFirstName)
        find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)

        # 2. นามสกุล (Name: นามสกุล, ID: CustomerLastName)
        find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

        # 3-7. กรอกที่อยู่ (เฉพาะ Manual Mode)
        if is_manual_mode:
            log("...[Manual Mode] เริ่มกรอกที่อยู่ (ตามลำดับ 3-7)...")
            addr1 = manual_data.get('Address1', '')
            addr2 = manual_data.get('Address2', '')
            province = manual_data.get('Province', '')
            district = manual_data.get('District', '')
            subdistrict = manual_data.get('SubDistrict', '')

            # 3. จังหวัด (ID: AdministrativeArea)
            if not find_and_fill_smart(window, "จังหวัด", "AdministrativeArea", province):
                window.type_keys("{TAB}")
                window.type_keys(province, with_spaces=True)

            # 4. เขต/อำเภอ (ID: Locality)
            if not find_and_fill_smart(window, "เขต/อำเภอ", "Locality", district):
                window.type_keys("{TAB}")
                window.type_keys(district, with_spaces=True)

            # 5. แขวง/ตำบล (ID: DependentLocality)
            if not find_and_fill_smart(window, "แขวง/ตำบล", "DependentLocality", subdistrict):
                window.type_keys("{TAB}")
                window.type_keys(subdistrict, with_spaces=True)

            # 6. ที่อยู่ 1 (ID: StreetAddress1)
            # ถ้าค่าว่าง ระบบจะข้ามไปเลย ไม่คลิกให้เสียเวลา
            find_and_fill_smart(window, "ที่อยู่ 1", "StreetAddress1", addr1)

            # 7. ที่อยู่ 2 (ID: StreetAddress2)
            find_and_fill_smart(window, "ที่อยู่ 2", "StreetAddress2", addr2)

        # 8. เบอร์โทรศัพท์ (Name: หมายเลขโทรศัพท์/โทร, ID: PhoneNumber)
        force_scroll_down(window, -5)
        if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
            find_and_fill_smart(window, "โทร", "Phone", phone)

    except Exception as e:
        log(f"[!] Error Details: {e}")

    # [Dynamic Next] ตรวจสอบบริการพิเศษเพื่อกำหนดจำนวนครั้งการกด
    try:
        config
    except NameError:
        import configparser
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')

    special_services = config['SPECIAL_SERVICES'].get('Services', '').strip()
    loop_count = 3 if special_services else 1

    log(f"...จบขั้นตอนข้อมูลผู้รับ (Services='{special_services}') -> กด 'ถัดไป' {loop_count} ครั้ง...")
    for i in range(loop_count):
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window); time.sleep(1.8)


def process_repeat_transaction(window, should_repeat):
    """
    จัดการ popup และส่งค่ากลับ (Return) ว่าสรุปแล้วคือการทำรายการซ้ำหรือไม่
    """
    log("--- หน้า: ทำรายการซ้ำ (รอ Popup) ---")

    # 1. ตีความค่า Config ให้ชัดเจน (ลบ Space, ลบ Quote, ตัวเล็ก)
    clean_flag = str(should_repeat).strip(
    ).lower().replace("'", "").replace('"', "")
    is_repeat_intent = clean_flag in ['true', 'yes', 'on', '1']

    found_popup = False
    for i in range(30):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=0.5):
            found_popup = True
            break
        time.sleep(0.5)

    if found_popup:
        log("...เจอ Popup ทำรายการซ้ำ...")
        time.sleep(1.0)

        target = "ใช่" if is_repeat_intent else "ไม่"
        log(f"...Config: {should_repeat} -> Intent: {is_repeat_intent} -> เลือก: '{target}'")

        if not smart_click(window, target, timeout=3):
            if target == "ไม่":
                window.type_keys("{ESC}")
            else:
                window.type_keys("{ENTER}")
    else:
        log("[WARN] ไม่พบ Popup ทำรายการซ้ำ (Timeout)")

    # สำคัญ: ส่งค่าความตั้งใจกลับไปบอกฟังก์ชันหลัก
    return is_repeat_intent


def process_payment(window, payment_method, received_amount):
    log("--- ขั้นตอนการชำระเงิน (โหมด Fast Cash) ---")

    # 1. กดรับเงิน (หน้าหลัก)
    log("...ค้นหาปุ่ม 'รับเงิน'...")
    time.sleep(1.5)

    if smart_click(window, "รับเงิน"):
        log("...เข้าสู่หน้าชำระเงิน รอโหลด 1.5s...")
        time.sleep(1.5)
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    # 2. กดปุ่ม Fast Cash (ID: EnableFastCash)
    # ปุ่มนี้คือการจ่ายเงินแบบด่วน (ช่อง 2) ไม่ต้องกรอกตัวเลข
    log("...กำลังกดปุ่ม Fast Cash (ID: EnableFastCash)...")

    # ใช้ฟังก์ชัน click_element_by_id ที่มีอยู่แล้วในโค้ด
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] กดปุ่ม Fast Cash สำเร็จ -> ระบบดำเนินการตัดเงินทันที")
    else:
        log("[WARN] ไม่เจอปุ่ม ID 'EnableFastCash' -> ลองกด Enter เผื่อเข้าระบบอัตโนมัติ")
        window.type_keys("{ENTER}")

    # 3. จบรายการ
    # รอหน้าสรุป/เงินทอน แล้วกด Enter เพื่อปิดบิล
    log("...รอหน้าสรุป/เงินทอน -> กด Enter ปิดรายการ...")
    time.sleep(2.0)  # รอ Animation จ่ายเงิน
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main =================


def run_smart_scenario(main_window, config):
    try:
        # แยกตัวแปร PostalCode ให้ชัดเจน
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        receiver_postal = config['DEPOSIT_ENVELOPE'].get(
            'ReceiverPostalCode', '10110')  # ปลายทาง
        sender_postal = config['TEST_DATA'].get(
            'SenderPostalCode', '10110')  # ต้นทาง (อ่านจาก [TEST_DATA])

        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        special_options_str = config['DEPOSIT_ENVELOPE'].get(
            'SpecialOptions', '')
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get(
            'AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', 'A')
        rcv_lname = config['RECEIVER_DETAILS'].get('LastName', 'B')
        rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '081')
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')

        # Payment Config
        pay_method = config['PAYMENT'].get(
            'Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get(
            'ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'

        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        wait_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))

        manual_data = {
            'Address1': config['MANUAL_ADDRESS_FALLBACK'].get('Address1', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Address2': config['MANUAL_ADDRESS_FALLBACK'].get('Address2', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '') if 'MANUAL_ADDRESS_FALLBACK' in config else ''
        }
    except:
        log("[Error] อ่าน Config ไม่สำเร็จ")
        return

    log(f"--- เริ่มต้นการทำงาน ---")
    log(f"--- ปณ.ต้นทาง: {sender_postal} | ปณ.ปลายทาง: {receiver_postal} ---")
    time.sleep(0.5)

    if not smart_click(main_window, "รับฝากสิ่งของ"):
        return
    time.sleep(step_delay)

    # ส่ง sender_postal ไปใช้ใน popup ข้อมูลผู้ส่ง (หน้าแรก)
    process_sender_info_popup(main_window, phone, sender_postal)

    time.sleep(step_delay)
    if not smart_click_with_scroll(main_window, "กล่องสำเร็จรูปแบบ ง.", scroll_dist=scroll_dist):
        return
    time.sleep(step_delay)
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            if opt:
                smart_click(main_window, opt.strip(), timeout=2)
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)
    handle_prohibited_items(main_window)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    time.sleep(1)

    # ตรงนี้ใช้ receiver_postal (ปลายทาง)
    try:
        log(f"...กรอก ปณ. ปลายทาง: {receiver_postal}")
        main_window.type_keys(str(receiver_postal), with_spaces=True)
    except:
        pass

    smart_next(main_window)
    time.sleep(step_delay)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ")
                found = True
                break
        if found:
            break
        time.sleep(0.5)

    log("...รอหน้าบริการหลัก...")

    # [แก้ไข] เพิ่ม timeout เป็น 60 และใส่ if not เพื่อเช็คว่าถ้าไม่เจอให้หยุดทันที
    target_service_id = "ShippingService_2579"
    if not wait_until_id_appears(main_window, target_service_id, timeout=60):
        log("Error: รอนานเกิน 60 วินาทีแล้ว ยังไม่เข้าหน้าบริการหลัก")
        return

    # คลิก 1 ครั้ง
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] หาปุ่มบริการไม่เจอ ({target_service_id})")
        return
    time.sleep(step_delay)

    if add_insurance_flag.lower() in ['true', 'yes']:
        log(f"...ใส่วงเงิน {insurance_amt}...")
        if click_element_by_id(main_window, "CoverageButton"):
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
                for child in main_window.descendants():
                    if child.element_info.automation_id == "CoverageAmount":
                        child.click_input()
                        child.type_keys(str(insurance_amt), with_spaces=True)
                        break
                time.sleep(0.5)
                submits = [c for c in main_window.descendants(
                ) if c.element_info.automation_id == "LocalCommand_Submit"]
                submits.sort(key=lambda x: x.rectangle().top)
                if submits:
                    submits[0].click_input()
                else:
                    main_window.type_keys("{ENTER}")

    time.sleep(1)
    smart_next(main_window)
    time.sleep(step_delay)
    process_special_services(main_window, special_services)
    time.sleep(step_delay)
    process_sender_info_page(main_window)
    time.sleep(step_delay)

    # 1. ค้นหาที่อยู่ และรับค่าสถานะว่าเป็น Manual Mode หรือไม่?
    is_manual_mode = process_receiver_address_selection(
        main_window, addr_keyword, manual_data)

    time.sleep(step_delay)

    # 2. กรอกรายละเอียดผู้รับ (ส่ง is_manual_mode และ manual_data เข้าไป)
    process_receiver_details_form(
        main_window, rcv_fname, rcv_lname, rcv_phone, is_manual_mode, manual_data)

    time.sleep(step_delay)

    # 1. เรียกฟังก์ชัน และรับค่ากลับมา (ตัวแปรนี้จะได้ค่า True/False จากจุดที่ 1)
    is_repeat_mode = process_repeat_transaction(main_window, repeat_flag)

    # 2. เช็คเลยว่า ถ้าเป็นจริง -> จบการทำงาน
    if is_repeat_mode:
        log("[Logic] ตรวจสอบพบโหมดทำรายการซ้ำ -> หยุดการทำงานทันที")
        return  # ออกจากฟังก์ชันทันที

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
            app = Application(backend="uia").connect(
                title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2:
                    main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")
