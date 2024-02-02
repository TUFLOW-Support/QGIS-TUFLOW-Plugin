from markdown2 import Markdown
import os
from pathlib import Path

if __name__ == "__main__":
    markdowner = Markdown()

    help_folder = Path(os.path.realpath(__file__)).parent / 'alg/help'
    print(f'Help folder: {help_folder}')
    print(help_folder.exists())
    markdown_files = list(help_folder.glob('markdown/*.md'))
    print(markdown_files)
    output_files = [help_folder/f'html/{x.stem}.html' for x in markdown_files]
    print(output_files)

    for markdown_file, output_file in zip(markdown_files, output_files):
        open(output_file, "w").write(markdowner.convert(open(markdown_file).read()))
