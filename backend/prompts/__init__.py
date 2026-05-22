from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent)),
    undefined=StrictUndefined,   # raise on missing variables — catches prompt bugs early
    trim_blocks=True,
    lstrip_blocks=True,
)


def load_prompt(template_name: str, **kwargs: object) -> str:
    """Render a Jinja2 prompt template by filename.

    Args:
        template_name: filename relative to prompts/ (e.g. 'cold_email.j2')
        **kwargs: variables injected into the template

    Returns:
        Rendered prompt string ready to send to the LLM.

    Raises:
        jinja2.UndefinedError: if a required template variable is missing.
        jinja2.TemplateNotFound: if the template file does not exist.
    """
    template = _env.get_template(template_name)
    return template.render(**kwargs)
