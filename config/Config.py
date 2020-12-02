from __future__ import annotations

import os
from typing import Optional, Dict

from config.AppConfig import AppConfig
from config.BaseConfig import BaseConfig
from oc.Oc import Oc
from processing.YmlTemplateProcessor import YmlTemplateProcessor
from utils.Errors import ConfigError


class ProjectConfig(BaseConfig):
    """
    Project configuration
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root
        self._oc = None
        self._library = None  # type: Optional[ProjectConfig]

        inherit = self.data.get('inherit')
        if inherit is not None:
            # Use a library
            parent_dir = os.path.abspath(os.path.join(path, os.pardir, os.pardir))
            lib_dir = os.path.join(parent_dir, inherit)
            if not os.path.isdir(lib_dir):
                raise FileNotFoundError('Library not found: ' + lib_dir)
            self._library = ProjectConfig.load(lib_dir)
            if not self._library.is_library():
                raise ConfigError('Project ' + inherit + ' referenced as library but is not a library')

    @classmethod
    def load(cls, path: str) -> ProjectConfig:
        return ProjectConfig(path, os.path.join(path, '_root.yml'))

    def get_config_root(self) -> str:
        return self._config_root

    def is_library(self) -> bool:
        """
        Indicates if this collection is a library
        """
        return self.data.get('type', '') == 'library'

    def create_oc(self) -> Oc:
        """
        Creates a new openshift client
        :return: Client
        """
        if self._oc is not None:
            return self._oc

        oc = Oc()
        self._oc = oc
        return oc

    def get_oc_project_name(self) -> Optional[str]:
        """
        Returns the name of the openshift project

        :return: Name or null for libraries
        """
        return self.data.get('project')

    def get_template_processor(self) -> YmlTemplateProcessor:
        root_processor = super().get_template_processor()
        if self._library is not None:
            processor = self._library.get_template_processor()
            root_processor.parent(processor)
        return root_processor

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all variables which are available for the yml files
        :return: Key, value map
        """
        items = super().get_replacements()
        name = self.get_oc_project_name()
        if name is not None:
            items.update({
                'OC_PROJECT': name
            })
        return items

    def load_app_config(self, name: str) -> AppConfig:
        folder_path = os.path.join(self._config_root, name)
        if not os.path.isdir(folder_path):
            if self._library is not None:
                return self._library.load_app_config(name)
            raise FileNotFoundError('App folder not found: ' + folder_path)

        index_file = os.path.join(folder_path, '_index.yml')
        if not os.path.isfile(index_file):
            # Index file missing
            raise FileNotFoundError('No index yml file found: ' + index_file)

        variables = self.get_replacements()
        return AppConfig(folder_path, index_file, variables)
