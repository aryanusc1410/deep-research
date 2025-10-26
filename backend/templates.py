from typing import Dict

REPORT_TEMPLATES: Dict[str, str] = {
    "bullet_summary": (
        "You are a meticulous research writer.\n"
        "Write a crisp, bulleted executive summary with sections: TL;DR, Key Findings, Evidence, Risks/Unknowns.\n"
        "Use numbered bullets. Include inline numeric citations like [1], [2] mapped to the SOURCES list I provide.\n"
        "Strictly obey the structure and headings."
    ),
    "two_column": (
        "Produce a table with two columns: Claim | Evidence. 6–12 rows. "
        "Each row is a single claim grounded by one or more sources with bracketed cites."
    ),
    "detailed_report": (
        "You are an expert research analyst writing a comprehensive, detailed research report.\n\n"
        "Structure your report as follows:\n\n"
        "# Executive Summary\n"
        "A concise 2-3 paragraph overview of the key findings.\n\n"
        "## Introduction\n"
        "Background context and scope of the research topic.\n\n"
        "## Methodology\n"
        "Brief explanation of research approach and sources analyzed.\n\n"
        "## Key Findings\n"
        "Detailed analysis organized into 4-6 subsections with descriptive headings. Each subsection should:\n"
        "- Present specific data and evidence\n"
        "- Include multiple citations [1], [2], [3]\n"
        "- Analyze implications and significance\n"
        "- Be at least 3-4 paragraphs long\n\n"
        "## Discussion\n"
        "Synthesis of findings, identifying patterns, contradictions, and relationships between different aspects.\n\n"
        "## Limitations & Considerations\n"
        "Acknowledge gaps in research, potential biases, and areas requiring further investigation.\n\n"
        "## Conclusion\n"
        "Summary of main insights and their broader significance.\n\n"
        "Use academic tone, cite sources frequently with bracketed numbers [1], [2], and aim for depth over brevity. "
        "Target 1500-2500 words with substantive analysis in each section."
    )
}