"""
@brief TranslationProcessor: Xử lý quy trình dịch và kiểm tra output.
"""
class TranslationProcessor:
    def __init__(self, translator_service, block_manager, logger):
        self.translator_service = translator_service
        self.block_manager = block_manager
        self.logger = logger

    def process_file(self, input_text, output_path, max_retry=3):
        input_blocks = self.block_manager.extract_blocks(input_text)
        num_input_blocks = len(input_blocks)
        retry_count = 0
        while True:
            translated = self.translator_service.translate_text(input_text)
            # Chuẩn hóa dòng: loại bỏ extra spaces 2 bên và dòng trống thừa
            normalized_first = "\n".join(l.strip() for l in translated.splitlines() if l.strip())
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(normalized_first + ("\n" if not normalized_first.endswith("\n") else ""))
            self.logger.info(f"🔍 Checking output: empty file, block count...")
            with open(output_path, "r", encoding="utf-8") as f:
                output_content = f.read().strip()
                output_blocks = self.block_manager.extract_blocks(output_content)
            num_output_blocks = len(output_blocks)
            self.logger.info(f"[BLOCKS] input_blocks={num_input_blocks}, output_blocks={num_output_blocks}")
            if num_output_blocks == num_input_blocks:
                self.logger.info(f"✅ Done: {output_path}")
                break
            elif num_output_blocks < num_input_blocks:
                missing_indices = self.block_manager.find_missing_indices(input_blocks, output_blocks)
                if missing_indices:
                    self.logger.warning(f"Output is missing blocks at indices: {missing_indices}. Re-translating all in one request...")
                    # Ghép các block bị thiếu bằng một newline để tránh sinh dòng trống
                    missing_blocks_text = "\n".join([input_blocks[idx] for idx in missing_indices])
                    translated_blocks = self.translator_service.translate_text(missing_blocks_text)
                    translated_blocks_list = self.block_manager.extract_blocks(translated_blocks)
                    output_blocks = self.block_manager.insert_blocks(output_blocks, missing_indices, translated_blocks_list)
                    # Chuẩn hóa ghi file: nối bằng một newline, không để trống giữa các block, có newline cuối file
                    normalized = ("\n".join(b.strip() for b in output_blocks)).rstrip("\n") + "\n"
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(normalized)
                    self.logger.info(f"🔍 Re-checking output after appending missing blocks...")
                    with open(output_path, "r", encoding="utf-8") as f:
                        output_content = f.read().strip()
                        output_blocks = self.block_manager.extract_blocks(output_content)
                    num_output_blocks = len(output_blocks)
                    self.logger.info(f"[BLOCKS] input_blocks={num_input_blocks}, output_blocks={num_output_blocks}")
                    if num_output_blocks == num_input_blocks:
                        self.logger.info(f"✅ Done: {output_path}")
                        break
                    else:
                        retry_count += 1
                        self.logger.warning(f"Still missing blocks after re-translation. Retrying (attempt {retry_count})...")
                        if retry_count >= max_retry:
                            self.logger.error(f"Failed to get valid translation for {output_path} after {max_retry} attempts.")
                            break
            else:
                retry_count += 1
                self.logger.warning(f"Block count mismatch: input={num_input_blocks}, output={num_output_blocks}. Retrying (attempt {retry_count})...")
                self.logger.info(f"[BLOCKS] input_blocks={num_input_blocks}, output_blocks={num_output_blocks}")
                if retry_count >= max_retry:
                    self.logger.error(f"Failed to get valid translation for {output_path} after {max_retry} attempts.")
                    break
