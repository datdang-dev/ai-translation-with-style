import re

"""
@brief BlockManager: Quản lý các thao tác với block text (extract, check missing, insert).
"""
class BlockManager:
    def __init__(self):
        pass

    def extract_blocks(self, text):
        blocks = []
        current_block = []
        for line in text.splitlines():
            if re.match(r'^\s*---------\d+\s*$', line):
                if current_block and any(l.strip() != '' for l in current_block):
                    # Chuẩn hóa loại bỏ dòng trắng cuối block
                    while current_block and current_block[-1].strip() == '':
                        current_block.pop()
                    blocks.append("\n".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        if current_block and any(l.strip() != '' for l in current_block):
            while current_block and current_block[-1].strip() == '':
                current_block.pop()
            blocks.append("\n".join(current_block))
        return blocks

    def find_missing_indices(self, input_blocks, output_blocks):
        missing_indices = []
        for idx in range(len(input_blocks)):
            if idx >= len(output_blocks):
                missing_indices.append(idx)
        return missing_indices

    def insert_blocks(self, output_blocks, missing_indices, translated_blocks):
        for i, idx in enumerate(missing_indices):
            if i < len(translated_blocks):
                block = translated_blocks[i].rstrip('\n')
                output_blocks.insert(idx, block)
        return output_blocks
