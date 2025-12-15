import time
import datetime
import sys
# ตรวจสอบและ Import library ที่จำเป็น
try:
    from pywinauto import uia_element_info
    from pywinauto import mouse
except ImportError:
    print("Error: ไม่พบไลบรารี pywinauto กรุณาติดตั้ง: pip install pywinauto")
    sys.exit(1)

def get_current_element_info():
    """ดึงข้อมูล Element ณ ตำแหน่งเมาส์ปัจจุบัน"""
    try:
        x, y = mouse.get_cursor_pos()
        # ดึง UI Element จากจุดพิกัด (UIA Mode)
        elem = uia_element_info.UIAElementInfo.from_point(x, y)
        return x, y, elem
    except Exception as e:
        return x, y, None

def print_separator():
    print("-" * 60)

def main():
    print("============================================================")
    print("   UI INSPECTOR (TIMER MODE) - By Gemini")
    print("   1. โปรแกรมจะนับถอยหลัง 5 วินาที")
    print("   2. ให้เอาเมาส์ไปชี้ค้างไว้ที่ปุ่มที่ต้องการ")
    print("   3. เมื่อครบเวลา ข้อมูลจะถูกบันทึกลง Log ด้านล่าง")
    print("   (กด Ctrl+C เพื่อหยุดโปรแกรม)")
    print("============================================================")
    print("")

    try:
        while True:
            # --- ส่วนนับถอยหลัง ---
            for i in range(5, 0, -1):
                # ใช้ \r เพื่อเขียนทับบรรทัดเดิมตอนนับเวลา
                print(f"   ⏳ กำลังจะบันทึกค่าในอีก {i} วินาที... (ชี้เมาส์รอไว้เลย)", end='\r')
                time.sleep(1)
            
            # --- ส่วนบันทึกข้อมูล (Capture) ---
            # ล้างบรรทัดนับถอยหลัง
            print(" " * 60, end='\r') 
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            x, y, elem = get_current_element_info()

            print(f"[{timestamp}] 📸 บันทึกข้อมูลที่พิกัด ({x}, {y})")
            print_separator()

            if elem:
                # ดึงค่าต่างๆ (ใช้ .get() หรือเข้าถึง attribute ตรงๆ แล้วแต่ version)
                name = elem.name
                auto_id = elem.automation_id
                control_type = elem.control_type
                class_name = elem.class_name
                rect = elem.rectangle

                # แสดงผล Automation ID (ตัวสำคัญสุด)
                if auto_id:
                    print(f"   🔑 Automation ID :  '{auto_id}'  <-- (ก๊อปปี้ค่านี้ไปใช้)")
                else:
                    print(f"   🔑 Automation ID :  (ไม่มี/Empty)")

                print(f"   🏷️  Name (Text)   :  '{name}'")
                print(f"   📦 Control Type  :  {control_type}")
                print(f"   💻 Class Name    :  {class_name}")
                
                if rect:
                    print(f"   🔲 Rectangle     :  (L:{rect.left}, T:{rect.top}, R:{rect.right}, B:{rect.bottom})")
                    print(f"   📐 Width/Height  :  W={rect.width()}, H={rect.height()}")
                
                # วิเคราะห์เบื้องต้นให้
                if not auto_id and not name:
                    print("\n   ⚠️  คำแนะนำ: Element นี้ไม่มีทั้ง ID และชื่อ")
                    print(f"       ลองใช้พิกัดแทน: click_input(coords=({x}, {y}))")
            else:
                print("   ❌ ไม่พบ UI Element (อาจจะเป็นพื้นที่ว่างหรือโปรแกรมเข้าถึงไม่ได้)")
            
            print_separator()
            print("\n") # เว้นบรรทัดเตรียมรอบต่อไป

    except KeyboardInterrupt:
        print("\n--- จบการทำงาน ---")

if __name__ == "__main__":
    main()