import re
import os
from typing import List, Tuple
from common_modules.logger import Logger
from common_modules.engines.base_engine import BaseEngineProcessor


class WebVTTProcessor(BaseEngineProcessor):
    """
    Module xử lý file WebVTT Transcript để trích xuất text cần dịch
    """
    
    def __init__(self, logger: Logger = None):
        super().__init__(logger or Logger("webvtt_processor").get_logger())

    @property
    def needs_preprocess(self) -> bool:
        return True
    
    def parse_webvtt_file(self, input_file: str) -> List[Tuple[str, str, str]]:
        """
        Parse file WebVTT để trích xuất các block text với timestamp
        
        Args:
            input_file: Đường dẫn file WebVTT input
            
        Returns:
            List[Tuple[str, str, str]]: List các tuple (index, timestamp, text)
        """
        blocks = []
        current_index = None
        current_timestamp = None
        current_text = ""
        
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Bỏ qua header WEBVTT và dòng trống
            if line == "WEBVTT" or line == "":
                i += 1
                continue
            
            # Parse index
            if line.isdigit():
                current_index = line
                i += 1
                continue
            
            # Parse timestamp
            if " --> " in line:
                current_timestamp = line
                i += 1
                continue
            
            # Parse text content
            if current_index and current_timestamp:
                current_text = ""
                while i < len(lines) and lines[i].strip() != "":
                    current_text += lines[i].strip() + " "
                    i += 1
                
                # Clean up text
                current_text = current_text.strip()
                if current_text:
                    blocks.append((current_index, current_timestamp, current_text))
                
                # Reset for next block
                current_index = None
                current_timestamp = None
                current_text = ""
            else:
                i += 1
        
        return blocks
    
    def process_transcript_file(self, input_file: str, output_txt: str = None) -> str:
        """
        Xử lý file transcript để trích xuất text và tạo format chuẩn cho translation
        
        Args:
            input_file: Đường dẫn file transcript input
            output_txt: Đường dẫn file .txt output (nếu None sẽ tự tạo)
            
        Returns:
            str: Đường dẫn file txt đã tạo
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Tạo tên file output nếu không được cung cấp
        if output_txt is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_txt = f"work_space/webvtt/text_to_translate/{base_name}_extracted.txt"
        
        # Đảm bảo thư mục output tồn tại
        os.makedirs(os.path.dirname(output_txt), exist_ok=True)
        
        self.logger.info(f"Processing WebVTT transcript file: {input_file}")
        
        # Parse WebVTT file
        blocks = self.parse_webvtt_file(input_file)
        
        # Tạo content theo format chuẩn "---------<block_number>"
        lines_out = []
        for i, (index, timestamp, text) in enumerate(blocks):
            # Thêm comment với timestamp để reference
            lines_out.append(f"# {timestamp}")
            lines_out.append(f"---------{i}")
            lines_out.append(text)
            lines_out.append("")  # Dòng trống giữa các block
        
        # Ghi file text để dịch
        content_to_write = "\n".join(lines_out).rstrip("\n") + "\n"
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(content_to_write)
        
        self.logger.info(f"✅ Extracted {len(blocks)} blocks → {output_txt}")
        
        return output_txt
    
    def preprocess(self, engine_input_folder: str, text_to_translate_folder: str) -> List[str]:
        """
        Tiền xử lý tất cả file transcript trong thư mục input
        
        Args:
            engine_input_folder: Thư mục chứa file transcript input
            text_to_translate_folder: Thư mục output cho file text cần dịch
            
        Returns:
            List[str]: Danh sách đường dẫn file .txt đã tạo
        """
        if not os.path.exists(engine_input_folder):
            self.logger.warning(f"Input folder not found: {engine_input_folder}")
            return []
        
        os.makedirs(text_to_translate_folder, exist_ok=True)
        
        # Tìm tất cả file transcript (có thể là .txt, .vtt, .srt)
        transcript_extensions = ['.txt', '.vtt', '.srt']
        transcript_files = []
        for ext in transcript_extensions:
            transcript_files.extend([f for f in os.listdir(engine_input_folder) if f.endswith(ext)])
        
        if not transcript_files:
            self.logger.warning(f"No transcript files found in {engine_input_folder}")
            return []

        processed_text_files: List[str] = []
        for transcript_file in transcript_files:
            transcript_path = os.path.join(engine_input_folder, transcript_file)
            try:
                txt_file = self.process_transcript_file(transcript_path)
                processed_text_files.append(txt_file)
                self.logger.info(f"✅ Processed {transcript_file}")
            except Exception as e:
                self.logger.error(f"Failed to process {transcript_file}: {e}")
                continue
        
        return processed_text_files
