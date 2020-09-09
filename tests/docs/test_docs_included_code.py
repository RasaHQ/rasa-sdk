import re
import os
import pytest

from pathlib import Path
from typing import List, Text, Tuple

DOCS_BASE_DIR = Path("docs/")
MDX_DOCS_FILES = list((DOCS_BASE_DIR / "docs").glob("**/*.mdx"))
# we're matching codeblocks `python-testable` type
# we support title or no title (you'll get a nice error message if there is a title)
TRAINING_DATA_CODEBLOCK_RE = re.compile(
    r"```python-runnable(?: title=[\"'][^\"']+[\"'])?(?: \((?P<python_path>.+?)\))?[^\n]*\n(?P<codeblock>.*?)```",
    re.DOTALL,
)


@pytest.mark.parametrize("mdx_file_path", MDX_DOCS_FILES)
def test_docs_python_blocks(mdx_file_path: Path):
    with mdx_file_path.open("r") as handle:
        mdx_content = handle.read()

    matches = TRAINING_DATA_CODEBLOCK_RE.finditer(mdx_content)
    lines_and_errors: List[Tuple[Text, Text]] = []

    for match in matches:
        python_path = match.group("python_path")
        if python_path:
            with (DOCS_BASE_DIR / python_path).open("r") as handle:
                codeblock = handle.read()
        else:
            codeblock = match.group("codeblock")

        start_index = match.span()[0]
        line_number = mdx_content.count("\n", 0, start_index) + 1
        try:
            exec(codeblock, {}, {})
        except Exception as e:
            lines_and_errors.append((str(line_number), str(e)))

    if lines_and_errors:
        error_message = ""
        for line_num, error in lines_and_errors:
            error_message += f"\n Invalid python code found at line {line_num}. Code execution failed with error {error}."
        raise AssertionError(error_message)
