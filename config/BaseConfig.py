from typing import Dict, List, Optional

from config.YmlConfig import YmlConfig
from processing.YmlTemplateProcessor import YmlTemplateProcessor


class BaseConfig(YmlConfig):
    def __init__(self, path: Optional[str], external_vars: Dict[str, str] = None):
        super().__init__(path)
        self._external_vars = {}  # type: Dict[str, str]
        """
        External variables for the templating engine
        """
        if external_vars is not None:
            self._external_vars = external_vars

    def get_template_processor(self) -> YmlTemplateProcessor:
        return YmlTemplateProcessor(self)

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all variables which are available for the yml files

        :return: Key, value map
        """
        items = self.data.get('vars', {})
        items.update(self._external_vars)
        return items

    def get_params(self) -> List[str]:
        """
        Returns all required parameters

        :return: Names
        """
        return self.data.get('params', [])
