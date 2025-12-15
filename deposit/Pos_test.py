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

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบเฉพาะส่วน Popup ---")
    
    # 1. กดปุ่มบริการหลัก (ShippingService_2580)
    # หมายเหตุ: ต้องเปิดหน้านี้รอไว้ก่อนรัน
    wait_until_id_appears(main_window, "ShippingService_2580", timeout=5)
    if not click_element_by_id(main_window, "ShippingService_2580"):
        log("[Error] หาปุ่มบริการไม่เจอ (ShippingService_2580)")
        return

    # 2. เริ่มกระบวนการจัดการ Popup
    qty = config['PRODUCT_QUANTITY'].get('Quantity', '5') if 'PRODUCT_QUANTITY' in config else '5' # ลองเปลี่ยนเลขเทสดู
    log(f"...รอ Popup 'จำนวน' (จะใส่เลข: {qty})...")
    
    time.sleep(1.5) # รอ Animation

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
            app_top = Application(backend="uia").connect(active_only=True).top_window()
            log(f"-> ตรวจสอบ Top Window: {app_top.window_text()}")
            if "จำนวน" in app_top.window_text() or "Escher" in app_top.window_text():
                popup_window = app_top
        except Exception as e:
            log(f"-> Error หา Top Window: {e}")

    # --- เริ่มเจาะหาช่อง Edit ---
    if popup_window:
        popup_window.set_focus()
        log("...กำลังสแกนหาช่อง Edit ใน Popup...")
        
        target_edit = None
        
        # ดึง Edit ทั้งหมดออกมาดู
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
        log("[Error] หา Popup Window ไม่เจอเลย")

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
            