from typing import List
from common_modules.engines.base_engine import BaseEngineProcessor
import os

class TemplateEngineProcessor(BaseEngineProcessor):
    """Template engine processor to implement for any new engine.

    Implements:
    - preprocess(engine_input_folder, text_to_translate_folder) -> List[str]
      Convert engine-specific raw input files into canonical block-format files placed into text_to_translate_folder.

    - postprocess(text_to_translate_folder, translate_output_folder) -> List[str]
      Apply translated canonical-format outputs back to engine-specific files (write outputs and return produced file paths).
    """
    
    @property
    def needs_preprocess(self) -> bool:
        return True

    def preprocess(self, engine_input_folder: str, text_to_translate_folder: str) -> List[str]:
        os.makedirs(text_to_translate_folder, exist_ok=True)
        # Example: copy all .txt files as-is (implementers must replace with real logic)
        created = []
        for fname in os.listdir(engine_input_folder):
            if not fname.endswith('.txt'):
                continue
            src = os.path.join(engine_input_folder, fname)
            dst = os.path.join(text_to_translate_folder, fname)
            with open(src, 'r', encoding='utf-8') as r, open(dst, 'w', encoding='utf-8') as w:
                w.write(r.read())
            created.append(dst)
        return created

    def postprocess(self, text_to_translate_folder: str, translate_output_folder: str) -> List[str]:
        # Default demo: merge translated files into a single output
        outputs = []
        merged = os.path.join(translate_output_folder, 'merged_translated.txt')
        if os.path.exists(merged):
            out_path = os.path.join('worker', 'template_final.txt')
            os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
            with open(merged, 'r', encoding='utf-8') as r, open(out_path, 'w', encoding='utf-8') as w:
                w.write(r.read())
            outputs.append(out_path)
        return outputs
