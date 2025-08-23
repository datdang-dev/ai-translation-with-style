import os
import re
import tempfile

'''
@brief FileManager module - Handles reading and writing of text files for translation workflow.
@details
- Reads input files from a directory.
- Writes translated files to output directory.
- Provides sorted file listing for processing.
@constructor
- @param input_folder (str): Directory containing input files.
- @param output_folder (str): Directory to save output files.
- @param logger (Logger): Logger for logging events.
@method
- `get_input_files() -> list`
    - @return (list): Sorted list of input file names.
- `read_file(filename: str) -> str`
    - @param filename (str): Name of the file to read.
    - @return (str): File content.
- `write_file(filename: str, content: str) -> None`
    - @param filename (str): Name of the file to write.
    - @param content (str): Content to write to file.
    - @return None
'''
class FileManager:
    def __init__(self, input_folder, output_folder, logger):
        '''
        @brief Constructor for FileManager.
        @param input_folder (str): Directory containing input files.
        @param output_folder (str): Directory to save output files.
        @param logger (Logger): Logger for logging events.
        '''
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.logger = logger

    def get_input_files(self):
        '''
        @brief Returns a sorted list of input file names in the input folder.
        @return (list): Sorted list of input file names.
        '''
        files = [f for f in os.listdir(self.input_folder) if f.endswith('.txt')]
        def _key(x):
            m = re.search(r"(\d+)", x)
            if m:
                # files with numbers should sort by number first
                return (0, int(m.group(1)), x)
            # files without numeric part come after, sort by name
            return (1, None, x)
        sorted_files = sorted(files, key=_key)
        self.logger.info(f"Found {len(sorted_files)} input files.")
        return sorted_files

    def read_file(self, filename):
        '''
        @brief Reads the content of a file from the input folder.
        @param filename (str): Name of the file to read.
        @return (str): File content.
        '''
        path = os.path.join(self.input_folder, filename)
        self.logger.debug(f"Reading file: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, filename, content):
        '''
        @brief Writes content to a file in the output folder.
        @param filename (str): Name of the file to write.
        @param content (str): Content to write to file.
        @return None
        '''
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, filename)
        self.logger.debug(f"Writing translated file: {path}")
        # Atomic write: write to a temp file then replace
        dirpath = os.path.dirname(path)
        fd, tmppath = tempfile.mkstemp(dir=dirpath)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(tmppath, path)
        finally:
            # Cleanup if something went wrong and temp still exists
            try:
                if os.path.exists(tmppath):
                    os.remove(tmppath)
            except Exception:
                pass
