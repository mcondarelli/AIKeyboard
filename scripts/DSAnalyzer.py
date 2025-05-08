import ast
import sys
from pathlib import Path
from typing import Set, Tuple


class DependencyAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processed_files = set()
        self.local_packages = {'aikeyboard'}  # Add other local package names if any

    def is_standard_library(self, module_name: str) -> bool:
        if module_name in sys.builtin_module_names:
            return True
        
        # Handle common standard library modules that might not be in builtins
        stdlib_modules = {'os', 'sys', 're', 'json', 'datetime', 'pathlib', 'dataclasses',
                          'locale', 'logging', 'platform', 'shutil', 'subprocess',
                          'tempfile', 'typing', 'zipfile'}
        if module_name in stdlib_modules:
            return True
            
        return False

    def is_local_import(self, module_name: str) -> bool:
        # Handle absolute imports from local packages
        if any(module_name.startswith(pkg) for pkg in self.local_packages):
            return True
            
        # Handle relative imports (they won't start with a known package name)
        if module_name.startswith('.'):
            return True
            
        return False

    def resolve_local_path(self, module_name: str, current_file: Path) -> Path:
        path = module_name.replace('.', '/')
        if path.startswith('/'):
            # relative import
            path = current_file.parent / path
        else:
            # we should match with all defined source bases
            base = str(current_file.parent)
            idx = base.index(path.split('/')[0])
            if idx >= 0:
                path = base[:idx] + path
                path = Path(path)
            else:
                path = Path(path)
        if path.is_dir():
            # see if we have a __init__.py
            path = path / '__init__.py'
            if path.is_file():
                return path
        path = Path(str(path) + '.py')
        if path.is_file():
            return path
            
        raise FileNotFoundError(f"Cannot resolve local path for {module_name}")


    def get_imports_from_file(self, file_path: Path) -> Tuple[Set[str], Set[str]]:
        local_imports = set()
        external_imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (UnicodeDecodeError, SyntaxError, FileNotFoundError):
            return set(), set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if not self.is_standard_library(module_name):
                        if self.is_local_import(module_name):
                            local_imports.add(module_name)
                        else:
                            external_imports.add(module_name)
                            
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ''
                level = getattr(node, 'level', 0)
                
                if level > 0:
                    # Relative import - treat as local
                    full_module = ('.' * level) + module_name if module_name else '.' * level
                    local_imports.add(full_module)
                elif module_name and not self.is_standard_library(module_name):
                    if self.is_local_import(module_name):
                        local_imports.add(module_name)
                    else:
                        external_imports.add(module_name)

        return local_imports, external_imports

    def analyze_file(self, file_path: Path, dept=0) -> Tuple[Set[str], Set[str]]:
        print(f'{'  '*dept}{str(file_path)}')
        if file_path in self.processed_files:
            return set(), set()
        self.processed_files.add(file_path)

        local_imports, external_imports = self.get_imports_from_file(file_path)
        all_external = set(external_imports)
        
        # Process local imports recursively
        for module_name in local_imports:
            print(f'{'  '*dept}--{module_name}')
            try:
                module_path = self.resolve_local_path(module_name, file_path)
                print(f'{'  '*dept}--{module_path}')
                sub_local, sub_external = self.analyze_file(module_path, dept+1)
                all_external.update(sub_external)
            except FileNotFoundError as e:
                print(f'{'  '*dept}??{e}')

        return local_imports, all_external

def main():
    #if len(sys.argv) != 2:
    #    print("Usage: python dependency_analyzer.py <path_to_script.py>")
    #    sys.exit(1)

    #script_path = Path(sys.argv[1]).resolve()
    script_path = Path('src/aikeyboard/AIKeyboard.py').resolve()
    project_root = script_path.parents[1] if 'src' in script_path.parts else script_path.parent
    
    analyzer = DependencyAnalyzer(project_root)
    local_deps, external_deps = analyzer.analyze_file(script_path)
    
    # Filter results
    final_external = set()
    for dep in external_deps:
        if not analyzer.is_standard_library(dep):
            final_external.add(dep.split('.')[0])  # Only top-level package
    
    print("\nExternal dependencies (non-local, not in standard library):")
    for dep in sorted(final_external):
        print(f"- {dep}")
    
    print(f"\nFound {len(final_external)} external dependencies")

if __name__ == "__main__":
    main()
