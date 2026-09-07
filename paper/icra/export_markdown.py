"""Export this manuscript's prose, math and fixed exhibits to a readable companion."""
from collections.abc import Callable
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
source = (ROOT / 'root.tex').read_text()
# This exporter is intentionally scoped to the commands used by this manuscript.

def argument(text: str, start: int) -> tuple[str, int]:
    depth = 1
    index = start + 1
    while depth:
        if text[index] == '{' and text[index-1] != '\\':
            depth += 1
        if text[index] == '}' and text[index-1] != '\\':
            depth -= 1
        index += 1
    return text[start+1:index-1], index


def commands(text: str, name: str, format_value: Callable[[str], str]) -> str:
    prefix = '\\' + name + '{'
    while prefix in text:
        start = text.index(prefix)
        value, end = argument(text, start+len(prefix)-1)
        text = text[:start] + format_value(value) + text[end:]
    return text


title, _ = argument(source, source.index('\\title{')+6)
title = ' '.join(title.replace(r'\LARGE', '').replace(r'\bf', '').split())
text = source.split('\\begin{abstract}', 1)[1].split('\\bibliographystyle', 1)[0]
text = '## Abstract\n\n' + text.replace('\\end{abstract}', '')
refs = {'fig:interface': '1', 'fig:scale': '2', 'fig:confirmation': '3',
        'tab:repair': '1', 'tab:confirmation': '2', 'tab:controls': '3', 'eq:gate': '3'}
# Resolve labels directly from the actual ordered environments as well.
for kind in ('figure', 'table'):
    blocks = re.findall(r'\\begin\{' + kind + r'\*?\}.*?\\end\{' + kind + r'\*?\}', text, flags=re.S)
    for index, block in enumerate(blocks, 1):
        for label in re.findall(r'\\label\{([^}]+)\}', block):
            refs[label] = str(index)


def figure(match: re.Match[str]) -> str:
    block = match.group()
    file = re.search(r'\\includegraphics\[[^]]*\]\{([^}]+)\}', block)[1]
    caption, _ = argument(block, block.index('\\caption{')+8)
    directory = 'figures' if file != 'f2_bank_scale.pdf' else '../figures'
    return f'\n\n![{Path(file).stem}]({directory}/{Path(file).stem}.png)\n\n{caption}\n\n'


def table(match: re.Match[str]) -> str:
    block = match.group()
    caption, _ = argument(block, block.index('\\caption{')+8)
    body = block.split('\\toprule', 1)[1].split('\\bottomrule', 1)[0].replace('\\midrule', '')
    rows = [[v.strip().replace('\n', ' ') for v in row.strip().split('&')]
            for row in body.split('\\\\') if row.strip()]
    output = ['| ' + ' | '.join(row) + ' |' for row in rows]
    output.insert(1, '| ' + ' | '.join('---' for _ in rows[0]) + ' |')
    return '\n\n' + caption + '\n\n' + '\n'.join(output) + '\n\n'


text = re.sub(r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}', figure, text, flags=re.S)
text = re.sub(r'\\begin\{table\*?\}.*?\\end\{table\*?\}', table, text, flags=re.S)
text = commands(text, 'section', lambda v: '\n\n## ' + v + '\n\n')
text = commands(text, 'section*', lambda v: '\n\n## ' + v + '\n\n')
text = commands(text, 'subsection', lambda v: '\n\n### ' + v + '\n\n')
text = commands(text, 'paragraph', lambda v: '\n\n**' + v + '.** ')
for name, wrapper in [('textbf', '**'), ('emph', '*'), ('texttt', '`')]:
    text = commands(text, name, lambda v, wrapper=wrapper: wrapper + v + wrapper)
text = commands(text, 'ref', lambda v: refs.get(v, v))
text = commands(text, 'eqref', lambda v: '(' + refs.get(v, v) + ')')
text = commands(text, 'label', lambda v: '')
keys = []

def cite(value: str) -> str:
    output = []
    for key in value.split(','):
        if key not in keys:
            keys.append(key)
        output.append(f'[{keys.index(key)+1}](references.bib)')
    return ', '.join(output)


text = commands(text, 'cite', cite)
text = text.replace('\\begin{equation}', '\n$$\n').replace('\\end{equation}', '\n$$\n')
text = text.replace('\\begin{enumerate}', '').replace('\\end{enumerate}', '').replace('\\item ', '\n1. ')
text = text.replace('\\method{}', 'CLIMB').replace('\\%', '%').replace('\\_', '_').replace('~', ' ')
text = text.replace('\\,', ' ').replace('``', '“').replace("''", '”').replace('---', '—').replace('--', '–')
# Restore Markdown's table separators after typographic dash conversion.
text = re.sub(r'(?m)^\| (?:— \| ?)+$', lambda m: m.group().replace('—', '---'), text)
text = re.sub(r'(?m)^%.*\n?', '', text)
text = re.sub(r'\n{3,}', '\n\n', text)
header = f'# {title.replace(chr(92)+chr(92), " ").replace("--", "–")}\n\n'
h1_note = ('The completed H1 admission result is reported separately from the allocation study.'
           if r'\label{sec:h1result}' in source else
           'H1 is pending and supplies no contribution or result here.')
header += ('**Status: unsealed manuscript.** Generated from `root.tex`; '
           'the compiled PDF is the submission-layout authority. The allocation result is '
           'complete and inconclusive. ' + h1_note + '\n\n')
footer = '\n\n## References\n\nFull bibliographic entries are maintained in [references.bib](references.bib) and rendered in [the PDF](ICRA_DRAFT.pdf). Citation order:\n\n'
footer += '\n'.join(f'{i}. `{key}`' for i, key in enumerate(keys, 1)) + '\n'
output = header + text.strip() + footer
(ROOT / 'DRAFT.md').write_text('\n'.join(line.rstrip() for line in output.splitlines()) + '\n')
print(f'Exported {len(keys)} citations and all manuscript prose/exhibits')
