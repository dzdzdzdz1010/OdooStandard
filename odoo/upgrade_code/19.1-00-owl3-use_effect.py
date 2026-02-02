import re


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.suffix == '.js']
    if not files:
        return

    reg_owl_import = re.compile(r'import\s*\{([^}]*)\}\s*from\s*(["\'])(@odoo/owl)\2;?', re.DOTALL)
    reg_use_effect_usage = re.compile(r'\buseEffect\b')

    for fileno, file in enumerate(files, start=1):
        content = file.content

        if 'useEffect' in content and reg_owl_import.search(content):
            new_import_block = ""

            def handle_import(match):
                nonlocal new_import_block
                raw_content = match.group(1)
                original_quote = match.group(2)
                is_multiline = '\n' in raw_content
                names = [n.strip() for n in raw_content.split(',') if n.strip()]

                if 'useEffect' in names:
                    names.remove('useEffect')
                    new_import_block = 'import { useLayoutEffect } from "@web/owl2/utils";'

                    if names:
                        if is_multiline:
                            formatted_names = ',\n    '.join(names)
                            return f'{new_import_block}\nimport {{\n    {formatted_names},\n}} from {original_quote}@odoo/owl{original_quote};'
                        else:
                            return f'{new_import_block}\nimport {{ {", ".join(names)} }} from {original_quote}@odoo/owl{original_quote};'
                    return new_import_block
                return match.group(0)

            content = reg_owl_import.sub(handle_import, content)
            content = reg_use_effect_usage.sub('useLayoutEffect', content)

        file.content = content
        file_manager.print_progress(fileno, len(files))
