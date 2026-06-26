import os
import re

blog_dir = "/root/projects/stock-research-blog/src/content/blog"
profit_pattern = re.compile(r'(获利盘|获利比例)[:：]?\s*([0-9.]+%?)')
cost_pattern = re.compile(r'(平均成本)[:：]?\s*([0-9.]+)(?:元)?')

def apply_styles(content):
    # This naive regex replace might break markdown if not careful, 
    # but since it's just plain text we are targeting it should be okay.
    # We will replace it safely only in paragraphs and list items.
    
    lines = content.split('\n')
    new_lines = []
    
    in_code_block = False
    for line in lines:
        if line.startswith('```'):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
            
        if not in_code_block:
            # Add span around profit values
            line = re.sub(r'(获利盘|获利比例)([:：]?\s*)([0-9.]+%?)', 
                          r'\1\2<span class="profit-ratio">\3</span>', 
                          line)
            
            # Add span around cost values
            line = re.sub(r'(平均成本)([:：]?\s*)([0-9.]+)(元)?', 
                          r'\1\2<span class="avg-cost">\3\4</span>', 
                          line)
                          
        new_lines.append(line)
        
    return '\n'.join(new_lines)


for filename in os.listdir(blog_dir):
    if not filename.endswith('.md'): continue
    
    filepath = os.path.join(blog_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = apply_styles(content)
    
    if new_content != content:
        print(f"Updated styles in: {filename}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
