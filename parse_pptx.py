import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def extract_text_from_pptx(pptx_path):
    if not os.path.exists(pptx_path):
        print(f"File not found: {pptx_path}")
        return
        
    try:
        with zipfile.ZipFile(pptx_path, 'r') as archive:
            # Find all slides
            slide_files = [f for f in archive.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            import re
            def get_slide_num(f):
                match = re.search(r'slide(\d+)\.xml$', f)
                return int(match.group(1)) if match else 0
            
            # Sort them by slide number
            slide_files.sort(key=get_slide_num)
            
            for slide_idx, slide_file in enumerate(slide_files, 1):
                print(f"--- Slide {slide_idx} ---")
                xml_content = archive.read(slide_file)
                tree = ET.fromstring(xml_content)
                # Find all text elements. The namespace for drawing is usually 'http://schemas.openxmlformats.org/drawingml/2006/main'
                # but we can just use a simple regex or findall with a wildcard namespace to be safe.
                texts = []
                for node in tree.iter():
                    if node.tag.endswith('}t'):
                        if node.text:
                            texts.append(node.text)
                if texts:
                    print('\n'.join(texts))
                else:
                    print("(No text)")
                print("")
    except Exception as e:
        print(f"Error parsing pptx: {e}")

if __name__ == '__main__':
    extract_text_from_pptx(sys.argv[1])
