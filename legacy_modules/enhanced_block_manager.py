import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BlockInfo:
    """Thông tin chi tiết về một block"""
    id: str
    content: str
    original_index: int
    line_number: int

class EnhancedBlockManager:
    """
    Enhanced BlockManager với khả năng handle các trường hợp error:
    - Block ID không unique
    - AI trả về thiếu block
    - AI trả về sai thứ tự block
    - AI trả về block ID không match
    """
    
    def __init__(self):
        self.logger = None
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def extract_blocks_with_info(self, text: str) -> List[BlockInfo]:
        """
        Extract blocks với thông tin chi tiết bao gồm ID, content, index gốc
        """
        blocks = []
        current_block = []
        current_block_id = None
        current_line_number = 0
        
        for line_num, line in enumerate(text.splitlines(), 1):
            match = re.match(r'^\s*---------\d+\s*$', line.strip())
            if match:
                # Lưu block trước đó nếu có
                if current_block and current_block_id:
                    content = "\n".join(current_block).strip()
                    if content:
                        blocks.append(BlockInfo(
                            id=current_block_id,
                            content=content,
                            original_index=len(blocks),
                            line_number=current_line_number
                        ))
                
                # Bắt đầu block mới
                current_block_id = match.group(0).strip()
                current_block = [line]
                current_line_number = line_num
            else:
                current_block.append(line)
        
        # Lưu block cuối cùng
        if current_block and current_block_id:
            content = "\n".join(current_block).strip()
            if content:
                blocks.append(BlockInfo(
                    id=current_block_id,
                    content=content,
                    original_index=len(blocks),
                    line_number=current_line_number
                ))
        
        return blocks
    
    def extract_blocks(self, text: str) -> List[str]:
        """Backward compatibility với interface cũ"""
        blocks_info = self.extract_blocks_with_info(text)
        return [block.content for block in blocks_info]
    
    def find_duplicate_block_ids(self, blocks_info: List[BlockInfo]) -> Dict[str, List[int]]:
        """Tìm các block ID bị duplicate"""
        id_count = {}
        for i, block in enumerate(blocks_info):
            if block.id not in id_count:
                id_count[block.id] = []
            id_count[block.id].append(i)
        
        return {block_id: indices for block_id, indices in id_count.items() if len(indices) > 1}
    
    def validate_block_consistency(self, input_blocks_info: List[BlockInfo], 
                                 output_blocks_info: List[BlockInfo]) -> Dict[str, any]:
        """
        Validate tính nhất quán giữa input và output blocks
        Returns: Dict chứa các thông tin validation
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_blocks': [],
            'duplicate_input_ids': [],
            'duplicate_output_ids': [],
            'mismatched_ids': []
        }
        
        # Check duplicate IDs trong input
        input_duplicates = self.find_duplicate_block_ids(input_blocks_info)
        if input_duplicates:
            result['duplicate_input_ids'] = list(input_duplicates.keys())
            result['warnings'].append(f"Input có duplicate block IDs: {list(input_duplicates.keys())}")
        
        # Check duplicate IDs trong output
        output_duplicates = self.find_duplicate_block_ids(output_blocks_info)
        if output_duplicates:
            result['duplicate_output_ids'] = list(output_duplicates.keys())
            result['warnings'].append(f"Output có duplicate block IDs: {list(output_duplicates.keys())}")
        
        # Check missing blocks
        input_ids = {block.id for block in input_blocks_info}
        output_ids = {block.id for block in output_blocks_info}
        missing_ids = input_ids - output_ids
        if missing_ids:
            result['missing_blocks'] = list(missing_ids)
            result['errors'].append(f"Thiếu blocks: {list(missing_ids)}")
            result['is_valid'] = False
        
        # Check mismatched IDs (output có ID không có trong input)
        extra_ids = output_ids - input_ids
        if extra_ids:
            result['mismatched_ids'] = list(extra_ids)
            result['warnings'].append(f"Output có block IDs không có trong input: {list(extra_ids)}")
        
        return result
    
    def find_missing_indices(self, input_blocks: List[str], output_blocks: List[str]) -> List[int]:
        """Backward compatibility - tìm missing indices theo thứ tự"""
        missing_indices = []
        for idx in range(len(input_blocks)):
            if idx >= len(output_blocks):
                missing_indices.append(idx)
        return missing_indices
    
    def find_missing_blocks_by_id(self, input_blocks_info: List[BlockInfo], 
                                output_blocks_info: List[BlockInfo]) -> List[BlockInfo]:
        """Tìm các block bị thiếu dựa trên ID"""
        input_ids = {block.id: block for block in input_blocks_info}
        output_ids = {block.id for block in output_blocks_info}
        
        missing_blocks = []
        for block_id, block_info in input_ids.items():
            if block_id not in output_ids:
                missing_blocks.append(block_info)
        
        return missing_blocks
    
    def insert_blocks(self, output_blocks: List[str], missing_indices: List[int], 
                     translated_blocks: List[str]) -> List[str]:
        """Backward compatibility - insert blocks theo index"""
        for i, idx in enumerate(missing_indices):
            if i < len(translated_blocks):
                block = translated_blocks[i].rstrip('\n')
                output_blocks.insert(idx, block)
        return output_blocks
    
    def insert_missing_blocks_by_id(self, output_blocks_info: List[BlockInfo], 
                                  missing_blocks_info: List[BlockInfo]) -> List[BlockInfo]:
        """Insert missing blocks dựa trên ID và vị trí gốc"""
        # Tạo map từ ID đến vị trí gốc
        id_to_original_index = {block.id: block.original_index for block in output_blocks_info}
        
        # Thêm missing blocks vào map
        for block in missing_blocks_info:
            id_to_original_index[block.id] = block.original_index
        
        # Sắp xếp lại theo original_index
        all_blocks = output_blocks_info + missing_blocks_info
        all_blocks.sort(key=lambda x: id_to_original_index[x.id])
        
        return all_blocks
    
    def fix_translation_output(self, input_text: str, output_text: str) -> Tuple[str, Dict[str, any]]:
        """
        Fix translation output khi có lỗi
        Returns: (fixed_output, validation_info)
        """
        input_blocks_info = self.extract_blocks_with_info(input_text)
        output_blocks_info = self.extract_blocks_with_info(output_text)
        
        validation = self.validate_block_consistency(input_blocks_info, output_blocks_info)
        
        if validation['is_valid'] and not validation['warnings']:
            return output_text, validation
        
        self._log('warning', f"Translation output có vấn đề: {validation}")
        
        # Nếu có missing blocks, thử fix
        if validation['missing_blocks']:
            missing_blocks_info = self.find_missing_blocks_by_id(input_blocks_info, output_blocks_info)
            
            if missing_blocks_info:
                self._log('info', f"Tìm thấy {len(missing_blocks_info)} missing blocks, đang fix...")
                
                # Tạo text cho missing blocks để translate lại
                missing_text = "\n\n".join([block.content for block in missing_blocks_info])
                
                # Insert missing blocks vào output
                fixed_blocks_info = self.insert_missing_blocks_by_id(output_blocks_info, missing_blocks_info)
                
                # Tạo output text mới
                fixed_output = self._blocks_info_to_text(fixed_blocks_info)
                
                validation['fixed'] = True
                validation['missing_blocks_fixed'] = [block.id for block in missing_blocks_info]
                
                return fixed_output, validation
        
        return output_text, validation
    
    def _blocks_info_to_text(self, blocks_info: List[BlockInfo]) -> str:
        """Convert blocks info về text"""
        lines = []
        for block in blocks_info:
            lines.append(block.content)
        return "\n".join(lines)
    
    def create_robust_translation_prompt(self, input_text: str) -> str:
        """
        Tạo prompt robust hơn để tránh AI trả về sai
        """
        blocks_info = self.extract_blocks_with_info(input_text)
        
        # Check duplicate IDs
        duplicates = self.find_duplicate_block_ids(blocks_info)
        if duplicates:
            self._log('warning', f"Input có duplicate block IDs: {list(duplicates.keys())}")
        
        # Tạo prompt với warning về duplicate
        prompt = "IMPORTANT: The following text contains blocks with duplicate IDs. "
        prompt += "Please ensure you translate ALL blocks and maintain the exact block structure.\n\n"
        prompt += input_text
        
        return prompt
