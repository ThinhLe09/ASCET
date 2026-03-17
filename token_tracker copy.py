# test_ascet_615.py
import sys, struct, platform

PROGID = "Ascet.Ascet.6.1.5"

def main() -> int:
    print("="*60)
    print("ASCET 6.1.5 COM 连接测试")
    print("="*60)
    print(f"Python {platform.python_version()} / {struct.calcsize('P')*8}-bit on {platform.system()}")
    print(f"Target ProgID: {PROGID}")

    try:
        import pythoncom
        from win32com.client import GetActiveObject, gencache, DispatchEx
    except Exception as e:
        print("× 缺少 pywin32，请先安装：pip install pywin32")
        print("  错误：", e)
        return 2

    # 1) 先尝试连接已运行实例
    try:
        app = GetActiveObject(PROGID)
        print("✓ 已连接到正在运行的 ASCET 实例（GetActiveObject）")
    except Exception:
        app = None

    # 2) 如无已运行实例，则创建
    if app is None:
        try:
            app = gencache.EnsureDispatch(PROGID)
            print("✓ 已创建 ASCET 实例（EnsureDispatch）")
        except Exception:
            try:
                app = DispatchEx(PROGID)
                print("✓ 已创建 ASCET 实例（DispatchEx）")
            except Exception as e:
                print(f"❌ 无法创建/连接：{e}")
                print("  提示：若报 0x80040154/无效类字符串，多半是位数不匹配或未完成注册。")
                return 1

    # 3) 试探数据库
    try:
        db = app.GetCurrentDataBase()
    except Exception as e:
        print("⚠️ 调用 GetCurrentDataBase() 异常：", e)
        db = None

    if db:
        try:
            name = db.GetName()
        except Exception:
            name = "(无法读取名称)"
        print(f"✓ 连接成功，当前数据库：{name}")
    else:
        print("⚠️ 已连接到应用，但未检测到当前数据库（可能 GUI 未打开工程）。")

    print("✅ 测试完成。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
