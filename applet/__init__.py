from .translation_applet import TranslationApplet

# Import batch orchestrator function
try:
    from .batch_orchestrator import run_batch_translation_from_directory
    __all__ = ['TranslationApplet', 'run_batch_translation_from_directory']
except ImportError:
    # If batch_orchestrator doesn't exist yet, create a simple wrapper
    async def run_batch_translation_from_directory(
        config_path: str,
        input_dir: str,
        output_dir: str,
        pattern: str = "*.json",
        max_concurrent: int = 2,
        job_delay: float = 10.0
    ):
        """Wrapper for batch translation using the applet"""
        applet = TranslationApplet(config_path)
        return await applet.translate_batch_from_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern=pattern,
            job_delay=job_delay
        )
    
    __all__ = ['TranslationApplet', 'run_batch_translation_from_directory']