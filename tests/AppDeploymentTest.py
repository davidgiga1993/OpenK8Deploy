import os
from unittest import TestCase

import yaml

from config.Config import ProjectConfig
from deploy.AppDeploy import AppDeployment
from utils.Errors import MissingParam


class AppDeploymentTest(TestCase):

    def setUp(self) -> None:
        self._base_path = os.path.dirname(__file__)
        self._tmp_file = 'out.yml'

    def tearDown(self) -> None:
        if os.path.isfile(self._tmp_file):
            os.remove(self._tmp_file)

    def test_library(self):
        prj_config = ProjectConfig.load(os.path.join(self._base_path, 'lib-usage'))
        app_config = prj_config.load_app_config('some-app')
        runner = AppDeployment(prj_config, app_config, dry_run=self._tmp_file)
        runner.deploy()
        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('paramValue', data['metadata']['name'])

    def test_for_each(self):
        prj_config = ProjectConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        app_config = prj_config.load_app_config('app-for-each')
        runner = AppDeployment(prj_config, app_config, dry_run=self._tmp_file)
        runner.deploy()

        docs = []
        with open(self._tmp_file) as f:
            data = yaml.load_all(f, Loader=yaml.FullLoader)
            for doc in data:
                docs.append(doc)

        # We should have two instances
        self.assertEqual(2, len(docs))
        self.assertEqual('hello', docs[0]['metadata']['REMAPPED'])
        self.assertEqual('hello', docs[1]['metadata']['REMAPPED'])

    def test_params(self):
        prj_config = ProjectConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        app_config = prj_config.load_app_config('app-params')
        runner = AppDeployment(prj_config, app_config, dry_run=self._tmp_file)
        try:
            runner.deploy()
            self.fail('No exception raised for missing param')
        except MissingParam:
            pass

        external_params = {
            'SomeParam': 'input'
        }
        app_config._external_vars = external_params
        runner.deploy()

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('input', data['someObj']['param'])

    def test_inherit_vars(self):
        prj_config = ProjectConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        app_config = prj_config.load_app_config('app')
        runner = AppDeployment(prj_config, app_config, dry_run=self._tmp_file)
        runner.deploy()

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('ABC', data['metadata']['name'])
        self.assertEqual('ABC-1', data['metadata']['REMAPPED'])
        self.assertEqual('ABC', data['metadata']['REMAPPED2'])
        self.assertEqual('DEF', data['metadata']['name2'])
        self.assertEqual('3', data['metadata']['base'])
        self.assertEqual('global', data['metadata']['GLOBAL_TEST'])
