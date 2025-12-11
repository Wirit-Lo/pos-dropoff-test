import time
import ctypes
from pywinauto import Desktop

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def main():
    print("="*60)
    print("   เครื่องมือส่อง ID ด้วยเมาส์ (Mouse Inspector)   ")
    print("="*60)
    print("วิธีใช้:")
    print("1. เปิดหน้าจอ POS ให้พร้อม (ให้เห็นปุ่ม + หรือ Popup)")
    print("2. โปรแกรมจะนับถอยหลัง 5 วินาที")
    print("3. ให้รีบเอาเมาส์ไปชี้ค้างไว้ที่ปุ่มที่ต้องการรู้ ID")
    print("="*60)

    while True:
        choice = input("\nกด Enter เพื่อเริ่มจับภาพ (หรือพิมพ์ q เพื่อออก): ")
        if choice.lower() == 'q': break
        
        print("\n...เตรียมตัว... 5 วินาที")
        for i in range(5, 0, -1):
            print(f"   {i}...")
            time.sleep(1)

        mx, my = get_mouse_pos()
        print(f"\n[Capture] ที่พิกัด ({mx}, {my})")

        try:
            # ใช้ AutomationElement จากจุดที่เมาส์ชี้
            elem = Desktop(backend="uia").from_point(mx, my)
            
            # วาดกรอบสีแดงให้รู้ว่าจับโดนตัวไหน
            try: elem.draw_outline(colour='red', thickness=2)
            except: pass

            wrapper = elem.wrapper_object()
            print("-" * 50)
            print(f"TEXT (ชื่อ)        : '{wrapper.window_text()}'")
            print(f"CONTROL TYPE      : {wrapper.element_info.control_type}")
            print(f"AUTOMATION ID     : '{wrapper.element_info.automation_id}'")
            print(f"CLASS NAME        : '{wrapper.element_info.class_name}'")
            print("-" * 50)
            
            # แถม: ดูตัวแม่ (Parent) เผื่อปุ่มจริงคือก้อนใหญ่
            parent = elem.parent()
            if parent:
                p_wrap = parent.wrapper_object()
                print(f"Parent ID         : '{p_wrap.element_info.automation_id}'")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()