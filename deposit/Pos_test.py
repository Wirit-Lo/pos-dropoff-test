import configparser
import os
import time
import datetime
from pywinauto.application import Application

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
def click_element_by_id(window, exact_id, timeout=2):
    """ฟังก์ชันพื้นฐานสำหรับกดปุ่ม (ใช้ภายใน)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if found:
                found[0].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except: pass
        time.sleep(0.3)
    return False

def find_and_click_with_scroll(window, target_id, max_attempts=5):
    """
    [UPDATED] ค้นหาปุ่มและกด โดยเช็คว่าปุ่มตกขอบจอหรือโดนบังหรือไม่
    ถ้าอยู่ชิดขวาเกินไป จะกดปุ่มเลื่อนหน้าจอก่อน
    """
    log(f"...ค้นหา ID: {target_id} (พร้อมตรวจสอบตำแหน่ง)...")
    
    for i in range(max_attempts):
        try:
            # 1. ค้นหา Element ใน Tree
            found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
            
            should_click = False
            if found:
                target = found[0]
                rect = target.rectangle()
                win_rect = window.rectangle()
                
                # คำนวณจุดกึ่งกลางของปุ่มเป้าหมาย
                center_x = (rect.left + rect.right) // 2
                
                # กำหนดเส้นขอบเขตปลอดภัย (Safe Zone) ประมาณ 85% ของความกว้างหน้าจอ
                # ถ้าเกินนี้แสดงว่าอาจจะโดนปุ่มลูกศรขวาบังอยู่
                safe_limit = win_rect.left + (win_rect.width() * 0.85)
                
                if center_x < safe_limit:
                    # อยู่ในระยะปลอดภัย -> กดได้เลย
                    log(f"   [/] พบปุ่มในระยะปลอดภัย (X={center_x}) -> กำลังกด...")
                    target.click_input()
                    return True
                else:
                    log(f"   [!] พบปุ่ม '{target_id}' แต่อยู่ชิดขอบขวาเกินไป (X={center_x}) -> ต้องเลื่อนก่อน")
            else:
                log(f"   [Attempt {i+1}] ยังไม่พบปุ่ม '{target_id}' ในหน้าจอ")

            # 2. ปฏิบัติการเลื่อนหน้าจอ (Scroll Action)
            log("   -> กำลังสั่งเลื่อนหน้าจอไปทางขวา...")
            
            scroll_success = False
            
            # วิธี A: หาปุ่มลูกศรขวาบนหน้าจอ (UI Button) แล้วกด
            # ปกติปุ่มเลื่อนจะอยู่ขวาสุดของจอ
            try:
                buttons = [b for b in window.descendants(control_type="Button") if b.is_visible()]
                right_arrow_btn = None
                
                # กรองหาปุ่มที่อยู่ขวาสุด (Top-Right หรือ Right-Center)
                for btn in buttons:
                    b_rect = btn.rectangle()
                    # ถ้าปุ่มอยู่ขวาสุด (90% ขึ้นไป) และไม่ใช่ปุ่มที่เราจะกด
                    if b_rect.left > win_rect.left + (win_rect.width() * 0.92):
                        right_arrow_btn = btn
                        break
                
                if right_arrow_btn:
                    right_arrow_btn.click_input()
                    log("      กดปุ่มลูกศรขวาบนหน้าจอ (UI Scroll Button)")
                    scroll_success = True
            except Exception as e:
                log(f"      Error หาปุ่มเลื่อน: {e}")

            # วิธี B: ถ้าหาปุ่มไม่เจอ ให้ใช้คีย์บอร์ด
            if not scroll_success:
                window.type_keys("{RIGHT}")
                log("      ใช้คีย์บอร์ดกดลูกศรขวา {RIGHT}")
            
            time.sleep(1.5) # รอ Animation เลื่อนให้เสร็จสำคัญมาก

        except Exception as e:
            log(f"Error Loop: {e}")
            time.sleep(1)

    log(f"[Fail] ไม่สามารถกดปุ่ม {target_id} ได้หลังจากลอง {max_attempts} ครั้ง")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (ระบบ Scroll อัจฉริยะ) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ (พร้อมระบบแก้การบัง)
    target_service_id = "ShippingService_2583" # ID ที่ต้องการ
    
    if not find_and_click_with_scroll(main_window, target_service_id):
        log(f"[Error] จบการทำงาน: หา/กดปุ่ม {target_service_id} ไม่สำเร็จ")
        return

    # [เพิ่ม] กด Enter (ถัดไป) เพื่อเรียก Popup ขึ้นมา
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(1.0)
    main_window.type_keys("{ENTER}")

    # 2. เริ่มกระบวนการจัดการ Popup
    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    
    time.sleep(1.5) # รอ Animation Popup เด้ง

    # --- ค้นหา Popup ---
    popup_window = None
    
    # หา Top Window
    try:
        app_top = Application(backend="uia").connect(active_only=True).top_window()
        if "จำนวน" in app_top.window_text() or app_top.element_info.control_type == "Window":
            popup_window = app_top
            log(f"-> เจอ Top Window: {app_top.window_text()}")
    except: pass
    
    # ถ้าไม่เจอ ลองหา Child
    if not popup_window:
        try:
            children = main_window.children(control_type="Window")
            if children: popup_window = children[0]
        except: pass

    # --- เริ่มเจาะหาช่อง Edit ---
    if popup_window:
        try: popup_window.set_focus()
        except: pass
        
        log("...สแกนหาช่อง Edit ใน Popup...")
        
        target_edit = None
        try:
            edits = [e for e in popup_window.descendants(control_type="Edit") if e.is_visible()]
            valid_edits = [e for e in edits if e.rectangle().width() > 30] # กรองปุ่มเล็กๆทิ้ง
            
            if valid_edits:
                target_edit = valid_edits[0]
                log(f"-> เป้าหมาย: {target_edit} (ID: {target_edit.element_info.automation_id})")
        except: pass

        if target_edit:
            try:
                # 1. Focus & Clear
                target_edit.click_input()
                time.sleep(0.2)
                target_edit.type_keys("^a{DELETE}", pause=0.1)
                
                # 2. Type & Enter
                target_edit.type_keys(str(qty), with_spaces=True)
                log(f"-> พิมพ์เลข {qty} เรียบร้อย")
                time.sleep(0.5)
                popup_window.type_keys("{ENTER}")
                log("-> กด Enter (ถัดไป) เรียบร้อย")
            except Exception as e:
                log(f"Error ขณะพิมพ์: {e}")
        else:
            log("[Warning] หาช่องไม่เจอ -> Blind Type")
            popup_window.type_keys(str(qty), with_spaces=True)
            popup_window.type_keys("{ENTER}")
    else:
        log("[Error] หา Popup Window ไม่เจอ")

    log("--- จบการทดสอบ ---")

# ================= 4. Run =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        try:
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to: {app_title}")
            app = Application(backend="uia").connect(title_re=app_title, timeout=10)
            main_window = app.top_window()
            main_window.set_focus()
            
            test_popup_process(main_window, conf)
            
        except Exception as e:
            log(f"Error Connect: {e}")