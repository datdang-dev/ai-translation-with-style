#!/usr/bin/env python3
"""
Module apply_translation: áp dụng bản dịch (format chuẩn ---------<block_number>)
 vào file .rpy có tag "---------<block_number>".
"""
import re
import os
from typing import Dict

class TranslationApplier:
    def __init__(self, logger=None):
        self.logger = logger
        self.translations: Dict[str, str] = {}

    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")

    def load_translations(self, translation_file: str) -> Dict[str, str]:
        if not os.path.exists(translation_file):
            raise FileNotFoundError(f"Translation file not found: {translation_file}")
        self._log('info', f"Loading translations from: {translation_file}")

        translations: Dict[str, str] = {}
        current_index = None
        current_text_lines = []

        with open(translation_file, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.rstrip('\n')
                m = re.match(r'^-{9,11}(\d+)$', line.strip())
                if m:
                    if current_index is not None and current_text_lines:
                        translations[current_index] = "\n".join(current_text_lines).strip()
                    current_index = m.group(1)
                    current_text_lines = []
                elif current_index is not None:
                    current_text_lines.append(line)
        if current_index is not None and current_text_lines:
            translations[current_index] = "\n".join(current_text_lines).strip()

        self.translations = translations
        self._log('info', f"Loaded {len(translations)} translations")
        return translations

    def apply_to_rpy(self, rpy_with_tags_file: str, output_file: str) -> str:
        if not os.path.exists(rpy_with_tags_file):
            raise FileNotFoundError(f"RPY file not found: {rpy_with_tags_file}")
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        applied = 0
        out_lines = []
        with open(rpy_with_tags_file, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'(\s*(?:\w+\s*)?)"---------(\d+)"', line)
                if m:
                    prefix, idx = m.group(1), m.group(2)
                    if idx in self.translations:
                        txt = self.translations[idx].replace('"', '\\"')
                        out_lines.append(f'{prefix}"{txt}"\n')
                        applied += 1
                    else:
                        out_lines.append(line)
                else:
                    out_lines.append(line)
        with open(output_file, 'w', encoding='utf-8') as out:
            out.writelines(out_lines)
        self._log('info', f"Applied {applied} translations → {output_file}")
        return output_file
