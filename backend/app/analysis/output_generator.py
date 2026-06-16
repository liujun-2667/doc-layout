import json
import os
from typing import List, Dict, Any
from datetime import datetime


class OutputGenerator:
    def __init__(self):
        pass

    def generate_json(
        self,
        task_id: str,
        pages_data: List[Dict[str, Any]]
    ) -> str:
        output = {
            "task_id": task_id,
            "generated_at": datetime.now().isoformat(),
            "pages": [],
        }

        for page_data in pages_data:
            page_output = {
                "page_number": page_data["page_number"],
                "width": page_data["width"],
                "height": page_data["height"],
                "rotation_angle": page_data.get("rotation_angle", 0),
                "elements": [],
                "tables": [],
                "reading_order": [],
            }

            for elem in page_data.get("elements", []):
                page_output["elements"].append({
                    "id": elem["id"],
                    "type": elem["element_type"],
                    "bbox": {
                        "x": elem["x"],
                        "y": elem["y"],
                        "width": elem["width"],
                        "height": elem["height"],
                    },
                    "confidence": elem["confidence"],
                    "reading_order": elem["reading_order"],
                    "level": elem.get("level", 1),
                    "text_content": elem.get("text_content", ""),
                    "metadata": elem.get("metadata", {}),
                })
                page_output["reading_order"].append(elem["reading_order"])

            for table in page_data.get("tables", []):
                page_output["tables"].append({
                    "id": table["id"],
                    "rows": table["rows"],
                    "cols": table["cols"],
                    "has_header": table["has_header"],
                    "cells": table.get("cells", []),
                })

            output["pages"].append(page_output)

        return json.dumps(output, ensure_ascii=False, indent=2)

    def generate_html(
        self,
        task_id: str,
        pages_data: List[Dict[str, Any]]
    ) -> str:
        html_parts = []

        html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文档版面还原 - 任务 {task_id}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .document-container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .page {{
            background: white;
            margin-bottom: 30px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
        }}
        .page-header {{
            font-size: 12px;
            color: #666;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .element {{
            margin-bottom: 10px;
            position: relative;
        }}
        .title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        .title.level-1 {{
            font-size: 28px;
            line-height: 1.3;
        }}
        .title.level-2 {{
            font-size: 22px;
            line-height: 1.3;
        }}
        .title.level-3 {{
            font-size: 18px;
            line-height: 1.3;
        }}
        .paragraph {{
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            text-align: justify;
            margin-bottom: 12px;
        }}
        .header {{
            font-size: 12px;
            color: #999;
            text-align: center;
            margin-bottom: 20px;
        }}
        .footer {{
            font-size: 12px;
            color: #999;
            text-align: center;
            margin-top: 20px;
        }}
        .page_number {{
            font-size: 12px;
            color: #999;
            text-align: center;
        }}
        .figure {{
            margin: 20px 0;
            text-align: center;
        }}
        .figure img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
        }}
        .caption {{
            font-size: 12px;
            color: #666;
            text-align: center;
            margin-top: 8px;
            font-style: italic;
        }}
        .list {{
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            padding-left: 20px;
        }}
        .formula {{
            font-family: 'Times New Roman', serif;
            font-style: italic;
            text-align: center;
            margin: 15px 0;
            font-size: 16px;
        }}
        .stamp {{
            display: inline-block;
            padding: 10px 20px;
            border: 2px solid #d32f2f;
            border-radius: 50%;
            color: #d32f2f;
            font-weight: bold;
            transform: rotate(-15deg);
            opacity: 0.8;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 13px;
        }}
        table th, table td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        table th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        table tr:nth-child(even) {{
            background-color: #fafafa;
        }}
        .columns-2 {{
            column-count: 2;
            column-gap: 40px;
        }}
        .columns-3 {{
            column-count: 3;
            column-gap: 30px;
        }}
    </style>
</head>
<body>
    <div class="document-container">
""".format(task_id=task_id))

        for page_data in pages_data:
            page_num = page_data["page_number"]
            width = page_data["width"]
            height = page_data["height"]
            elements = sorted(
                page_data.get("elements", []),
                key=lambda e: e["reading_order"]
            )
            tables = page_data.get("tables", [])
            columns_count = page_data.get("columns_count", 1)

            html_parts.append(f'        <div class="page">')
            html_parts.append(f'            <div class="page-header">第 {page_num} 页</div>')

            if columns_count > 1:
                html_parts.append(f'            <div class="columns-{columns_count}">')

            for elem in elements:
                elem_type = elem["element_type"]
                text = elem.get("text_content", "")
                level = elem.get("level", 1)

                if elem_type == "title":
                    html_parts.append(
                        f'            <div class="element title level-{level}">{text}</div>'
                    )
                elif elem_type == "paragraph":
                    html_parts.append(
                        f'            <div class="element paragraph">{text}</div>'
                    )
                elif elem_type == "header":
                    html_parts.append(
                        f'            <div class="element header">{text}</div>'
                    )
                elif elem_type == "footer":
                    html_parts.append(
                        f'            <div class="element footer">{text}</div>'
                    )
                elif elem_type == "page_number":
                    html_parts.append(
                        f'            <div class="element page_number">{text}</div>'
                    )
                elif elem_type == "figure":
                    img_path = elem.get("image_path", "")
                    html_parts.append(f'''            <div class="element figure">
                <img src="{img_path}" alt="Figure">
            </div>''')
                elif elem_type == "caption":
                    html_parts.append(
                        f'            <div class="element caption">{text}</div>'
                    )
                elif elem_type == "list":
                    html_parts.append(
                        f'            <div class="element list"><ul><li>{text}</li></ul></div>'
                    )
                elif elem_type == "formula":
                    html_parts.append(
                        f'            <div class="element formula">{text}</div>'
                    )
                elif elem_type == "stamp":
                    html_parts.append(
                        f'            <div class="element stamp">{text}</div>'
                    )
                elif elem_type == "table":
                    for table in tables:
                        if table.get("element_id") == elem["id"]:
                            html_parts.append(self._render_table_html(table))
                            break

            if columns_count > 1:
                html_parts.append('            </div>')

            html_parts.append('        </div>')

        html_parts.append("""    </div>
</body>
</html>""")

        return "\n".join(html_parts)

    def _render_table_html(self, table_data: Dict[str, Any]) -> str:
        rows = table_data.get("rows", 0)
        cols = table_data.get("cols", 0)
        cells = table_data.get("cells", [])

        cell_map = {}
        for cell in cells:
            key = (cell["row"], cell["col"])
            cell_map[key] = cell

        html_lines = ['            <table>']

        for r in range(rows):
            html_lines.append('                <tr>')
            c = 0
            while c < cols:
                cell = cell_map.get((r, c))
                if cell:
                    tag = 'th' if cell.get("is_header", False) else 'td'
                    attrs = ''
                    if cell.get("rowspan", 1) > 1:
                        attrs += f' rowspan="{cell["rowspan"]}"'
                    if cell.get("colspan", 1) > 1:
                        attrs += f' colspan="{cell["colspan"]}"'
                    content = cell.get("content", "")
                    html_lines.append(f'                    <{tag}{attrs}>{content}</{tag}>')
                    c += cell.get("colspan", 1)
                else:
                    c += 1
            html_lines.append('                </tr>')

        html_lines.append('            </table>')

        return "\n".join(html_lines)

    def generate_markdown(
        self,
        task_id: str,
        pages_data: List[Dict[str, Any]]
    ) -> str:
        md_parts = []

        md_parts.append(f"# 文档版面还原 - 任务 {task_id}\n")
        md_parts.append(f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")

        for page_data in pages_data:
            page_num = page_data["page_number"]
            elements = sorted(
                page_data.get("elements", []),
                key=lambda e: e["reading_order"]
            )
            tables = page_data.get("tables", [])

            md_parts.append(f"---\n\n## 第 {page_num} 页\n\n")

            for elem in elements:
                elem_type = elem["element_type"]
                text = elem.get("text_content", "")
                level = elem.get("level", 1)

                if elem_type == "title":
                    md_prefix = "#" * (level + 1)
                    md_parts.append(f"\n{md_prefix} {text}\n\n")
                elif elem_type == "paragraph":
                    md_parts.append(f"{text}\n\n")
                elif elem_type == "header":
                    md_parts.append(f"> **页眉**: {text}\n\n")
                elif elem_type == "footer":
                    md_parts.append(f"> **页脚**: {text}\n\n")
                elif elem_type == "page_number":
                    md_parts.append(f"> 页码: {text}\n\n")
                elif elem_type == "figure":
                    img_path = elem.get("image_path", "")
                    md_parts.append(f"![Figure]({img_path})\n\n")
                elif elem_type == "caption":
                    md_parts.append(f"*图注: {text}*\n\n")
                elif elem_type == "list":
                    md_parts.append(f"- {text}\n")
                elif elem_type == "formula":
                    md_parts.append(f"$$ {text} $$\n\n")
                elif elem_type == "stamp":
                    md_parts.append(f"**[印章: {text}]**\n\n")
                elif elem_type == "table":
                    for table in tables:
                        if table.get("element_id") == elem["id"]:
                            md_parts.append(self._render_table_markdown(table))
                            md_parts.append("\n")
                            break

        return "".join(md_parts)

    def _render_table_markdown(self, table_data: Dict[str, Any]) -> str:
        rows = table_data.get("rows", 0)
        cols = table_data.get("cols", 0)
        cells = table_data.get("cells", [])
        has_header = table_data.get("has_header", False)

        cell_map = {}
        for cell in cells:
            key = (cell["row"], cell["col"])
            cell_map[key] = cell

        md_lines = []

        for r in range(rows):
            row_cells = []
            c = 0
            while c < cols:
                cell = cell_map.get((r, c))
                if cell:
                    content = cell.get("content", "").replace("|", "\\|")
                    row_cells.append(content)
                    c += cell.get("colspan", 1)
                else:
                    row_cells.append("")
                    c += 1
            md_lines.append("| " + " | ".join(row_cells) + " |")

            if has_header and r == 0:
                md_lines.append("| " + " | ".join(["---"] * cols) + " |")

        return "\n".join(md_lines) + "\n"

    def save_output(
        self,
        content: str,
        output_dir: str,
        filename: str,
        fmt: str
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        ext_map = {
            "json": "json",
            "html": "html",
            "markdown": "md",
        }

        ext = ext_map.get(fmt, "txt")
        output_path = os.path.join(output_dir, f"{filename}.{ext}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path
