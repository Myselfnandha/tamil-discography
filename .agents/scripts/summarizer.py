#!/usr/bin/env python3
"""
Heuristic file summarizer — generates 1-line intelligent summaries per file.

Phase 1: Python (AST-based) + JS/TS (regex-based)
Phase 2: Go, Rust, Java, C/C++, Dart, Ruby (regex fallback)

Zero external dependencies. Uses only Python stdlib.
"""

import ast
import os
import re


# =============================================================================
# Python AST-Based Summarizer
# =============================================================================

class PythonSummarizer:
    """Deep heuristic analysis of Python files using the ast module."""

    # Patterns to detect inside function bodies
    OPERATION_PATTERNS = {
        'api_route': re.compile(r'@(app|router|api)\.(get|post|put|delete|patch|route|websocket)\s*\('),
        'db_query': re.compile(r'\b(session|db|cursor|conn|connection)\.(query|execute|add|commit|delete|merge|flush|select|insert|update|fetchone|fetchall)\b'),
        'orm_model': re.compile(r'class\s+\w+\(.*(?:Base|Model|DeclarativeBase|db\.Model)'),
        'http_call': re.compile(r'\b(requests|httpx|aiohttp|urllib)\.(get|post|put|delete|patch|head|request)\b'),
        'file_io': re.compile(r'\bopen\s*\(|\.read\(|\.write\(|\.readlines\(|Path\s*\('),
        'auth_pattern': re.compile(r'(?:import|from)\s+.*\b(jwt|bcrypt|oauth)\b|\bdef\s+\w*(?:login|logout|auth|verify_token|verify_password)\b|@\w*auth\w*', re.I),
        'test_pattern': re.compile(r'^\s*(?:def\s+test_|class\s+Test\w+|@pytest\.)', re.M),
        'cli_pattern': re.compile(r'\b(argparse|click|typer|fire)\b'),
        'async_pattern': re.compile(r'\basync\s+def\b'),
        'celery_task': re.compile(r'@(shared_task|task|celery\.task)\b'),
        'django_view': re.compile(r'class\s+\w+\(.*(?:View|ViewSet|APIView|GenericAPIView|ModelViewSet)\)'),
        'fastapi_dep': re.compile(r'\bDepends\s*\('),
        'socket_pattern': re.compile(r'\b(socket|websocket|socketio|ws)\b', re.I),
        'cache_pattern': re.compile(r'(?:import|from)\s+.*\b(redis|memcache)\b|@lru_cache|@cache\b|\bcache\.(?:get|set|delete)\b', re.I),
        'ml_pattern': re.compile(r'\b(torch|tensorflow|keras|sklearn|numpy|pandas|model\.fit|model\.predict)\b'),
        'logging_pattern': re.compile(r'\b(logger|logging|log\.)\b'),
    }

    def summarize(self, filepath, content):
        """Generate a 1-line summary of a Python file."""
        try:
            tree = ast.parse(content, filename=filepath)
        except SyntaxError:
            return self._fallback_summary(filepath, content)

        info = {
            'classes': [],
            'functions': [],
            'decorators': set(),
            'imports': set(),
            'operations': set(),
            'docstring': None,
            'is_test': False,
            'is_config': False,
            'is_init': False,
            'is_main': False,
            'constants': [],
        }

        basename = os.path.basename(filepath)
        info['is_test'] = basename.startswith('test_') or basename.endswith('_test.py')
        info['is_config'] = basename in ('config.py', 'settings.py', 'conf.py', 'constants.py')
        info['is_init'] = basename == '__init__.py'
        info['is_main'] = basename == '__main__.py'

        # Extract module docstring
        info['docstring'] = ast.get_docstring(tree)

        for node in ast.walk(tree):
            # Collect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info['imports'].add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info['imports'].add(node.module.split('.')[0])

            # Collect classes
            elif isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)
                class_info = {
                    'name': node.name,
                    'bases': bases,
                    'methods': [],
                    'decorators': [],
                }
                for dec in node.decorator_list:
                    dec_name = self._get_decorator_name(dec)
                    if dec_name:
                        class_info['decorators'].append(dec_name)
                        info['decorators'].add(dec_name)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_info['methods'].append(item.name)
                info['classes'].append(class_info)

            # Collect functions (top-level only)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if self._is_top_level(tree, node):
                    func_info = {
                        'name': node.name,
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'decorators': [],
                        'args_count': len(node.args.args),
                    }
                    for dec in node.decorator_list:
                        dec_name = self._get_decorator_name(dec)
                        if dec_name:
                            func_info['decorators'].append(dec_name)
                            info['decorators'].add(dec_name)
                    info['functions'].append(func_info)

            # Collect top-level constants
            elif isinstance(node, ast.Assign) and self._is_top_level(tree, node):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        info['constants'].append(target.id)

        # Scan raw content for operation patterns
        for op_name, pattern in self.OPERATION_PATTERNS.items():
            if pattern.search(content):
                info['operations'].add(op_name)

        return self._build_summary(filepath, info)

    def _is_top_level(self, tree, node):
        """Check if a node is at the top level of the module."""
        return node in tree.body

    def _get_decorator_name(self, dec):
        """Extract decorator name from AST node."""
        if isinstance(dec, ast.Name):
            return dec.id
        elif isinstance(dec, ast.Attribute):
            return dec.attr
        elif isinstance(dec, ast.Call):
            return self._get_decorator_name(dec.func)
        return None

    def _build_summary(self, filepath, info):
        """Build the 1-line summary from collected info."""
        parts = []
        basename = os.path.basename(filepath)

        # Special file types
        if info['is_init']:
            if info['imports']:
                parts.append(f"Package init: re-exports from {', '.join(sorted(list(info['imports']))[:5])}")
            else:
                parts.append("Package init (empty)")
            if info['classes']:
                parts.append(f"{len(info['classes'])} classes")
            if info['functions']:
                parts.append(f"{len(info['functions'])} functions")
            return '; '.join(parts) if parts else "Package initializer"

        if info['is_config']:
            const_preview = ', '.join(info['constants'][:5])
            if const_preview:
                return f"Configuration: {const_preview}" + (f" +{len(info['constants'])-5} more" if len(info['constants']) > 5 else "")
            return "Configuration module"

        if info['is_main']:
            return "CLI entry point" + (f" using {', '.join(sorted(list(info['imports'] & {'argparse', 'click', 'typer', 'fire'})))}" if info['imports'] & {'argparse', 'click', 'typer', 'fire'} else "")

        # Test files
        if info['is_test'] or 'test_pattern' in info['operations']:
            test_subjects = []
            for func in info['functions']:
                name = func['name']
                if name.startswith('test_'):
                    subject = name[5:].split('_')[0]
                    if subject not in test_subjects:
                        test_subjects.append(subject)
            for cls in info['classes']:
                name = cls['name']
                if name.startswith('Test'):
                    subject = name[4:]
                    if subject not in test_subjects:
                        test_subjects.append(subject)
            count = len(info['functions']) + sum(len(c['methods']) for c in info['classes'])
            subject_str = f" for {', '.join(test_subjects[:3])}" if test_subjects else ""
            return f"Tests{subject_str}: {count} test functions/methods"

        # Detect primary role from operations
        role = self._detect_role(info)
        if role:
            parts.append(role)

        # Classes
        if info['classes']:
            class_names = [c['name'] for c in info['classes'][:3]]
            suffix = f" +{len(info['classes'])-3} more" if len(info['classes']) > 3 else ""
            parts.append(f"classes: {', '.join(class_names)}{suffix}")

        # Functions
        if info['functions']:
            func_names = [f['name'] for f in info['functions'] if not f['name'].startswith('_')][:4]
            if func_names:
                suffix = f" +{len(info['functions'])-4} more" if len(info['functions']) > 4 else ""
                parts.append(f"functions: {', '.join(func_names)}{suffix}")

        # Use docstring as fallback
        if not parts and info['docstring']:
            doc = info['docstring'].split('\n')[0].strip()
            if len(doc) > 100:
                doc = doc[:97] + '...'
            return doc

        return '; '.join(parts) if parts else f"Python module ({len(info['functions'])} functions, {len(info['classes'])} classes)"

    def _detect_role(self, info):
        """Detect the primary role/purpose of the file from operations."""
        ops = info['operations']
        roles = []

        if 'api_route' in ops or any('route' in d or 'api' in d for d in info['decorators']):
            # Try to extract route paths
            roles.append("API routes")
        if 'django_view' in ops:
            roles.append("Django views")
        if 'orm_model' in ops or 'db_query' in ops:
            roles.append("database operations")
        if 'http_call' in ops:
            roles.append("HTTP client")
        if 'auth_pattern' in ops:
            roles.append("authentication")
        if 'celery_task' in ops:
            roles.append("async tasks (Celery)")
        if 'ml_pattern' in ops:
            roles.append("ML/data processing")
        if 'socket_pattern' in ops:
            roles.append("WebSocket/real-time")
        if 'cache_pattern' in ops:
            roles.append("caching")
        if 'cli_pattern' in ops:
            roles.append("CLI tool")

        if roles:
            return ', '.join(roles[:3])
        return None

    def _fallback_summary(self, filepath, content):
        """Fallback for files that can't be parsed by ast."""
        lines = content.split('\n')
        func_count = sum(1 for l in lines if re.match(r'^(async\s+)?def\s+\w+', l))
        class_count = sum(1 for l in lines if re.match(r'^class\s+\w+', l))

        # Try to get first comment block
        first_comment = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('#!'):
                first_comment.append(stripped.lstrip('# ').strip())
            elif first_comment:
                break

        if first_comment:
            comment = ' '.join(first_comment[:2])
            if len(comment) > 80:
                comment = comment[:77] + '...'
            return f"{comment} ({func_count} functions, {class_count} classes)"

        return f"Python module: {class_count} classes, {func_count} functions, {len(lines)} lines"


# =============================================================================
# JavaScript / TypeScript Regex-Based Summarizer
# =============================================================================

class JSTSSummarizer:
    """Regex-based analysis of JS/TS files."""

    PATTERNS = {
        'react_component': re.compile(r'(?:export\s+(?:default\s+)?)?(?:function|const)\s+([A-Z]\w+)\s*(?:=\s*(?:\([^)]*\)|[^=])\s*=>|[\(:])', re.M),
        'react_hooks': re.compile(r'\b(useState|useEffect|useCallback|useMemo|useRef|useContext|useReducer|useQuery|useMutation)\b'),
        'exports_named': re.compile(r'^export\s+(?:async\s+)?(?:function|const|let|var|class|interface|type|enum)\s+(\w+)', re.M),
        'exports_default': re.compile(r'^export\s+default\s+(?:function|class|)\s*(\w*)', re.M),
        'function_decl': re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.M),
        'class_decl': re.compile(r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', re.M),
        'interface_decl': re.compile(r'^(?:export\s+)?interface\s+(\w+)', re.M),
        'type_decl': re.compile(r'^(?:export\s+)?type\s+(\w+)\s*=', re.M),
        'arrow_func': re.compile(r'^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*(?::\s*\w+(?:<[^>]+>)?\s*)?=>', re.M),
        'express_route': re.compile(r'(?:app|router)\.(get|post|put|delete|patch|use|all)\s*\('),
        'nextjs_page': re.compile(r'export\s+default\s+(?:async\s+)?function\s+\w*Page'),
        'nextjs_api': re.compile(r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b'),
        'prisma_usage': re.compile(r'\bprisma\.\w+\.(find|create|update|delete|upsert|aggregate|count|groupBy)\b'),
        'fetch_call': re.compile(r'\bfetch\s*\('),
        'axios_call': re.compile(r'\baxios\.(get|post|put|delete|patch|request)\b'),
        'import_react': re.compile(r'import\s+.*from\s+[\'"]react[\'"]'),
        'import_next': re.compile(r'import\s+.*from\s+[\'"]next'),
        'import_express': re.compile(r'import\s+.*from\s+[\'"]express[\'"]|require\s*\(\s*[\'"]express[\'"]\s*\)'),
        'zod_schema': re.compile(r'\bz\.\w+\(|zodResolver\b'),
        'graphql': re.compile(r'\bgql\s*`|useQuery\s*\(|useMutation\s*\('),
        'test_file': re.compile(r'\b(describe|it|test|expect|jest|vitest|beforeEach|afterEach|beforeAll|afterAll)\s*\('),
        'middleware': re.compile(r'(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+middleware\b|NextResponse\.(next|redirect|rewrite)\b'),
        'styled_comp': re.compile(r'styled\.\w+`|css`'),
        'tailwind': re.compile(r'className\s*=\s*[{"\'].*(?:flex|grid|p-|m-|bg-|text-|w-|h-)'),
        'enum_decl': re.compile(r'^(?:export\s+)?(?:const\s+)?enum\s+(\w+)', re.M),
        'socket_io': re.compile(r'\b(?:io|socket)\.(on|emit|connect|disconnect)\b'),
    }

    def summarize(self, filepath, content):
        """Generate a 1-line summary of a JS/TS file."""
        basename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1]
        is_ts = ext in ('.ts', '.tsx')
        is_jsx = ext in ('.jsx', '.tsx')

        matches = {}
        for name, pattern in self.PATTERNS.items():
            found = pattern.findall(content)
            if found:
                matches[name] = found

        parts = []

        # Test file detection
        if 'test_file' in matches or '.test.' in basename or '.spec.' in basename:
            test_count = len(matches.get('test_file', []))
            return f"Test suite: {test_count} test blocks" + (f", {', '.join(set(matches.get('test_file', [])[:3]))}" if matches.get('test_file') else "")

        # React component detection
        is_react = 'import_react' in matches or is_jsx or 'react_hooks' in matches
        if is_react and 'react_component' in matches:
            comp_names = list(set(matches['react_component']))[:3]
            hooks = list(set(matches.get('react_hooks', [])))[:4]
            parts.append(f"React component: {', '.join(comp_names)}")
            if hooks:
                parts.append(f"hooks: {', '.join(hooks)}")
            if 'fetch_call' in matches or 'axios_call' in matches:
                parts.append("fetches data")
            if 'prisma_usage' in matches:
                parts.append("Prisma queries")
            return '; '.join(parts)

        # Next.js detection
        if 'nextjs_api' in matches:
            methods = list(set(matches['nextjs_api']))
            parts.append(f"Next.js API route: {', '.join(methods)} handlers")
            if 'prisma_usage' in matches:
                parts.append("Prisma queries")
            if 'zod_schema' in matches:
                parts.append("Zod validation")
            return '; '.join(parts)

        if 'nextjs_page' in matches:
            parts.append("Next.js page component")
            if 'react_hooks' in matches:
                parts.append(f"hooks: {', '.join(list(set(matches['react_hooks']))[:3])}")
            return '; '.join(parts)

        if 'middleware' in matches:
            return "Next.js/Express middleware" + (", auth/routing logic" if any(p in matches for p in ['import_next']) else "")

        # Express detection
        if 'express_route' in matches:
            methods = list(set(matches['express_route']))
            parts.append(f"Express routes: {', '.join(methods)} handlers")
            if 'prisma_usage' in matches or 'db_query' in content:
                parts.append("database operations")
            return '; '.join(parts)

        # Type/interface-heavy files
        if 'interface_decl' in matches or 'type_decl' in matches:
            interfaces = matches.get('interface_decl', [])
            types = matches.get('type_decl', [])
            enums = matches.get('enum_decl', [])
            all_types = interfaces + types + enums
            if len(all_types) >= 3:  # Primarily a types file
                preview = ', '.join(all_types[:4])
                suffix = f" +{len(all_types)-4} more" if len(all_types) > 4 else ""
                return f"Type definitions: {preview}{suffix}"

        # Class-based
        if 'class_decl' in matches:
            classes = matches['class_decl']
            class_info = []
            for c in classes[:3]:
                if isinstance(c, tuple):
                    name, base = c
                    class_info.append(f"{name}" + (f" extends {base}" if base else ""))
                else:
                    class_info.append(c)
            parts.append(f"Classes: {', '.join(class_info)}")

        # Exported functions
        if 'exports_named' in matches:
            names = list(set(matches['exports_named']))[:4]
            suffix = f" +{len(matches['exports_named'])-4} more" if len(matches['exports_named']) > 4 else ""
            parts.append(f"exports: {', '.join(names)}{suffix}")
        elif 'function_decl' in matches or 'arrow_func' in matches:
            funcs = list(set(matches.get('function_decl', []) + matches.get('arrow_func', [])))[:4]
            if funcs:
                parts.append(f"functions: {', '.join(funcs)}")

        # Operations
        ops = []
        if 'fetch_call' in matches or 'axios_call' in matches:
            ops.append("HTTP calls")
        if 'prisma_usage' in matches:
            ops.append("Prisma DB")
        if 'zod_schema' in matches:
            ops.append("Zod validation")
        if 'graphql' in matches:
            ops.append("GraphQL")
        if 'socket_io' in matches:
            ops.append("WebSocket")
        if ops:
            parts.append(', '.join(ops))

        if parts:
            lang = "TypeScript" if is_ts else "JavaScript"
            return '; '.join(parts)

        # Fallback: count exports and functions
        return self._fallback(filepath, content, is_ts)

    def _fallback(self, filepath, content, is_ts):
        """Fallback summary using line counts."""
        lines = content.split('\n')
        export_count = sum(1 for l in lines if l.strip().startswith('export'))
        func_count = sum(1 for l in lines if re.match(r'^\s*(?:export\s+)?(?:async\s+)?(?:function|const\s+\w+\s*=.*=>)', l))
        lang = "TypeScript" if is_ts else "JavaScript"
        return f"{lang} module: {export_count} exports, {func_count} functions, {len(lines)} lines"


# =============================================================================
# Generic Regex Fallback Summarizer (Go, Rust, Java, C/C++, Dart, Ruby, etc.)
# =============================================================================

class GenericSummarizer:
    """Regex-based analysis for languages without AST support in Python stdlib."""

    LANG_PATTERNS = {
        # Go
        '.go': {
            'function': re.compile(r'^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(', re.M),
            'struct': re.compile(r'^type\s+(\w+)\s+struct\b', re.M),
            'interface': re.compile(r'^type\s+(\w+)\s+interface\b', re.M),
            'package': re.compile(r'^package\s+(\w+)', re.M),
            'import': re.compile(r'import\s+(?:\(\s*\n((?:.*\n)*?)\s*\)|"([^"]+)")', re.M),
            'http_handler': re.compile(r'http\.(HandleFunc|Handle|ListenAndServe|Get|Post)\b'),
            'goroutine': re.compile(r'\bgo\s+\w+'),
            'channel': re.compile(r'\bchan\s+\w+|<-\s*\w+'),
        },
        # Rust
        '.rs': {
            'function': re.compile(r'^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)', re.M),
            'struct': re.compile(r'^(?:pub\s+)?struct\s+(\w+)', re.M),
            'enum': re.compile(r'^(?:pub\s+)?enum\s+(\w+)', re.M),
            'trait': re.compile(r'^(?:pub\s+)?trait\s+(\w+)', re.M),
            'impl': re.compile(r'^impl(?:<[^>]+>)?\s+(\w+)', re.M),
            'macro': re.compile(r'^macro_rules!\s+(\w+)', re.M),
        },
        # Java
        '.java': {
            'class': re.compile(r'^(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)', re.M),
            'interface': re.compile(r'^(?:public\s+)?interface\s+(\w+)', re.M),
            'method': re.compile(r'^\s+(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\],\s]+)\s+(\w+)\s*\(', re.M),
            'annotation': re.compile(r'^(\s*@\w+)', re.M),
            'spring': re.compile(r'@(RestController|Controller|Service|Repository|Component|Bean|Autowired|RequestMapping|GetMapping|PostMapping)\b'),
        },
        # C/C++
        '.c': {
            'function': re.compile(r'^(?:static\s+)?(?:inline\s+)?(?:const\s+)?(?:\w+[\s*]+)+(\w+)\s*\([^)]*\)\s*\{', re.M),
            'struct': re.compile(r'^(?:typedef\s+)?struct\s+(\w+)', re.M),
            'include': re.compile(r'^#include\s+[<"]([^>"]+)[>"]', re.M),
            'define': re.compile(r'^#define\s+(\w+)', re.M),
        },
        '.cpp': {
            'function': re.compile(r'^(?:(?:virtual|static|inline|const|explicit)\s+)*(?:\w+[\s*&]+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?(?:=\s*0\s*)?[{;]', re.M),
            'class': re.compile(r'^class\s+(\w+)', re.M),
            'namespace': re.compile(r'^namespace\s+(\w+)', re.M),
            'template': re.compile(r'^template\s*<', re.M),
        },
        '.h': None,   # Uses .cpp patterns
        '.hpp': None,  # Uses .cpp patterns
        # Dart
        '.dart': {
            'class': re.compile(r'^(?:abstract\s+)?class\s+(\w+)', re.M),
            'function': re.compile(r'^\s*(?:static\s+)?(?:Future<[^>]+>\s+|void\s+|int\s+|String\s+|bool\s+|double\s+|dynamic\s+|List<[^>]+>\s+|Map<[^>]+>\s+|\w+\s+)(\w+)\s*\(', re.M),
            'widget': re.compile(r'class\s+(\w+)\s+extends\s+(Stateless|Stateful)Widget\b'),
            'provider': re.compile(r'\b(Provider|ChangeNotifier|Riverpod|Bloc|Cubit)\b'),
            'flutter_import': re.compile(r"import\s+'package:flutter/"),
        },
        # Ruby
        '.rb': {
            'class': re.compile(r'^class\s+(\w+)', re.M),
            'module': re.compile(r'^module\s+(\w+)', re.M),
            'method': re.compile(r'^\s*def\s+(?:self\.)?(\w+)', re.M),
            'rails': re.compile(r'class\s+\w+\s*<\s*(ApplicationController|ApplicationRecord|ActiveRecord|ActionMailer|ApplicationJob)\b'),
            'route': re.compile(r'\b(get|post|put|patch|delete|resources|resource|root)\s+'),
        },
        # SQL
        '.sql': {
            'create_table': re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)', re.I | re.M),
            'alter_table': re.compile(r'ALTER\s+TABLE\s+[`"\']?(\w+)', re.I | re.M),
            'select': re.compile(r'SELECT\s+.+\s+FROM\s+[`"\']?(\w+)', re.I),
            'insert': re.compile(r'INSERT\s+INTO\s+[`"\']?(\w+)', re.I | re.M),
            'create_index': re.compile(r'CREATE\s+(?:UNIQUE\s+)?INDEX', re.I | re.M),
            'view': re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+[`"\']?(\w+)', re.I | re.M),
            'procedure': re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\s+[`"\']?(\w+)', re.I | re.M),
        },
        # Shell
        '.sh': {
            'function': re.compile(r'^(?:function\s+)?(\w+)\s*\(\)\s*\{', re.M),
            'shebang': re.compile(r'^#!\s*(/\S+)', re.M),
            'source': re.compile(r'^\.\s+(\S+)|^source\s+(\S+)', re.M),
        },
        '.bash': None,  # Uses .sh patterns
        # YAML/Config
        '.yaml': {
            'top_keys': re.compile(r'^(\w[\w-]*)\s*:', re.M),
            'docker': re.compile(r'^services:|^volumes:|^networks:', re.M),
            'k8s': re.compile(r'^kind:\s*(\w+)', re.M),
            'github_actions': re.compile(r'^on:|^jobs:', re.M),
        },
        '.yml': None,  # Uses .yaml patterns
        # JSON files
        '.json': {
            'package_json': re.compile(r'"(name|version|scripts|dependencies|devDependencies)"'),
            'tsconfig': re.compile(r'"(compilerOptions|include|exclude)"'),
        },
        # Vue
        '.vue': {
            'template': re.compile(r'<template', re.I),
            'script': re.compile(r'<script(?:\s+(?:setup|lang="ts"))?\s*>', re.I),
            'composition_api': re.compile(r'\b(ref|reactive|computed|watch|onMounted|defineProps|defineEmits)\b'),
            'component_name': re.compile(r"(?:name:\s*['\"](\w+)['\"]|defineComponent\s*\(\s*\{[^}]*name:\s*['\"](\w+)['\"])"),
        },
        # Svelte
        '.svelte': {
            'script': re.compile(r'<script(?:\s+(?:context="module"|lang="ts"))?\s*>'),
            'reactive': re.compile(r'\$:\s+\w+'),
            'store': re.compile(r'\b(writable|readable|derived)\b'),
            'slot': re.compile(r'<slot'),
        },
        # GraphQL
        '.graphql': {
            'type': re.compile(r'^type\s+(\w+)', re.M),
            'query': re.compile(r'^(?:type\s+)?Query\b', re.M),
            'mutation': re.compile(r'^(?:type\s+)?Mutation\b', re.M),
            'input': re.compile(r'^input\s+(\w+)', re.M),
            'enum': re.compile(r'^enum\s+(\w+)', re.M),
        },
        '.gql': None,  # Uses .graphql patterns
        # Prisma
        '.prisma': {
            'model': re.compile(r'^model\s+(\w+)', re.M),
            'enum': re.compile(r'^enum\s+(\w+)', re.M),
            'datasource': re.compile(r'^datasource\s+(\w+)', re.M),
            'generator': re.compile(r'^generator\s+(\w+)', re.M),
        },
        # TOML
        '.toml': {
            'sections': re.compile(r'^\[(\w[\w.-]*)\]', re.M),
            'cargo': re.compile(r'^\[package\]|^\[dependencies\]', re.M),
        },
        # Dockerfile
        'Dockerfile': {
            'from': re.compile(r'^FROM\s+(\S+)', re.M),
            'stage': re.compile(r'^FROM\s+\S+\s+AS\s+(\w+)', re.I | re.M),
            'expose': re.compile(r'^EXPOSE\s+(\d+)', re.M),
            'cmd': re.compile(r'^(?:CMD|ENTRYPOINT)\s+(.+)$', re.M),
        },
    }

    # Alias mappings for extensions that share patterns
    ALIASES = {'.h': '.cpp', '.hpp': '.cpp', '.bash': '.sh', '.yml': '.yaml', '.gql': '.graphql'}

    def summarize(self, filepath, content):
        """Generate a 1-line summary using regex patterns."""
        basename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1]

        # Check for Dockerfile by name
        if basename.startswith('Dockerfile'):
            ext = 'Dockerfile'

        # Resolve aliases
        if ext in self.ALIASES:
            ext = self.ALIASES[ext]

        patterns = self.LANG_PATTERNS.get(ext)
        if not patterns:
            return self._generic_fallback(filepath, content)

        matches = {}
        for name, pattern in patterns.items():
            found = pattern.findall(content)
            if found:
                matches[name] = found

        return self._build_summary(filepath, ext, content, matches)

    def _build_summary(self, filepath, ext, content, matches):
        """Build language-specific summary from matched patterns."""
        parts = []
        lines = content.split('\n')

        if ext == '.go':
            pkg = matches.get('package', [''])[0] if matches.get('package') else ''
            if pkg:
                parts.append(f"Go package '{pkg}'")
            structs = matches.get('struct', [])
            interfaces = matches.get('interface', [])
            funcs = matches.get('function', [])
            exported = [f for f in funcs if f[0].isupper()]
            if structs:
                parts.append(f"structs: {', '.join(structs[:3])}")
            if interfaces:
                parts.append(f"interfaces: {', '.join(interfaces[:3])}")
            if exported:
                parts.append(f"{len(exported)} exported functions")
            if 'http_handler' in matches:
                parts.append("HTTP handlers")
            if 'goroutine' in matches:
                parts.append("concurrent (goroutines)")

        elif ext == '.rs':
            structs = matches.get('struct', [])
            enums = matches.get('enum', [])
            traits = matches.get('trait', [])
            funcs = matches.get('function', [])
            pub_funcs = [f for f in funcs if f[0].islower()]  # Simplified
            if structs:
                parts.append(f"structs: {', '.join(structs[:3])}")
            if enums:
                parts.append(f"enums: {', '.join(enums[:3])}")
            if traits:
                parts.append(f"traits: {', '.join(traits[:3])}")
            if funcs:
                parts.append(f"{len(funcs)} functions")
            if matches.get('macro'):
                parts.append(f"macros: {', '.join(matches['macro'][:2])}")

        elif ext == '.java':
            classes = matches.get('class', [])
            methods = matches.get('method', [])
            if matches.get('spring'):
                spring_annots = list(set(matches['spring']))
                parts.append(f"Spring {', '.join(spring_annots[:3])}")
            if classes:
                parts.append(f"classes: {', '.join(classes[:3])}")
            if methods:
                parts.append(f"{len(methods)} methods")

        elif ext in ('.c', '.cpp'):
            classes = matches.get('class', [])
            structs = matches.get('struct', [])
            funcs = matches.get('function', [])
            namespaces = matches.get('namespace', [])
            if namespaces:
                parts.append(f"namespace {', '.join(namespaces[:2])}")
            if classes:
                parts.append(f"classes: {', '.join(classes[:3])}")
            if structs:
                parts.append(f"structs: {', '.join(structs[:3])}")
            if funcs:
                parts.append(f"{len(funcs)} functions")

        elif ext == '.dart':
            widgets = matches.get('widget', [])
            classes = matches.get('class', [])
            if widgets:
                widget_info = [f"{w[0]} ({w[1]})" for w in widgets[:3]]
                parts.append(f"Flutter widgets: {', '.join(widget_info)}")
                if matches.get('provider'):
                    parts.append(f"state: {', '.join(list(set(matches['provider']))[:2])}")
            elif classes:
                parts.append(f"Dart classes: {', '.join(classes[:3])}")
            funcs = matches.get('function', [])
            if funcs:
                parts.append(f"{len(funcs)} functions")

        elif ext == '.rb':
            if matches.get('rails'):
                rails_bases = list(set(matches['rails']))
                parts.append(f"Rails {', '.join(rails_bases[:2])}")
            classes = matches.get('class', [])
            modules = matches.get('module', [])
            methods = matches.get('method', [])
            if modules:
                parts.append(f"modules: {', '.join(modules[:3])}")
            if classes:
                parts.append(f"classes: {', '.join(classes[:3])}")
            if methods:
                parts.append(f"{len(methods)} methods")

        elif ext == '.sql':
            tables_created = matches.get('create_table', [])
            tables_altered = matches.get('alter_table', [])
            views = matches.get('view', [])
            procs = matches.get('procedure', [])
            if tables_created:
                parts.append(f"creates tables: {', '.join(tables_created[:4])}")
            if tables_altered:
                parts.append(f"alters: {', '.join(tables_altered[:3])}")
            if views:
                parts.append(f"views: {', '.join(views[:3])}")
            if procs:
                parts.append(f"procedures: {', '.join(procs[:3])}")
            if matches.get('create_index'):
                parts.append(f"{len(matches['create_index'])} indexes")

        elif ext == '.sh':
            funcs = matches.get('function', [])
            shebang = matches.get('shebang', [''])[0] if matches.get('shebang') else ''
            if shebang:
                parts.append(f"Shell script ({os.path.basename(shebang)})")
            else:
                parts.append("Shell script")
            if funcs:
                parts.append(f"functions: {', '.join(funcs[:4])}")

        elif ext == '.yaml':
            if matches.get('docker'):
                services = matches.get('top_keys', [])
                parts.append(f"Docker Compose")
            elif matches.get('k8s'):
                kinds = matches.get('k8s', [])
                parts.append(f"Kubernetes: {', '.join(kinds[:3])}")
            elif matches.get('github_actions'):
                parts.append("GitHub Actions workflow")
            else:
                keys = matches.get('top_keys', [])[:5]
                if keys:
                    parts.append(f"YAML config: {', '.join(keys)}")

        elif ext == '.json':
            if matches.get('package_json') and 'name' in str(matches.get('package_json', [])):
                parts.append("package.json")
            elif matches.get('tsconfig'):
                parts.append("tsconfig.json")
            else:
                parts.append("JSON data")

        elif ext == '.vue':
            comp = matches.get('component_name', [])
            name = ''
            if comp:
                name = comp[0] if isinstance(comp[0], str) else comp[0][0] or comp[0][1]
            api_hooks = matches.get('composition_api', [])
            if name:
                parts.append(f"Vue component: {name}")
            else:
                parts.append("Vue component")
            if api_hooks:
                parts.append(f"composition API: {', '.join(list(set(api_hooks))[:3])}")

        elif ext == '.svelte':
            parts.append("Svelte component")
            if matches.get('reactive'):
                parts.append("reactive declarations")
            if matches.get('store'):
                parts.append(f"stores: {', '.join(list(set(matches['store']))[:3])}")

        elif ext == '.graphql':
            types = matches.get('type', [])
            inputs = matches.get('input', [])
            has_query = bool(matches.get('query'))
            has_mutation = bool(matches.get('mutation'))
            role_parts = []
            if has_query:
                role_parts.append("Query")
            if has_mutation:
                role_parts.append("Mutation")
            if types:
                role_parts.append(f"types: {', '.join(types[:3])}")
            if inputs:
                role_parts.append(f"inputs: {', '.join(inputs[:3])}")
            parts.append(f"GraphQL schema: {', '.join(role_parts)}")

        elif ext == '.prisma':
            models = matches.get('model', [])
            enums = matches.get('enum', [])
            if models:
                parts.append(f"Prisma models: {', '.join(models[:4])}")
            if enums:
                parts.append(f"enums: {', '.join(enums[:3])}")

        elif ext == '.toml':
            if matches.get('cargo'):
                parts.append("Cargo.toml (Rust project)")
            sections = matches.get('sections', [])
            if sections and not matches.get('cargo'):
                parts.append(f"TOML config: {', '.join(sections[:5])}")

        elif ext == 'Dockerfile':
            bases = matches.get('from', [])
            stages = matches.get('stage', [])
            ports = matches.get('expose', [])
            if stages:
                parts.append(f"Dockerfile: multi-stage ({', '.join(stages[:3])})")
            elif bases:
                parts.append(f"Dockerfile: FROM {bases[0]}")
            if ports:
                parts.append(f"exposes {', '.join(ports[:3])}")

        if parts:
            return '; '.join(parts)
        return self._generic_fallback(filepath, content)

    def _generic_fallback(self, filepath, content):
        """Ultimate fallback: first comment + line count."""
        lines = content.split('\n')
        non_empty = sum(1 for l in lines if l.strip())

        # Try to extract first meaningful comment block
        first_comment = self._extract_first_comment(content)
        if first_comment:
            if len(first_comment) > 90:
                first_comment = first_comment[:87] + '...'
            return f"{first_comment} ({non_empty} lines)"

        ext = os.path.splitext(filepath)[1]
        return f"{ext.lstrip('.').upper() or 'Text'} file: {non_empty} lines"

    def _extract_first_comment(self, content):
        """Extract the first comment block from any language."""
        lines = content.strip().split('\n')

        # Skip shebang
        start = 0
        if lines and lines[0].startswith('#!'):
            start = 1

        comment_lines = []
        for line in lines[start:start+10]:
            stripped = line.strip()
            # Single-line comments: # // -- ;
            for prefix in ('#', '//', '--', ';'):
                if stripped.startswith(prefix):
                    comment_text = stripped[len(prefix):].strip()
                    if comment_text and not comment_text.startswith('!'):
                        comment_lines.append(comment_text)
                    break
            else:
                # Block comments: /* ... */ or /** ... */
                block_match = re.match(r'/\*\*?\s*(.*?)(?:\*/)?$', stripped)
                if block_match:
                    comment_lines.append(block_match.group(1).strip())
                elif stripped.startswith('*') and not stripped.startswith('*/'):
                    comment_lines.append(stripped.lstrip('* ').strip())
                elif comment_lines:
                    break  # End of comment block

        if comment_lines:
            return ' '.join(comment_lines[:2])
        return None


# =============================================================================
# Main Entry Point
# =============================================================================

# Language extension to summarizer class mapping
PYTHON_EXTS = {'.py'}
JSTS_EXTS = {'.js', '.jsx', '.ts', '.tsx'}

# Instantiate summarizers (reusable, stateless)
_python_summarizer = PythonSummarizer()
_jsts_summarizer = JSTSSummarizer()
_generic_summarizer = GenericSummarizer()


def summarize_file(filepath, content=None):
    """
    Generate a 1-line heuristic summary for a file.

    Args:
        filepath: Path to the file (used for extension detection)
        content: File content string. If None, reads from filepath.

    Returns:
        str: A 1-line summary of the file's purpose and contents.
    """
    if content is None:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return f"[Error reading file: {e}]"

    ext = os.path.splitext(filepath)[1]
    basename = os.path.basename(filepath)

    # Special files by name
    if basename == 'Dockerfile' or basename.startswith('Dockerfile.'):
        return _generic_summarizer.summarize(filepath, content)

    if ext in PYTHON_EXTS:
        return _python_summarizer.summarize(filepath, content)
    elif ext in JSTS_EXTS:
        return _jsts_summarizer.summarize(filepath, content)
    else:
        return _generic_summarizer.summarize(filepath, content)


# CLI testing
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <file1> [file2] ...")
        sys.exit(1)

    for fpath in sys.argv[1:]:
        if os.path.isfile(fpath):
            summary = summarize_file(fpath)
            print(f"  {fpath}: {summary}")
        else:
            print(f"  {fpath}: [not found]")
