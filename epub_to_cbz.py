import os
import re
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# ===== 配置区域 =====
OUTPUT_DIR = "comic_output"  # 输出目录
# ===================

def find_opf_file(epub_dir):
    """在解压目录中定位OPF文件"""
    container_path = epub_dir / "META-INF" / "container.xml"
    if not container_path.exists():
        raise FileNotFoundError("container.xml not found in META-INF")
    
    tree = ET.parse(container_path)
    root = tree.getroot()
    ns = {'n': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    rootfile = root.find('.//n:rootfile', ns)
    if rootfile is None:
        raise ValueError("OPF file path not found in container.xml")
    return epub_dir / rootfile.attrib['full-path']

def parse_opf(opf_path):
    """解析OPF文件获取资源清单和阅读顺序"""
    tree = ET.parse(opf_path)
    root = tree.getroot()
    ns = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    
    # 获取manifest资源列表
    manifest = {}
    for item in root.findall('.//opf:manifest/opf:item', ns):
        manifest[item.attrib['id']] = item.attrib['href']
    
    # 获取spine阅读顺序
    spine = []
    spine_elements = root.findall('.//opf:spine/opf:itemref', ns)
    for itemref in spine_elements:
        spine.append(itemref.attrib['idref'])
    
    return manifest, spine

def extract_images(epub_dir, opf_path, manifest, spine):
    """按阅读顺序提取图片资源"""
    opf_dir = opf_path.parent
    image_files = []
    supported_formats = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    
    # 遍历spine顺序获取图片
    for item_id in spine:
        if item_id not in manifest:
            continue
            
        item_path = opf_dir / manifest[item_id]
        if not item_path.exists():
            continue
        
        # 检查是否是图片文件
        if item_path.suffix.lower() in supported_formats:
            image_files.append(item_path)
            continue
        
        # 解析HTML文件获取图片
        if item_path.suffix.lower() in ('.html', '.xhtml'):
            try:
                # 使用HTML解析器提取图片
                with open(item_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找所有图片标签
                img_tags = re.findall(r'<img[^>]+src="([^">]+)"', content, re.IGNORECASE)
                for img_src in img_tags:
                    # 处理相对路径
                    img_path = (item_path.parent / img_src).resolve()
                    if img_path.exists() and img_path.suffix.lower() in supported_formats:
                        image_files.append(img_path)
            except Exception as e:
                print(f"  Error processing {item_path}: {str(e)}")
    
    return image_files

def create_cbz(image_files, output_dir, base_name):
    """创建CBZ文件和图片文件夹"""
    img_dir = output_dir / f"{base_name}_img"
    os.makedirs(img_dir, exist_ok=True)
    
    # 复制图片并重命名
    for i, img_path in enumerate(image_files, start=1):
        # 确保文件存在
        if not img_path.exists():
            continue
            
        ext = img_path.suffix
        # 处理可能的无扩展名情况
        if not ext:
            # 尝试从MIME类型推断
            try:
                with open(img_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b"\xFF\xD8\xFF"):
                        ext = ".jpg"
                    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
                        ext = ".png"
                    elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
                        ext = ".gif"
                    elif header.startswith(b"RIFF") and header[4:8] == b"WEBP":
                        ext = ".webp"
                    else:
                        ext = ".jpg"  # 默认使用jpg
            except:
                ext = ".jpg"
        
        new_name = f"page_{i:03d}{ext}"
        shutil.copy(img_path, img_dir / new_name)
    
    # 创建CBZ文件
    cbz_path = output_dir / f"{base_name}.cbz"
    with zipfile.ZipFile(cbz_path, 'w') as cbz_file:
        for img_file in img_dir.glob('*'):
            cbz_file.write(img_file, img_file.name)
    
    return cbz_path, img_dir

def process_epub(epub_file, output_dir):
    """处理单个EPUB文件"""
    print(f"\nProcessing: {epub_file.name}")
    epub_stem = epub_file.stem
    
    try:
        # 创建临时解压目录（使用唯一名称）
        temp_dir = output_dir / "temp" / f"temp_{epub_stem}"
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 解压EPUB文件
        with zipfile.ZipFile(epub_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 定位并解析OPF文件
        opf_path = find_opf_file(Path(temp_dir))
        manifest, spine = parse_opf(opf_path)
        
        # 提取图片
        image_files = extract_images(Path(temp_dir), opf_path, manifest, spine)
        print(f"  Found {len(image_files)} images")
        
        if not image_files:
            print("  No images found, skipping...")
            return
        
        # 使用原始EPUB文件名作为基础名称
        base_name = epub_stem
        
        # 创建CBZ和图片文件夹
        cbz_path, img_dir = create_cbz(
            image_files, output_dir, base_name
        )
        
        print(f"  Created CBZ: {cbz_path.name}")
        print(f"  Image folder: {img_dir.name}")
    
    except Exception as e:
        print(f"  Error processing {epub_file.name}: {str(e)}")
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    # 准备输出目录
    output_path = Path(OUTPUT_DIR)
    os.makedirs(output_path, exist_ok=True)
    
    # 处理当前目录所有EPUB文件
    epubs = list(Path('.').glob('*.epub'))
    if not epubs:
        print("No EPUB files found in current directory")
        return
    
    print(f"Found {len(epubs)} EPUB file(s)")
    for epub in epubs:
        process_epub(epub, output_path)
    
    print("\nProcessing completed!")
    print(f"Output directory: {output_path.resolve()}")

if __name__ == "__main__":
    main()