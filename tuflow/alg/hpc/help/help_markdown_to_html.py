from markdown2 import Markdown
from pathlib import Path


if __name__ == "__main__":
    markdowner = Markdown()

    help_folder = Path(__file__).parent
    print(f'Help folder: {help_folder}')
    print(help_folder.exists())
    markdown_files = list(help_folder.glob('.//**//*.md'))
    print(markdown_files)
    output_files = [help_folder / f'html/{x.stem}.html' for x in markdown_files]
    print(output_files)

    for markdown_file, output_file in zip(markdown_files, output_files):
        output_file.open('w').write(markdowner.convert(markdown_file.open().read()))