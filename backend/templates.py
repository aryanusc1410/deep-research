"""
Report generation templates and prompts.

This module contains all prompt templates used for generating different
styles of research reports. Each template provides specific instructions
to the LLM for structuring and formatting the output.
"""

from typing import Final

from constants import (
    TEMPLATE_BULLET_SUMMARY,
    TEMPLATE_TWO_COLUMN,
    TEMPLATE_DETAILED_REPORT,
)


# ============================================================================
# Template Definitions
# ============================================================================

BULLET_SUMMARY_TEMPLATE: Final[str] = (
    "You are a meticulous research writer.\n"
    "Write a crisp, bulleted executive summary with sections: TL;DR, Key Findings, Evidence, Risks/Unknowns.\n"
    "Use numbered bullets. Include inline numeric citations like [1], [2] mapped to the SOURCES list I provide.\n"
    "Strictly obey the structure and headings."
)

TWO_COLUMN_TEMPLATE: Final[str] = (
    "You are a research analyst. Create a markdown table with EXACTLY two columns: Claim | Evidence.\n\n"
    "CRITICAL REQUIREMENTS:\n"
    "1. Output ONLY the table - no introduction, no conclusion, no extra text\n"
    "2. First row must be: | Claim | Evidence |\n"
    "3. Second row must be separator: |-------|----------|\n"
    "4. Each following row: | specific claim | evidence with citations [1], [2] |\n"
    "5. Create 6-12 rows total\n"
    "6. Each claim must be concise (1-2 sentences)\n"
    "7. Each evidence must have at least one citation [X]\n"
    "8. Use proper markdown table format with pipes (|)\n\n"
    "Example format:\n"
    "| Claim | Evidence |\n"
    "|-------|----------|\n"
    "| First claim here | Supporting evidence with source [1] |\n"
    "| Second claim here | More evidence from [2] and [3] |\n\n"
    "DO NOT include any text before or after the table."
)

DETAILED_REPORT_TEMPLATE: Final[str] = (
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


# ============================================================================
# Template Registry
# ============================================================================

REPORT_TEMPLATES: Final[dict[str, str]] = {
    TEMPLATE_BULLET_SUMMARY: BULLET_SUMMARY_TEMPLATE,
    TEMPLATE_TWO_COLUMN: TWO_COLUMN_TEMPLATE,
    TEMPLATE_DETAILED_REPORT: DETAILED_REPORT_TEMPLATE,
}


# ============================================================================
# Template Utility Functions
# ============================================================================

def get_template(template_name: str) -> str:
    """
    Retrieve a template by name.

    Args:
        template_name: Name of the template to retrieve

    Returns:
        The template string

    Raises:
        KeyError: If template name is not recognized
    """
    return REPORT_TEMPLATES[template_name]


def get_available_templates() -> list[str]:
    """
    Get list of all available template names.

    Returns:
        List of template names
    """
    return list(REPORT_TEMPLATES.keys())


def add_provider_specific_instructions(
    template: str,
    is_gemini: bool,
    template_name: str
) -> str:
    """
    Add provider-specific instructions to a template.

    Different LLM providers may need different instructions for
    optimal output. This function adds those customizations.

    Args:
        template: Base template string
        is_gemini: Whether this is for Gemini provider
        template_name: Name of the template being used

    Returns:
        Template with provider-specific instructions added
    """
    if not is_gemini:
        return template

    # Gemini-specific instructions
    if template_name == TEMPLATE_TWO_COLUMN:
        additional = (
            "\n\n**CRITICAL INSTRUCTIONS FOR THIS TASK**: "
            "You MUST output ONLY a markdown table, nothing else. "
            "NO introduction, NO explanation, NO conclusion. "
            "Maximum 12 rows. Each cell: 1-2 sentences maximum. "
            "Start directly with: | Claim | Evidence |"
        )
    else:
        additional = "\nBe concise and focused. Prioritize quality over length."

    return template + additional