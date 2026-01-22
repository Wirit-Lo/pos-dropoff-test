import os

# ==============================================================================
# 🎯 เป้าหมาย: แก้ไฟล์ Customsize2.py
# ==============================================================================
target_file = "Customsize2.py"

# ==============================================================================
# 🛠️ โค้ดที่จะซ่อม
# ==============================================================================

# สิ่งที่ต้องหา (บรรทัดที่เกิด Error)
ERROR_POINT_KEYWORD = "special_services = config['SPECIAL_SERVICES']"

# สิ่งที่จะเติมเข้าไปข้างหน้า (ประกาศตัวแปร config)
CONFIG_LOADER_CODE = """    # [Fix] โหลด Config ก่อนใช้งาน
    import configparser
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    """

# สิ่งที่จะเติมหัวไฟล์ (ถ้ายังไม่มี)
IMPORT_LINE = "import configparser"

# ==============================================================================
# 🚀 เริ่มทำงาน
# ==============================================================================

if not os.path.exists(target_file):
    print(f"❌ ไม่พบไฟล์ {target_file}")
else:
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        is_fixed = False
        has_import = False

        # 1. เช็ค Import ก่อน
        for line in lines:
            if "import configparser" in line:
                has_import = True
                break
        
        # ถ้ายังไม่มี Import ให้เติมบรรทัดแรก
        if not has_import:
            new_lines.append("import configparser\n")

        # 2. วนลูปหาจุดแก้
        for line in lines:
            # ถ้าเจอบรรทัดที่เป็นจุดตาย (ใช้ config แต่ยังไม่มี config)
            if ERROR_POINT_KEYWORD in line and "config =" not in line:
                # เติมตัวโหลด config เข้าไปก่อนหน้า (รักษาย่อหน้าเดิม)
                indentation = line.split(ERROR_POINT_KEYWORD)[0] # จับย่อหน้า
                # ล้าง whitespace ของ indentation ออกจาก string ที่เราเตรียมไว้ก่อนเติม
                fixed_block = CONFIG_LOADER_CODE.replace("    ", indentation, 1) # แค่บรรทัดแรก
                # หรือใช้วิธีง่ายกว่าคือ เติมดื้อๆ แล้วให้ Python จัดการ scope (แต่อาจไม่สวย)
                
                # วิธีปลอดภัย: เติมเข้าไปเลย
                new_lines.append(f"{indentation}import configparser\n")
                new_lines.append(f"{indentation}config = configparser.ConfigParser()\n")
                new_lines.append(f"{indentation}config.read('config.ini', encoding='utf-8')\n")
                
                new_lines.append(line) # ใส่บรรทัดเดิมตามไป
                is_fixed = True
                print(f"🔧 เจอจุดแก้! แทรก Config Loader ให้แล้ว")
            else:
                new_lines.append(line)

        if is_fixed:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✅ {target_file}: ซ่อม Error 'config not defined' เรียบร้อยครับ")
        else:
            print(f"⚠️ {target_file}: ไม่พบจุดที่ต้องแก้ หรืออาจจะแก้ไปแล้ว")

    except Exception as e:
        print(f"🔥 Error: {e}")