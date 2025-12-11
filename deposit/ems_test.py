import configparser
import os
import time
import ctypes
from pywinauto.application import Application
from pywinauto import Desktop

# โหลด Config เพื่อหาชื่อหน้าต่าง
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def run_element_inspector():
    conf = load_config()
    if not conf:
        print("ไม่พบไฟล์ config.ini")
        return

    print("Connecting...")
    try:
        # เชื่อมต่อเพื่อดึงหน้าต่างขึ้นมา
        app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=10)
        win = app.top_window()
        win.set_focus()
        
        # ดึงหน้าต่างขึ้นมา (Restore if minimized)
        if win.get_show_state() == 2:
            win.restore()

        print("\n" + "="*60)
        print("   เครื่องมือค้นหาชื่อปุ่มที่แท้จริง (Name Inspector)   ")
        print("="*60)
        print("คำแนะนำ: เอาเมาส์ไปชี้ที่ 'ปุ่มบริการ EMS' แล้วอยู่นิ่งๆ")
        print("ระบบจะดึง 'ชื่อ (Text)' ที่คอมพิวเตอร์มองเห็นออกมาให้")
        print("นับถอยหลัง 5 วินาที... เริ่ม!")
        
        for i in range(5, 0, -1):
            print(f"... {i} ...")
            time.sleep(1)
            
        # 1. จับพิกัดเมาส์
        mx, my = get_mouse_pos()
        print(f"\n[CAPTURE] ดึงข้อมูลที่พิกัดเมาส์ ({mx}, {my})...")
        
        # 2. หา Element ที่เมาส์ชี้อยู่ (UIA Backend)
        elem = Desktop(backend="uia").from_point(mx, my)
        
        # 3. แสดงผลลัพธ์แบบเจาะลึก (ดูทั้งตัวมันเอง และตัวแม่)
        # บ่อยครั้งที่ Text เป็นแค่ป้ายชื่อ แต่ตัวปุ่มจริงๆ คือตัวแม่ (Parent)
        
        print("\n" + "-"*30)
        print(" 1. สิ่งที่เมาส์ชี้อยู่ (Child/Text) ")
        print("-" * 30)
        try:
            # วาดกรอบสีเขียว
            elem.draw_outline(colour='green', thickness=2)
            
            wrapper = elem.wrapper_object()
            text = wrapper.window_text()
            control_type = wrapper.element_info.control_type
            
            print(f"   ชื่อที่เห็น (Text)   : '{text}'  <-- ลองก๊อปปี้ค่านี้ไปใช้")
            print(f"   ชนิด (Type)          : {control_type}")
            print(f"   AutomationId         : '{wrapper.element_info.automation_id}'")
        except Exception as e:
            print(f"   Error reading element: {e}")

        # ดูตัวแม่ (Parent) - เผื่อปุ่มจริงคือกรอบนอก
        parent = elem.parent()
        if parent:
            print("\n" + "-"*30)
            print(" 2. ตัวแม่/กรอบนอก (Parent) ")
            print("-" * 30)
            try:
                # วาดกรอบสีเหลือง
                parent.draw_outline(colour='yellow', thickness=2)
                
                p_wrapper = parent.wrapper_object()
                p_text = p_wrapper.window_text()
                p_type = p_wrapper.element_info.control_type
                
                print(f"   ชื่อที่เห็น (Text)   : '{p_text}'  <-- หรือค่านี้")
                print(f"   ชนิด (Type)          : {p_type}")
                print(f"   AutomationId         : '{p_wrapper.element_info.automation_id}'")
            except:
                print("   (ไม่สามารถอ่านค่า Parent ได้)")

        print("\n" + "="*60)
        print("สรุป: ให้ก๊อปปี้ข้อความในช่อง 'ชื่อที่เห็น (Text)' ไปใส่ในโค้ด")
        print("ตัวอย่าง: smart_click(window, 'ค่าที่คุณเห็นตรงนี้')")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_element_inspector()