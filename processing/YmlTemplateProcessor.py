from __future__ import annotations

from typing import Optional, Dict

from config.Config import AppConfig


class YmlTemplateProcessor:
    """
    Processes yml files by replacing any string placeholders
    """

    def __init__(self, app_config: AppConfig):
        self._app_config = app_config  # type: AppConfig
        self._parent = None  # type: Optional[YmlTemplateProcessor]

    def process(self, data: dict):
        """
        Processes the app data

        :param data: Data of the app, the data will be modified in place
        """
        replacements = self.get_replacements()
        self._walk_dict(replacements, data)

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all replacements handled by this processor, including all parent variables
        :return: Replacements
        """
        replacements = self._app_config.get_replacements()
        if self._parent is not None:
            replacements.update(self._parent.get_replacements())
        return replacements

    def _walk_dict(self, replacements, data: dict):
        for key, obj in data.items():
            data[key] = self._walk_item(replacements, obj)
        return data

    def _walk_item(self, replacements, obj):
        if isinstance(obj, list):
            for idx, item in enumerate(obj):
                obj[idx] = self._walk_item(replacements, item)
            return obj

        if isinstance(obj, str):
            return self._replace(obj, replacements)

        if isinstance(obj, dict):
            return self._walk_dict(replacements, obj)
        return obj

    def _replace(self, item: str, replacements):
        for variable, value in replacements.items():
            item = item.replace('${' + variable + '}', value)
        return item

    def inherit(self, template_processor: YmlTemplateProcessor):
        """
        Inherits all replacements from the given processor.
        If the same value is defined the definition of the given processor will override
        the existing definition
        :param template_processor: Parent processor
        """
        self._parent = template_processor
