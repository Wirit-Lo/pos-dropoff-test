import configparser
import os
import time
import datetime
import ctypes 
from pywinauto.application import Application
from pywinauto import Desktop

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Inspector Mode (โหมดดึงค่า ID แบบเจาะลึก) =================
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_position_windows():
    """ดึงตำแหน่งเมาส์โดยใช้ Windows API โดยตรง"""
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def print_element_details(element, level_name):
    """ฟังก์ชันช่วยปริ้นข้อมูล Element แบบละเอียดและปลอดภัย"""
    try:
        wrapper = element.wrapper_object()
        print(f"\n[{level_name}] ----------------------------------------")
        
        # พยายามอ่านค่าทีละตัว กัน Error
        try:
            ctype = wrapper.element_info.control_type
            print(f"  Type          : {ctype}")
        except: print("  Type          : <Error>")

        try:
            text = wrapper.window_text()
            print(f"  Text (Name)   : '{text}'")
        except: print("  Text          : <Error>")

        try:
            aid = wrapper.element_info.automation_id
            print(f"  AutomationId  : '{aid}'   <--- มองหาตัวนี้!")
        except: 
            aid = ""
            print("  AutomationId  : <Error>")

        try:
            cls = wrapper.element_info.class_name
            print(f"  ClassName     : {cls}")
        except: print("  ClassName     : <Error>")
        
        return aid # ส่ง ID กลับไปเช็ค
        
    except Exception as e:
        print(f"  [!] อ่านข้อมูล {level_name} ไม่ได้: {e}")
        return None

def run_hover_inspector():
    """
    โหมดโหด V2: ดึง ID แบบเจาะลึก (Leaf -> Parent -> Grandparent)
    """
    log("\n" + "="*60)
    log("       โหมดดึง ID V2: Deep Inspect (ชี้แล้วขุดหาตัวแม่)       ")
    log("="*60)
    log("คำแนะนำ: เอาเมาส์ไปชี้ที่ปุ่ม 'บริการ EMS' ไว้")
    log("ระบบจะนับถอยหลัง 5 วินาที... (เตรียมตัว)")

    for i in range(5, 0, -1):
        log(f"... {i} ...")
        time.sleep(1)

    log("\n[CAPTURE] เริ่มการวิเคราะห์...")
    
    try:
        # 1. ดึงพิกัด
        x, y = get_mouse_position_windows()
        log(f"พิกัดเมาส์: ({x}, {y})")

        # 2. จับ Element ที่เมาส์ชี้ (ตัวลูกสุด)
        target_elem = Desktop(backend="uia").from_point(x, y)
        
        # วาดกรอบสีเขียว (จุดที่ชี้)
        try: target_elem.draw_outline(colour='green', thickness=3)
        except: pass

        # 3. เริ่มรายงานผล (ไต่ระดับขึ้นไปหา ID)
        print("\n" + ">"*20 + " ผลการตรวจสอบ " + "<"*20)
        
        # Level 0: จุดที่ชี้
        found_id = print_element_details(target_elem, "Level 0: จุดที่เมาส์ชี้ (Leaf)")
        
        # ถ้า Level 0 ไม่มี ID หรือ Text ให้ลองดูตัวแม่ (Parent)
        current_elem = target_elem
        for i in range(1, 4): # เช็คย้อนขึ้นไป 3 ระดับ
            try:
                parent = current_elem.wrapper_object().parent()
                if not parent:
                    print(f"\n[End] ไม่มี Parent ต่อแล้ว")
                    break
                
                # วาดกรอบสีเหลือง (ตัวแม่)
                try: parent.draw_outline(colour='yellow', thickness=2)
                except: pass

                pid = print_element_details(parent, f"Level {i}: ตัวแม่ (Parent)")
                
                # ถ้าเจอ ID ที่ไม่ใช่ค่าว่าง ให้ไฮไลท์บอกเลย
                if pid and pid.strip() != "":
                    print(f"\n*** เจอ ID ที่น่าใช้ใน Level {i} !!! ***")
                    print(f"*** แนะนำให้ใช้: '{pid}' ***")
                
                current_elem = parent
            except Exception as e:
                print(f"\n[!] ไม่สามารถดึง Parent Level {i}: {e}")
                break

        log("\n" + "="*60)
        log("วิธีใช้: เลือก AutomationId ที่ดูสื่อความหมายที่สุด (มักจะอยู่ Level 1 หรือ 2)")
        log("นำไปใส่ในโค้ด: smart_click(window, ['ค่าIDที่เจอ'])")
        log("="*60)

    except Exception as e:
        log(f"[Error] เกิดข้อผิดพลาดร้ายแรง: {e}")
        log("ลองรันใหม่อีกครั้ง")

# ================= 3. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting to POS Application...")
        try:
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            
            # เด้งหน้าต่างขึ้นมา
            win.set_focus()
            try:
                if win.get_show_state() == 2: win.restore()
            except: pass

            log("[/] Ready! เตรียมชี้เมาส์...")
            time.sleep(1) 
            
            run_hover_inspector()
            
        except Exception as e:
            log(f"Error Connecting: {e}")
    else:
        log("ไม่พบไฟล์ Config")