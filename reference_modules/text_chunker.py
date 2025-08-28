import os
import re
from typing import List
from transformers import AutoTokenizer

class TextChunker:
    def __init__(self, input_file: str, output_dir: str, max_tokens: int = 12000, model_name: str = "tngtech/DeepSeek-TNG-R1T2-Chimera", logger=None):
        self.input_file = input_file
        self.output_dir = output_dir
        self.max_tokens = max_tokens
        self.model_name = model_name
        self.logger = logger
        os.makedirs(self.output_dir, exist_ok=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def split_file(self) -> None:
        if self.logger:
            self.logger.info(f"Reading input file: {self.input_file}")
        with open(self.input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        blocks: List[str] = []
        current: List[str] = []
        for line in lines:
            if line.strip().startswith("---------") and current:
                blocks.append("".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append("".join(current))

        file_idx = 1
        cur_tokens = 0
        cur_content: List[str] = []

        for block in blocks:
            block_tokens = len(self.tokenizer.encode(block))
            if cur_tokens + block_tokens > self.max_tokens:
                out_path = os.path.join(self.output_dir, f"part_{file_idx}.txt")
                with open(out_path, "w", encoding="utf-8") as out:
                    out.write("".join(cur_content))
                if self.logger:
                    self.logger.info(f"→ Saved part_{file_idx}.txt ({cur_tokens} tokens)")
                file_idx += 1
                cur_tokens = 0
                cur_content = []
            cur_content.append(block)
            cur_tokens += block_tokens

        if cur_content:
            out_path = os.path.join(self.output_dir, f"part_{file_idx}.txt")
            with open(out_path, "w", encoding="utf-8") as out:
                out.write("".join(cur_content))
            if self.logger:
                self.logger.info(f"→ Saved part_{file_idx}.txt ({cur_tokens} tokens)")

        if self.logger:
            self.logger.info("Done splitting files with correct tokenizer 👍")

    @staticmethod
    def merge_translated_files(translated_folder: str, output_filename: str = "merged_translated.txt") -> str:
        if not os.path.isdir(translated_folder):
            raise FileNotFoundError(f"Translated folder not found: {translated_folder}")
        files = [f for f in os.listdir(translated_folder) if f.endswith('.txt')]
        def part_key(x: str):
            m = re.search(r"part_(\d+)\.txt$", x)
            return (0, int(m.group(1))) if m else (1, x)
        files = sorted(files, key=part_key)
        merged_content = ""
        for fname in files:
            path = os.path.join(translated_folder, fname)
            with open(path, "r", encoding="utf-8") as f:
                merged_content += f.read()
                if not merged_content.endswith("\n"):
                    merged_content += "\n"
        out_path = os.path.join(translated_folder, output_filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(merged_content)
        return out_path
