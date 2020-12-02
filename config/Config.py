from __future__ import annotations

import os

from config.AppConfig import AppConfig
from config.BaseConfig import BaseConfig
from oc.Oc import Oc


class ProjectConfig(BaseConfig):
    """
    Project configuration
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root
        self._oc = None

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
        Creates a new openshift client, preconfigured for this project
        :return: Client
        """
        if self._oc is not None:
            return self._oc

        oc = Oc()
        self._oc = oc
        return oc

    def get_project(self) -> str:
        """
        Returns the name of the openshift project
        :return:
        """
        return self.data['project']

    def load_app_config(self, name: str) -> AppConfig:
        folder_path = os.path.join(self._config_root, name)
        if not os.path.isdir(folder_path):
            raise FileNotFoundError('App folder not found: ' + folder_path)

        index_file = os.path.join(folder_path, '_index.yml')
        if not os.path.isfile(index_file):
            # Index file missing
            raise FileNotFoundError('No index yml file found: ' + index_file)

        variables = self.get_replacements()
        return AppConfig(folder_path, index_file, variables)
