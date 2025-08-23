import re
import os
from typing import List, Tuple
from common_modules.logger import Logger
from common_modules.engines.base_engine import BaseEngineProcessor
from common_modules.apply_translation import TranslationApplier
from common_modules.text_chunker import TextChunker


class RenPyProcessor(BaseEngineProcessor):
    """
    Module xử lý file RenPy (.rpy) để trích xuất text cần dịch và tạo tag mapping
    """
    
    def __init__(self, logger: Logger = None):
        super().__init__(logger or Logger("renpy_processor").get_logger())

    @property
    def needs_preprocess(self) -> bool:
        return True
    
    def process_rpy_file(self, input_file: str, output_txt: str = None, output_rpy_with_tags: str = None) -> Tuple[str, str]:
        """
        Xử lý file .rpy để trích xuất text và tạo tag mapping
        
        Args:
            input_file: Đường dẫn file .rpy input
            output_txt: Đường dẫn file .txt output (nếu None sẽ tự tạo)
            output_rpy_with_tags: Đường dẫn file .rpy với tag output (nếu None sẽ tự tạo)
            
        Returns:
            Tuple[str, str]: (đường dẫn file txt, đường dẫn file rpy với tag)
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Tạo tên file output nếu không được cung cấp
        if output_txt is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_txt = f"work_space/renpy/text_to_translate/{base_name}_extracted.txt"
        
        if output_rpy_with_tags is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_rpy_with_tags = f"work_space/renpy/text_to_translate/{base_name}_with_tags.rpy"
        
        # Đảm bảo thư mục output tồn tại
        os.makedirs(os.path.dirname(output_txt), exist_ok=True)
        os.makedirs(os.path.dirname(output_rpy_with_tags), exist_ok=True)
        
        self.logger.info(f"Processing RenPy file: {input_file}")
        
        lines_out: list[str] = []
        counter = 0
        new_lines: list[str] = []
        current_comment_text: str | None = None
        current_old_text: str | None = None

        # Quét một lượt, hỗ trợ đồng thời cả hai dạng old/new và comment/empty
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                # 1) Nhận diện nguồn từ old "..." (đuôi sẽ chờ dòng new tương ứng)
                m_old = re.match(r'^\s*old\s+"(.*?)"\s*$', line)
                if m_old:
                    current_old_text = m_old.group(1)
                    new_lines.append(line)
                    continue

                # 2) Nhận diện nguồn từ comment: # "..." hoặc # name "..."
                m_cmt = re.match(r'^\s*#\s*(?:\w+\s*)?"(.*?)"\s*$', line)
                if m_cmt and not line.strip().startswith("# game/"):
                    current_comment_text = m_cmt.group(1)
                    new_lines.append(line)
                    continue

                # 3) new "..." NON-EMPTY → bỏ qua pending old
                m_new_nonempty = re.match(r'^\s*new\s+"(.+?)"\s*$', line)
                if m_new_nonempty and m_new_nonempty.group(1) != "":
                    current_old_text = None
                    new_lines.append(line)
                    continue

                # 4) Dòng nhân vật NON-EMPTY (không phải comment) → bỏ qua pending comment
                m_dialog_nonempty = re.match(r'^\s*(?:\w+\s*)?"(.+?)"\s*$', line)
                if m_dialog_nonempty and m_dialog_nonempty.group(1) != "" and not line.lstrip().startswith("#"):
                    current_comment_text = None
                    new_lines.append(line)
                    continue

                # 5) Khi gặp dòng dịch rỗng thì gắn tag với nguồn phù hợp
                m_new_empty = re.match(r'^(\s*new\s+)""\s*$', line)
                if m_new_empty:
                    prefix = m_new_empty.group(1)
                    text_for_block = current_old_text if current_old_text is not None else (current_comment_text or "")
                    lines_out.append(f"---------{counter}\n{text_for_block}")
                    new_lines.append(f'{prefix}"---------{counter}"\n')
                    counter += 1
                    current_old_text = None
                    current_comment_text = None
                    continue

                m_empty_any = re.match(r'^(\s*(?:\w+\s*)?)""\s*$', line)
                if m_empty_any:
                    prefix = m_empty_any.group(1) if m_empty_any else ""
                    text_for_block = current_comment_text or ""
                    lines_out.append(f"---------{counter}\n{text_for_block}")
                    new_lines.append(f'{prefix}"---------{counter}"\n')
                    counter += 1
                    current_comment_text = None
                    continue

                # 6) Mặc định: giữ nguyên
                new_lines.append(line)
        
        # Ghi file text để dịch
        extracted_blocks = lines_out[:counter] if len(lines_out) > counter else lines_out
        content_to_write = ("\n".join(extracted_blocks)).rstrip("\n") + "\n"
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(content_to_write)
        
        # Ghi file rpy với tag
        with open(output_rpy_with_tags, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        if len(lines_out) != counter:
            self.logger.warning(
                f"Alignment notice: extracted={len(lines_out)} vs tagged={counter}. "
                f"Using first {min(len(lines_out), counter)} blocks to keep alignment."
            )
        self.logger.info(f"✅ Extracted {min(len(lines_out), counter)} lines → {output_txt}")
        self.logger.info(f"✅ File với tag block_number: {output_rpy_with_tags}")
        
        return output_txt, output_rpy_with_tags
    
    def preprocess(self, engine_input_folder: str, text_to_translate_folder: str) -> List[str]:
        if not os.path.exists(engine_input_folder):
            self.logger.warning(f"Input folder not found: {engine_input_folder}")
            return []
        os.makedirs(text_to_translate_folder, exist_ok=True)
        rpy_files = [f for f in os.listdir(engine_input_folder) if f.endswith('.rpy')]
        if not rpy_files:
            self.logger.warning(f"No .rpy files found in {engine_input_folder}")
            return []

        processed_text_files: List[str] = []
        for rpy_file in rpy_files:
            rpy_path = os.path.join(engine_input_folder, rpy_file)
            try:
                txt_file, _ = self.process_rpy_file(rpy_path)
                processed_text_files.append(txt_file)
                self.logger.info(f"✅ Processed {rpy_file}")
            except Exception as e:
                self.logger.error(f"Failed to process {rpy_file}: {e}")
                continue
        return processed_text_files

    def postprocess(self, text_to_translate_folder: str, translate_output_folder: str) -> List[str]:
        """
        Apply translated canonical files back into RenPy outputs.

        - Attempts to use merged_translated.txt; if not present, tries to merge parts.
        - Applies translations to the first `_with_tags.rpy` file found in `text_to_translate_folder`.
        - Returns list of produced output paths.
        """
        outputs: List[str] = []
        # Ensure merged file exists
        merged_path = os.path.join(translate_output_folder, 'merged_translated.txt')
        if not os.path.exists(merged_path):
            try:
                merged_path = TextChunker.merge_translated_files(translate_output_folder)
            except Exception as e:
                self.logger.warning(f"Could not find or merge translated files: {e}")
                return outputs

        rpy_candidates = [f for f in os.listdir(text_to_translate_folder) if f.endswith('_with_tags.rpy')]
        if not rpy_candidates:
            self.logger.info("No RPY with tags found to apply translations. Skipping RenPy postprocess.")
            return outputs

        rpy_with_tags = os.path.join(text_to_translate_folder, rpy_candidates[0])
        applier = TranslationApplier(self.logger)
        try:
            applier.load_translations(merged_path)
            out_rpy = os.path.join('worker', 'final_translated.rpy')
            applier.apply_to_rpy(rpy_with_tags, out_rpy)
            outputs.append(out_rpy)
            self.logger.info(f"✅ Applied translations to RPY: {out_rpy}")
        except Exception as e:
            self.logger.error(f"Failed to apply translations to RPY: {e}")

        return outputs
