#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PNG转ICO格式转换器
将Logo.png转换为icon.ico文件，用于PyInstaller打包
"""

import os
from PIL import Image

def png_to_ico(png_path, ico_path, sizes=None):
    """
    将PNG文件转换为ICO文件
    
    Args:
        png_path: PNG文件路径
        ico_path: 输出ICO文件路径
        sizes: ICO文件包含的尺寸列表，默认为常用尺寸
    """
    if sizes is None:
        # 常用的ICO尺寸
        sizes = [16, 24, 32, 48, 64, 128, 256]
    
    try:
        # 打开PNG图片
        with Image.open(png_path) as img:
            print(f"原始图片尺寸: {img.size}")
            print(f"原始图片模式: {img.mode}")
            
            # 如果图片有透明通道，保持RGBA模式；否则转换为RGB
            if img.mode in ('RGBA', 'LA') or 'transparency' in img.info:
                img = img.convert('RGBA')
                print("保持透明通道")
            else:
                img = img.convert('RGB')
                print("转换为RGB模式")
            
            # 创建不同尺寸的图片列表
            icon_images = []
            for size in sizes:
                # 计算合适的重采样尺寸
                resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                icon_images.append(resized_img)
                print(f"生成 {size}x{size} 尺寸")
            
            # 保存为ICO文件
            icon_images[0].save(
                ico_path,
                format='ICO',
                sizes=[(img.width, img.height) for img in icon_images],
                append_images=icon_images[1:]
            )
            
            print(f"✅ 成功转换: {png_path} -> {ico_path}")
            print(f"ICO文件包含尺寸: {sizes}")
            
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {png_path}")
    except Exception as e:
        print(f"❌ 转换失败: {e}")

def main():
    """主函数"""
    # 项目路径
    project_root = r'C:\ZJR\AscetTool'
    png_path = os.path.join(project_root, 'svg', 'Logo.png')
    ico_path = os.path.join(project_root, 'icon.ico')
    
    print("PNG转ICO转换器")
    print("=" * 50)
    print(f"输入文件: {png_path}")
    print(f"输出文件: {ico_path}")
    print("=" * 50)
    
    # 检查输入文件是否存在
    if not os.path.exists(png_path):
        print(f"❌ 错误: PNG文件不存在 {png_path}")
        return
    
    # 执行转换
    png_to_ico(png_path, ico_path)
    
    # 检查输出文件
    if os.path.exists(ico_path):
        file_size = os.path.getsize(ico_path)
        print(f"📁 ICO文件大小: {file_size:,} 字节")
        
        # 更新PyInstaller配置建议
        print("\n" + "=" * 50)
        print("PyInstaller配置更新建议:")
        print("=" * 50)
        print("将icon参数改为:")
        print(f"icon=r'{ico_path}'")
        print("\n或者使用相对路径:")
        print("icon=os.path.join(PROJECT_ROOT, 'icon.ico')")

if __name__ == "__main__":
    main()