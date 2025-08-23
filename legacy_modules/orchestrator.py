import os
import re
import json
import importlib.util
from typing import List
from .logger import Logger
from .file_manager import FileManager
from .token_counter import TokenCounter
from .api_key_manager import APIKeyManager
from .api_client import OpenRouterClient
from .translator_service import TranslatorService
from .text_chunker import TextChunker
# Legacy processors removed: enhanced pipeline is the only supported runtime path.
from .apply_translation import TranslationApplier

# Import enhanced components
from common_modules.master_translation_processor import MasterTranslationProcessor

class Orchestrator:
    def __init__(self, config_path: str, api_url: str, preset_file: str, prefix: str, logger: Logger):
        self.config_path = config_path
        self.api_url = api_url
        self.preset_file = preset_file
        self.prefix = prefix
        self.logger = logger
        # Engine processor instance (loaded dynamically if configured)
        self.engine_processor = None
        try:
            self.engine_processor = self._load_engine_processor()
            if self.engine_processor:
                self.logger.info(f"🔌 Loaded engine processor: {self.engine_processor.__class__.__name__}")
        except Exception as e:
            # Non-fatal: keep going, preprocess/postprocess will handle missing engine
            self.logger.warning(f"⚠️ Could not load engine processor at init: {e}")

    def _load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def preprocess(self) -> List[str]:
        cfg = self._load_config()
        engine_input_folder = cfg["engine_input_folder"]
        text_to_translate_folder = cfg["text_to_translate_folder"]
        needs_preprocess = cfg.get("needs_preprocess", True)

        for path in [engine_input_folder, text_to_translate_folder]:
            os.makedirs(path, exist_ok=True)

        if not needs_preprocess:
            self.logger.info("Engine doesn't need preprocess. Skipping...")
            return []

        # If engine was loaded at init, reuse it; otherwise attempt to load now
        if not self.engine_processor:
            try:
                self.engine_processor = self._load_engine_processor()
                self.logger.info(f"🔌 Dynamically loaded engine processor: {self.engine_processor.__class__.__name__}")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to load engine processor for preprocess: {e}")
                return []

        return self.engine_processor.preprocess(engine_input_folder, text_to_translate_folder)

    def _load_engine_processor(self):
        """Dynamically load the engine processor specified in config.

        Returns instance of engine processor or None if not configured/fails.
        """
        cfg = self._load_config()
        engine_processor_file = cfg.get("engine_processor_file")
        engine_processor_class = cfg.get("engine_processor_class")
        if not engine_processor_file or not engine_processor_class:
            return None

        if not os.path.exists(engine_processor_file):
            # Not present in workspace
            raise FileNotFoundError(f"Engine processor file not found: {engine_processor_file}")

        spec = importlib.util.spec_from_file_location("engine_processor_module", engine_processor_file)
        engine_module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(engine_module)
        EngineProcessor = getattr(engine_module, engine_processor_class)
        return EngineProcessor(self.logger)

    def translate(self, api_keys: list):
        cfg = self._load_config()
        text_to_translate_folder = cfg["text_to_translate_folder"]
        split_output_folder = cfg["split_output_folder"]
        translate_input_folder = cfg["translate_input_folder"]
        translate_output_folder = cfg["translate_output_folder"]
        resume_from_last = cfg.get("resume_from_last", False)

        for path in [split_output_folder, translate_input_folder, translate_output_folder]:
            os.makedirs(path, exist_ok=True)

        with open(self.preset_file, 'r', encoding='utf-8') as f:
            preset_data = json.load(f)
        model_name = preset_data.get('model')
        # Determine tokenizer name and chunk size from preset/app config
        tokenizer_name = preset_data.get('tokenizer_name') or cfg.get('tokenizer_name') or 'gpt2'
        max_tokens_per_chunk = cfg.get('max_tokens_per_chunk', 6000)

        source_txt_files = [
            f for f in os.listdir(text_to_translate_folder)
            if os.path.isfile(os.path.join(text_to_translate_folder, f)) and f.endswith('.txt')
        ]

        selected_input_folder = None

        if resume_from_last:
            # Resume: only use existing parts in translate_input_folder; do not split
            existing_parts = [
                f for f in os.listdir(translate_input_folder)
                if os.path.isfile(os.path.join(translate_input_folder, f)) and f.endswith('.txt')
            ]
            if existing_parts:
                self.logger.info("Resume mode enabled. Continue translating existing parts in translate_input_folder.")
                selected_input_folder = translate_input_folder
            else:
                self.logger.error("Resume mode enabled but no existing parts found in translate_input_folder. Aborting.")
                return False

        if selected_input_folder is None:
            if not source_txt_files:
                self.logger.error("No text files found to translate.")
                return False
            # Always split when not resuming
            first_input_file = os.path.join(text_to_translate_folder, source_txt_files[0])
            splitter = TextChunker(
                first_input_file,
                split_output_folder,
                max_tokens=max_tokens_per_chunk,
                model_name=tokenizer_name,
                logger=self.logger
            )
            self.logger.info(f"Splitting input file: {first_input_file}")
            splitter.split_file()
            selected_input_folder = split_output_folder

        file_manager = FileManager(selected_input_folder, translate_output_folder, self.logger)
        token_counter = TokenCounter(self.logger, model_name=tokenizer_name)
        api_key_manager = APIKeyManager(api_keys)
        api_client = OpenRouterClient(api_key_manager, self.api_url, self.logger)
        translator_service = TranslatorService(api_client, token_counter, self.preset_file, self.prefix, self.logger)

        # Initialize translation pipeline (enhanced pipeline is the runtime default)
        translation_processor = MasterTranslationProcessor(translator_service, self.logger)
        status = translation_processor.get_component_status()
        self.logger.info(f"Translation pipeline initialized (retries={status['max_retries']}, confidence={status['confidence_threshold']})")

        input_files = file_manager.get_input_files()

        # Resume continuity check: min pending index must equal max done index + 1 (or =1 if none done)
        if resume_from_last:
            def part_index(name: str):
                m = re.search(r"part_(\d+)\.txt$", name)
                return int(m.group(1)) if m else None

            done_indices: List[int] = []
            for f in os.listdir(translate_output_folder):
                if not f.endswith('.txt'):
                    continue
                idx = part_index(f)
                if idx is None:
                    continue
                path = os.path.join(translate_output_folder, f)
                if os.path.getsize(path) > 0:
                    done_indices.append(idx)

            pending_indices: List[int] = []
            for f in input_files:
                idx = part_index(f)
                if idx is None:
                    continue
                out_path = os.path.join(translate_output_folder, f)
                if not (os.path.exists(out_path) and os.path.getsize(out_path) > 0):
                    pending_indices.append(idx)

            if pending_indices:
                min_pending = min(pending_indices)
                if done_indices:
                    max_done = max(done_indices)
                    if min_pending != max_done + 1:
                        self.logger.error(
                            f"Resume continuity violated: max_done=part_{max_done}.txt, min_pending=part_{min_pending}.txt. They must be consecutive."
                        )
                        return False
                else:
                    if min_pending != 1:
                        self.logger.error(
                            f"Resume expects to start from part_1.txt but found min_pending=part_{min_pending}.txt."
                        )
                        return False

        # Skip files that already have output to continue from previous runs
        pending_files = []
        for filename in input_files:
            out_path = os.path.join(translate_output_folder, filename)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                # Frequent during large runs; reduce noise unless debugging
                self.logger.debug(f"Skipping already translated file: {filename}")
                continue
            pending_files.append(filename)

        if not pending_files:
            self.logger.info("Nothing to translate. All parts already processed.")
            return True

        # Process files with the enhanced system
        success_count = 0
        total_files = len(pending_files)

        self.logger.info(f"Processing {total_files} files...")
        for i, filename in enumerate(pending_files, 1):
            self.logger.info(f"Processing {i}/{total_files}: {filename}")

            try:
                text = file_manager.read_file(filename)
                out_path = os.path.join(translate_output_folder, filename)

                # Use enhanced processor (always enabled)
                result = translation_processor.process_file(text, out_path)

                if result.success:
                    success_count += 1
                    # Keep success concise
                    self.logger.info(f"Success: {filename} (score={result.quality_score:.2f}, confidence={result.confidence_level})")

                    # Log counts at INFO; full lists are debug to avoid spam
                    if result.issues_detected:
                        self.logger.warning(f"Issues detected: {len(result.issues_detected)} (use DEBUG for details)")
                        self.logger.debug(f"Issue details for {filename}: {result.issues_detected}")

                    if result.recommendations:
                        self.logger.info(f"Recommendations: {len(result.recommendations)} (use DEBUG for details)")
                        self.logger.debug(f"Recommendations for {filename}: {result.recommendations}")
                else:
                    # Enhanced processing failed for this file — abort the run and raise an error.
                    self.logger.error(f"❌ Failed: {filename}")
                    self.logger.error(f"📋 Issues: {result.issues_detected}")
                    raise RuntimeError(f"Enhanced processing failed for {filename}: {result.issues_detected}")

            except Exception as e:
                self.logger.error(f"❌ Error processing {filename}: {e}")
                continue

        # Log final statistics (concise)
        self.logger.info(f"Processing completed: {success_count}/{total_files} files successful")

        return success_count > 0

    def postprocess(self):
        cfg = self._load_config()
        text_to_translate_folder = cfg["text_to_translate_folder"]
        translate_output_folder = cfg["translate_output_folder"]
        # Only run engine-specific postprocess/apply. If engine is not configured
        # or does not implement postprocess, log and return — do not attempt a
        # hardcoded RenPy fallback.
        try:
            if not self.engine_processor:
                # Attempt to load engine if not already loaded
                self.engine_processor = self._load_engine_processor()

            if not self.engine_processor:
                self.logger.warning("No engine processor configured; skipping postprocess.")
                return

            if not hasattr(self.engine_processor, 'postprocess'):
                self.logger.warning("Configured engine processor does not implement postprocess(); skipping postprocess.")
                return

            self.logger.info("🔧 Running engine-specific postprocess...")
            outputs = self.engine_processor.postprocess(text_to_translate_folder, translate_output_folder)
            self.logger.info(f"✅ Engine postprocess produced: {outputs}")
            return

        except Exception as e:
            self.logger.error(f"Engine postprocess failed: {e}")
            return
