Engine implementation guide

Purpose
-------
This guide explains how to implement an engine processor for the translation framework.

Contract
--------
Implement a class that inherits from `common_modules.engines.base_engine.BaseEngineProcessor` and provide:

- preprocess(engine_input_folder: str, text_to_translate_folder: str) -> List[str]
  - Convert engine-specific source files (e.g. `.rpy`, `.csv`, `.json`) into the canonical block format used by the framework.
  - Canonical block format: each block must start with a header like `---------<number>` followed by block content.
  - Write canonical `.txt` files into `text_to_translate_folder` and return the created file paths.

- postprocess(text_to_translate_folder: str, translate_output_folder: str) -> List[str]
  - Read translated canonical files (e.g. merged_translated.txt or part_*.txt) from `translate_output_folder` and apply
    translations back to engine-specific outputs (e.g. produce final `.rpy`, `.csv`, or other files).
  - Return list of produced output file paths.

Notes
-----
- The Orchestrator will attempt to load the engine processor specified in `config/app_config.json` via `engine_processor_file`
  and `engine_processor_class`. If the engine processor implements `postprocess` that will be used. Otherwise the orchestrator
  falls back to a default RPY applier behaviour.

- Keep preprocess and postprocess deterministic and idempotent when possible. Use backups for outputs when overwriting.

Example
-------
See `work_space/engines/engine_default.py` for a minimal example included in the repo.
