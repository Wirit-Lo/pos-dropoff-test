import os
from pywinauto.application import Application
from pywinauto import Desktop

def generate_ui_report():
    print("--- Pywinauto UI Inspector Tool ---")
    print("เครื่องมือนี้จะช่วยดึงรายชื่อปุ่มและ ID ทั้งหมดออกมาเป็นไฟล์ Text")
    
    # 1. ค้นหาหน้าต่างทั้งหมดที่เปิดอยู่ เพื่อหาชื่อที่ถูกต้อง
    print("\n[1] กำลังค้นหาหน้าต่างที่เปิดอยู่ (backend='uia')...")
    try:
        # ใช้ Desktop เพื่อกวาดดูทุกโปรแกรม
        windows = Desktop(backend="uia").windows()
        pos_window = None
        
        print(f"พบหน้าต่างทั้งหมด {len(windows)} รายการ:")
        for w in windows:
            w_text = w.window_text()
            if w_text:
                print(f" - {w_text}")
                # พยายามจับหน้าต่างที่มีคำว่า POS หรือชื่อที่ใกล้เคียง
                if "POS" in w_text or "Riposte" in w_text:
                    pos_window = w
        
        if not pos_window:
            print("\n[!] ไม่พบหน้าต่างที่มีคำว่า 'POS' หรือ 'Riposte'")
            target_name = input("กรุณาพิมพ์ชื่อ Title bar ของโปรแกรมคุณ (บางส่วนก็ได้): ")
            # ค้นหาใหม่ตามชื่อที่พิมพ์
            for w in windows:
                if target_name in w.window_text():
                    pos_window = w
                    break
        
        if pos_window:
            real_title = pos_window.window_text()
            print(f"\n[2] พบเป้าหมาย: '{real_title}'")
            print("...กำลังเชื่อมต่อ (Connect)...")
            
            # เชื่อมต่อแบบระบุ found_index=0 เพื่อกัน Error กรณีเจอหลายหน้าต่างซ้อนกัน
            app = Application(backend="uia").connect(title=real_title, found_index=0, timeout=10)
            win = app.top_window()
            
            # สร้างชื่อไฟล์ Report
            report_file = "UI_Structure_Report.txt"
            print(f"[3] กำลังวิเคราะห์โครงสร้างหน้าจอ และบันทึกลงไฟล์ '{report_file}'...")
            print("    (อาจใช้เวลา 10-30 วินาที หากหน้าจอซับซ้อน)...")
            
            # คำสั่งสำคัญ: print_control_identifiers() จะปริ้นโครงสร้างทั้งหมด
            # เราจะ Redirect ผลลัพธ์ลงไฟล์แทนการปริ้นหน้าจอ
            try:
                with open(report_file, "w", encoding="utf-8") as f:
                    # depth=None คือเอาทุกระดับชั้น (ลึกสุด)
                    win.print_control_identifiers(depth=None, filename=report_file)
                
                print(f"\n[SUCCESS] สร้างรายงานเรียบร้อยแล้ว!")
                print(f" -> ให้เปิดไฟล์ '{report_file}'")
                print(f" -> กด Ctrl+F ค้นหาคำว่า 'E' หรือชื่อปุ่มที่คุณกดไม่ได้")
                print(f" -> ดูบรรทัดเหนือชื่อนั้น จะมี 'auto_id', 'control_type' ให้ก๊อปมาใช้")
                
            except Exception as e:
                print(f"Error writing report: {e}")
                
        else:
            print("\n[FAILED] หาหน้าต่างโปรแกรมไม่เจอ กรุณาเปิดโปรแกรม POS ก่อนรันสคริปต์นี้")

    except Exception as e:
        print(f"\n[Error] เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    generate_ui_report()
    