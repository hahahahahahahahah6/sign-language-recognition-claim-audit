"""Deterministic documentation and Python source inspection."""
import argparse
import ast
import json
from pathlib import Path
import re
import sys
from .phrases import SIGNLANGUAGE, NOSIGNLANGUAGE, GENERIC_NAMES, DEDICATED_CLASSES


def match_phrases(text, phrases):
    text = text.lower()
    matches = []
    for phrase in sorted(phrases, key=len, reverse=True):
        start = text.find(phrase)
        while start >= 0:
            matches.append(phrase)
            text = text[:start] + ' ' * len(phrase) + text[start + len(phrase):]
            start = text.find(phrase)
    return matches, text


def prose(text):
    return re.sub(r'^\s*```[^\n]*\n.*?^\s*```[^\n]*(?:\n|$)', '', text, flags=re.M | re.S).replace('`', '')


def claims(text):
    negative, remainder = match_phrases(prose(text), NOSIGNLANGUAGE)
    positive, _ = match_phrases(remainder, SIGNLANGUAGE)
    return positive, negative


def has_evidence(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    aliases = {}
    shadows = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                aliases[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                aliases[a.asname or a.name] = (n.module or '') + '.' + a.name

    def resolve(n):
        if isinstance(n, ast.Name):
            if n.id in shadows:
                return ''
            return aliases.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            base = resolve(n.value)
            return base + '.' + n.attr if base else ''
        return ''

    def kind(n):
        if not isinstance(n, ast.Call):
            return None
        name = resolve(n.func)
        last = name.split('.')[-1]
        if not name or last in shadows:
            return None
        if last == 'pipeline' and name.startswith('transformers.'):
            model = next((k.value for k in n.keywords if k.arg == 'model'), n.args[1] if len(n.args) > 1 else None)
            if n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 'video-classification' and isinstance(model, ast.Constant) and isinstance(model.value, str) and 'sign' in model.value.lower():
                return 'pair'
        if last in DEDICATED_CLASSES:
            return 'pair'
        if 'sign_language_translator' in name:
            return 'pair'
        if name.startswith('mediapipe.') and last in ('Hands', 'Holistic'):
            return 'landmark'
        return None

    instances = {}
    # Resolve simple assignment aliases to constructed instances, including with-as.
    for _ in range(2):
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                value = n.value
                k = kind(value) or (instances.get(value.id) if isinstance(value, ast.Name) else None)
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for target in targets:
                    if isinstance(target, ast.Name) and k:
                        instances[target.id] = k
            elif isinstance(n, ast.withitem) and isinstance(n.optional_vars, ast.Name):
                k = kind(n.context_expr)
                if k:
                    instances[n.optional_vars.id] = k
    processed = False
    predicted = False
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = resolve(n.func)
        last = name.split('.')[-1]
        if last in GENERIC_NAMES and last not in shadows:
            if isinstance(n.func, ast.Attribute) or (isinstance(n.func, ast.Name) and n.func.id in aliases):
                return True
        if isinstance(n.func, ast.Attribute) and n.func.attr == 'predict':
            predicted = True
        base = n.func.value if isinstance(n.func, ast.Attribute) else n.func
        k = kind(base) or (instances.get(base.id) if isinstance(base, ast.Name) else None)
        if k == 'pair':
            return True
        if k == 'landmark' and isinstance(n.func, ast.Attribute) and n.func.attr == 'process':
            processed = True
    return processed and predicted


def audit(repo, ignore=(), decisions=None):
    root = Path(repo)
    if not root.is_dir():
        raise OSError('Repository is not a directory: ' + str(root))
    sources, documents = [], []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if any(p in ('.git', '__pycache__', '.venv', 'venv', 'env', '.env') for p in rel.parts) or any((root.joinpath(*rel.parts[:i]) / 'pyvenv.cfg').is_file() for i in range(1, len(rel.parts))):
            continue
        if not path.is_file():
            continue
        label = rel.as_posix()
        if any(label.startswith(prefix) for prefix in ignore):
            if decisions is not None:
                decisions.append(label + ': ignored')
            continue
        if path.suffix == '.py':
            sources.append(path)
        if label == 'README.md' or (path.suffix == '.md' and (rel.parts[0] == 'docs' or 'tests' in rel.parts)):
            documents.append(path)
        if decisions is not None and (path.suffix == '.py' or path in documents):
            decisions.append(label + ': scanned')
    evidence = False
    for path in sources:
        if has_evidence(path.read_text(encoding='utf-8')):
            evidence = True
    findings = []
    for path in documents:
        positive, negative = claims(path.read_text(encoding='utf-8'))
        rel = path.relative_to(root)
        for phrases, contradiction, identifier in ((positive, not evidence, 'documented-sign-language-recognition-claim-false'), (negative, evidence, 'documented-no-sign-language-recognition-claim-false')):
            if contradiction:
                for phrase in phrases:
                    severity = 'medium' if 'tests' in rel.parts else 'high'
                    findings.append(dict(id=identifier, severity=severity, path=rel.as_posix(), phrase=phrase, verdict='FAIL', message='Documentation claim contradicts detected source evidence.'))
    return findings


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, message + '\n')


def main(argv=None):
    parser = Parser(description='Audit documentation claims against static Python evidence.')
    parser.add_argument('--version', action='version', version='0.1.0')
    sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    command = sub.add_parser('audit')
    command.add_argument('repo', nargs='?', default='.')
    command.add_argument('--json', action='store_true')
    command.add_argument('--verbose', action='store_true')
    command.add_argument('--ignore', action='append', default=[])
    command.add_argument('--fail-on', choices=('high', 'medium'), default='high')
    args = parser.parse_args(argv)
    decisions = []
    try:
        findings = audit(args.repo, args.ignore, decisions)
    except (OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.verbose:
        print('Scope: README.md, docs/**/*.md, test Markdown fixtures; Python sources under ' + str(Path(args.repo).resolve()), file=sys.stderr)
        print('\n'.join(decisions), file=sys.stderr)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for finding in findings:
            print('{severity} {id} {path}: {message}'.format(**finding))
        if not findings:
            print('PASS')
    return 2 if any(f['severity'] == 'high' or args.fail_on == 'medium' for f in findings) else 0
