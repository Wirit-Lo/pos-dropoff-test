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
def find_scroll_button_strict(window):
    """
    ค้นหาปุ่มเลื่อน (Scroll) แบบเข้มงวด
    1. ตัดปุ่มที่อยู่โซนล่าง (Payment/Total) ทิ้ง
    2. ตัดปุ่ม Help/Info ทิ้ง
    3. เน้นปุ่มที่อยู่ขวาสุด
    """
    try:
        win_rect = window.rectangle()
        # กำหนดเส้นแบ่ง: สนใจเฉพาะปุ่มที่อยู่เหนือ 75% ของความสูงหน้าจอ (กันไปโดนปุ่มข้างล่าง)
        cutoff_y = win_rect.top + (win_rect.height() * 0.75)
        
        # รายชื่อ ID ที่ห้ามกด
        blacklist_ids = ["ShowHelpText", "ServiceGroupShowHelpText", "Help", "Info", 
                         "Total", "Summary", "Cart", "Payment", "Notification", "GlobalCommand"]

        candidates = []
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        
        valid_buttons = []
        for btn in candidates:
            if not btn.is_visible(): continue
            
            r = btn.rectangle()
            center_y = (r.top + r.bottom) // 2
            aid = btn.element_info.automation_id
            text = btn.window_text()

            # กฏที่ 1: ต้องไม่อยู่โซนล่าง (ต่ำกว่าเส้น Cutoff)
            if center_y > cutoff_y: continue
            
            # กฏที่ 2: ต้องอยู่ด้านขวา (ขวากว่า 85% ของจอ)
            if r.left < win_rect.left + (win_rect.width() * 0.85): continue

            # กฏที่ 3: ห้ามติด Blacklist
            if any(b in aid for b in blacklist_ids): continue
            
            # กฏที่ 4: ปุ่มเลื่อนมักจะแคบ (Width < 150)
            if r.width() > 150: continue

            # ถ้าผ่านทุกข้อ เก็บไว้พิจารณา
            # ให้คะแนนพิเศษถ้ามีคำว่า Arrow หรือ Scroll
            score = 1
            if "Arrow" in aid or "Scroll" in aid or ">" in text: score += 5
            
            valid_buttons.append((score, btn))
        
        if valid_buttons:
            # เรียงตามคะแนน และ ความขวาสุด
            valid_buttons.sort(key=lambda x: (x[0], x[1].rectangle().left), reverse=True)
            best_btn = valid_buttons[0][1]
            # log(f"      [Debug] เจอปุ่มเลื่อน: {best_btn.element_info.automation_id} (Y={best_btn.rectangle().top})")
            return best_btn
            
    except Exception as e:
        log(f"Error finding scroll button: {e}")
    
    return None

def find_and_click_with_rotate_logic(window, target_id, max_rotations=10):
    """
    ค้นหาปุ่มแบบ Rotate Loop (ตาม Log ที่คุณต้องการ)
    """
    log(f"...ค้นหา ID '{target_id}' (โหมดเลื่อนหาไว)...")
    
    for i in range(1, max_rotations + 1):
        # 1. ลองหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
        
        target_ready = False
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            # Safe Zone: ต้องไม่ชิดขอบขวาเกินไป (75-80%)
            safe_limit = win_rect.left + (win_rect.width() * 0.8) 
            
            if rect.right < safe_limit:
                 log(f"   [/] เจอ '{target_id}' ใน Safe Zone -> คลิก")
                 try:
                    target.click_input()
                 except:
                    # ถ้าคลิกไม่ติด ให้ลอง Focus + Enter
                    target.set_focus()
                    window.type_keys("{ENTER}")
                 return True
            else:
                 log(f"   [Rotate {i}] เจอ '{target_id}' แต่อยู่ชิดขอบขวา -> เลื่อนหา (Scroll)")
        else:
            log(f"   [Rotate {i}] ไม่เจอ '{target_id}' -> เลื่อนหา (Scroll)")
        
        # 2. สั่งเลื่อน (Scroll)
        scroll_btn = find_scroll_button_strict(window)
        if scroll_btn:
            try:
                scroll_btn.click_input()
            except:
                window.type_keys("{RIGHT}")
        else:
            # ถ้าหาปุ่มเลื่อนไม่เจอจริงๆ ให้กดลูกศรขวาแทน
            # log("      [Debug] ไม่เจอปุ่มเลื่อน -> ใช้ปุ่มลูกศรขวา {RIGHT}")
            window.type_keys("{RIGHT}")
            
        time.sleep(1.2) # รอ Animation เลื่อน
        
    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}'")
    
    # Debug: ปริ้นท์รายการ Text ที่เห็น (เหมือนใน Log เก่า)
    try:
        visible_texts = []
        for c in window.descendants():
            txt = c.window_text()
            if txt and txt.strip(): visible_texts.append(txt)
        # log(f"รายการ Text ที่เจอในหน้านี้: {visible_texts[:10]}...") 
    except: pass
    
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (Rotate Logic & Strict Scroll) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ (ด้วย Logic ใหม่)
    target_service_id = "ShippingService_2583" 
    
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] ไม่สามารถกดปุ่ม {target_service_id} ได้")
        return

    # [ส่วน Popup เดิม - ไม่แตะต้อง]
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(1.0)
    main_window.type_keys("{ENTER}")

    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    time.sleep(1.5)

    popup_window = None
    try:
        app_top = Application(backend="uia").connect(active_only=True).top_window()
        if ("จำนวน" in app_top.window_text() or app_top.element_info.control_type == "Window") and "Riposte" not in app_top.window_text():
            popup_window = app_top
    except: pass
    
    if not popup_window:
        try:
            children = main_window.children(control_type="Window")
            if children: popup_window = children[0]
        except: pass

    if popup_window:
        try: popup_window.set_focus()
        except: pass
        
        target_edit = None
        try:
            edits = [e for e in popup_window.descendants(control_type="Edit") if e.is_visible()]
            valid_edits = [e for e in edits if e.rectangle().width() > 30]
            if valid_edits: target_edit = valid_edits[0]
        except: pass

        if target_edit:
            try:
                target_edit.click_input()
                time.sleep(0.2)
                target_edit.type_keys("^a{DELETE}", pause=0.1)
                time.sleep(0.1)
                target_edit.type_keys(str(qty), with_spaces=True)
                popup_window.type_keys("{ENTER}")
                log("-> พิมพ์เลขและกด Enter (ถัดไป) เรียบร้อย")
            except Exception as e:
                log(f"Error: {e}")
        else:
            log("[Warning] ไม่เจอช่อง Edit -> พิมพ์ใส่ Window เลย")
            popup_window.type_keys(str(qty), with_spaces=True)
            popup_window.type_keys("{ENTER}")
    else:
        log("[Error] หา Popup ไม่เจอ")

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