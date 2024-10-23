"""
A prompt management module using Jinja to generate complex prompts with simple templates.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from jinja2 import Environment, FileSystemLoader, Template

current_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.dirname(current_dir)

env = Environment(
    loader=FileSystemLoader(
        os.path.join(project_root, os.environ.get("PROMPT_PATH", "prompts"))
    )
)


@dataclass
class Prompter:
    """
    A class for managing and rendering prompt templates.

    Attributes:
        prompt_template (str, optional): The name of the prompt template file.
        prompt_variation (str, optional): The variation of the prompt template.
        prompt_text (str, optional): The raw prompt text.
        template (Union[str, Template], optional): The Jinja2 template object.
    """

    prompt_template: Optional[str] = None
    prompt_variation: Optional[str] = "default"
    prompt_text: Optional[str] = None
    template: Optional[Union[str, Template]] = None
    parser: Optional[Any] = None

    def __init__(self, prompt_template=None, prompt_text=None, parser=None):
        """
        Initialize the Prompter with either a template file or raw text.

        Args:
            prompt_template (str, optional): The name of the prompt template file.
            prompt_text (str, optional): The raw prompt text.
        """
        self.prompt_template = prompt_template
        self.prompt_text = prompt_text
        self.parser = parser
        self.setup()

    def setup(self):
        """
        Set up the Jinja2 template based on the provided template file or text.
        Raises:
            ValueError: If neither prompt_template nor prompt_text is provided.
        """
        if self.prompt_template:
            self.template = env.get_template(f"{self.prompt_template}.jinja")
        elif self.prompt_text:
            self.template = Template(self.prompt_text)
        else:
            raise ValueError("Prompter must have a prompt_template or prompt_text")

        assert self.prompt_template or self.prompt_text, "Prompt is required"

    @classmethod
    def from_text(cls, text: str):
        """
        Create a Prompter instance from raw text, which can contain Jinja code.

        Args:
            text (str): The raw prompt text.

        Returns:
            Prompter: A new Prompter instance.
        """
        return cls(prompt_text=text)

    def render(self, data) -> str:
        """
        Render the prompt template with the given data.

        Args:
            data (dict): The data to be used in rendering the template.

        Returns:
            str: The rendered prompt text.

        Raises:
            AssertionError: If the template is not defined or not a Jinja2 Template.
        """
        data["current_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.parser:
            data["format_instructions"] = self.parser.get_format_instructions()
        assert self.template, "Prompter template is not defined"
        assert isinstance(
            self.template, Template
        ), "Prompter template is not a Jinja2 Template"
        return self.template.render(data)
