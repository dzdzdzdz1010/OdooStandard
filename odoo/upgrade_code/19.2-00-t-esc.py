# Replaces the t-esc directive by t-out in preparation for the OWL3 migration

import re
import logging

_logger = logging.getLogger(__name__)


def upgrade(file_manager):
    # files = [file for file in file_manager if str(file.path) == "/home/odoo/dev/odoo/enterprise/web_gantt/static/src/gantt_compiler.js"]
    files = [file for file in file_manager if file.path.suffix == '.xml']
    if not files:
        return

    reg_t_esc = re.compile(r"""\bt-esc=""")
    # matches: <attribute name="t-esc">  /  <attribute name="t-esc"/> /  <attribute remove="1" name="t-esc" />
    reg_att_t_esc = re.compile(r'(<attribute\b[^>]*\bname\s*=\s*(["\']))t-esc(\2)')

    for fileno, file in enumerate(files, start=1):
        try:
            content = file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            # For file enterprise/l10n_cl_edi_factoring/template/aec_template.xml
            _logger.warning("upgrade_code: skipping non-utf8 file %s (%s)", file.path, e)
            continue

        if "t-esc" not in content:
            continue

        if content.startswith(("// skip_owl_ref", "# skip_owl_ref", "<!-- skip_owl_ref -->")):
            _logger.info("Skipping file %s due to presence of skip tag", file.path)
            continue

        content = reg_t_esc.sub(r't-out=', content)
        content = reg_att_t_esc.sub(r"\1t-out\3", content)

        file.content = content
        file_manager.print_progress(fileno, len(files))
